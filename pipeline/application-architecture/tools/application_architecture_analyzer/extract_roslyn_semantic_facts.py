#!/usr/bin/env python3
"""
Optional Roslyn semantic extraction phase.

This stage reads Step 1 inventory outputs and relevant C# source files, then
uses a local .NET SDK/Roslyn semantic model when available. It always emits a
valid parsed artifact so the pipeline remains reusable for non-.NET projects.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


EXTRACTOR_VERSION = "0.1.0"

CSHARP_EXTRACTOR_SOURCE = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Text;

public sealed class SourceFileRecord
{
    public string Path { get; set; } = "";
    public string Project { get; set; } = "unknown";
    public string ProjectPath { get; set; } = "unknown";
    public string ProjectType { get; set; } = "unknown";
    public string ProjectCategory { get; set; } = "unknown";
    public List<string> ProjectReferences { get; set; } = new();
}

public static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    public static int Main(string[] args)
    {
        if (args.Length < 3)
        {
            Console.Error.WriteLine("Usage: RoslynSemanticExtractor <repoRoot> <outputJson> <sourceListJson>");
            return 2;
        }

        var repoRoot = Path.GetFullPath(args[0]);
        var outputJson = Path.GetFullPath(args[1]);
        var sourceListJson = Path.GetFullPath(args[2]);
        var sourceRows = JsonSerializer.Deserialize<List<SourceFileRecord>>(
            File.ReadAllText(sourceListJson, Encoding.UTF8),
            JsonOptions) ?? new List<SourceFileRecord>();

        var allComponents = new List<Dictionary<string, object?>>();
        var allDependencies = new List<Dictionary<string, object?>>();
        var allRouteHints = new List<Dictionary<string, object?>>();
        var unresolvedInvocations = 0;
        var compilationDiagnostics = new List<Dictionary<string, object?>>();

        foreach (var projectGroup in sourceRows.GroupBy(row => row.Project).OrderBy(group => group.Key))
        {
            var primaryRows = projectGroup.ToList();
            var projectReferences = primaryRows.SelectMany(row => row.ProjectReferences).Where(value => !string.IsNullOrWhiteSpace(value)).Distinct().ToHashSet();
            var compilationRows = sourceRows
                .Where(row => row.Project == projectGroup.Key || (projectReferences.Contains(row.Project) && !row.Path.EndsWith("/Program.cs", StringComparison.OrdinalIgnoreCase)))
                .GroupBy(row => row.Path)
                .Select(group => group.First())
                .ToList();

            var sourceByPath = compilationRows.ToDictionary(row => NormalizePath(row.Path), row => row);
            var ownPaths = primaryRows.Select(row => NormalizePath(row.Path)).ToHashSet();
            var syntaxTrees = new List<SyntaxTree>();
            foreach (var row in compilationRows)
            {
                var absolutePath = Path.Combine(repoRoot, row.Path.Replace('/', Path.DirectorySeparatorChar));
                if (!File.Exists(absolutePath))
                {
                    continue;
                }

                var text = SourceText.From(File.ReadAllText(absolutePath, Encoding.UTF8), Encoding.UTF8);
                syntaxTrees.Add(CSharpSyntaxTree.ParseText(
                    text,
                    new CSharpParseOptions(LanguageVersion.Preview, DocumentationMode.None, SourceCodeKind.Regular),
                    path: NormalizePath(row.Path)));
            }

            if (syntaxTrees.Count == 0)
            {
                continue;
            }

            var compilation = CSharpCompilation.Create(
                "ArchitectureSemanticExtraction_" + SafeId(projectGroup.Key),
                syntaxTrees,
                MetadataReferences(),
                new CSharpCompilationOptions(
                    OutputKind.DynamicallyLinkedLibrary,
                    nullableContextOptions: NullableContextOptions.Enable));

            foreach (var diagnostic in compilation.GetDiagnostics().Where(item => item.Severity == DiagnosticSeverity.Error).Take(20))
            {
                compilationDiagnostics.Add(new Dictionary<string, object?>
                {
                    ["project"] = projectGroup.Key,
                    ["id"] = diagnostic.Id,
                    ["message"] = diagnostic.GetMessage(),
                    ["severity"] = diagnostic.Severity.ToString(),
                    ["source_file"] = NormalizePath(diagnostic.Location.GetLineSpan().Path),
                    ["line"] = diagnostic.Location.GetLineSpan().StartLinePosition.Line + 1
                });
            }

            var localTypesByFullName = new Dictionary<string, INamedTypeSymbol>();
            var localTypesBySimpleName = new Dictionary<string, List<INamedTypeSymbol>>();
            foreach (var tree in syntaxTrees)
            {
                var relPath = NormalizePath(tree.FilePath);
                var model = compilation.GetSemanticModel(tree, ignoreAccessibility: true);
                var root = tree.GetRoot();
                foreach (var typeDecl in root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>())
                {
                    var symbol = model.GetDeclaredSymbol(typeDecl) as INamedTypeSymbol;
                    if (symbol == null)
                    {
                        continue;
                    }

                    var fullName = CleanSymbol(symbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
                    localTypesByFullName[fullName] = symbol;
                    if (!localTypesBySimpleName.ContainsKey(symbol.Name))
                    {
                        localTypesBySimpleName[symbol.Name] = new List<INamedTypeSymbol>();
                    }
                    localTypesBySimpleName[symbol.Name].Add(symbol);
                }
            }

            foreach (var tree in syntaxTrees)
            {
                var relPath = NormalizePath(tree.FilePath);
                if (!ownPaths.Contains(relPath))
                {
                    continue;
                }

                var row = sourceByPath.TryGetValue(relPath, out var record) ? record : new SourceFileRecord { Path = relPath, Project = projectGroup.Key };
                var model = compilation.GetSemanticModel(tree, ignoreAccessibility: true);
                var root = tree.GetRoot();

                foreach (var typeDecl in root.DescendantNodes().OfType<BaseTypeDeclarationSyntax>())
                {
                    var symbol = model.GetDeclaredSymbol(typeDecl) as INamedTypeSymbol;
                    if (symbol == null)
                    {
                        continue;
                    }

                    allComponents.Add(BuildComponent(symbol, typeDecl, tree, row));
                }

                foreach (var invocation in root.DescendantNodes().OfType<InvocationExpressionSyntax>())
                {
                    var syntaxMethodName = InvokedMethodName(invocation.Expression);
                    var callerType = invocation.Ancestors().OfType<BaseTypeDeclarationSyntax>().FirstOrDefault();
                    var callerSymbol = callerType == null ? null : model.GetDeclaredSymbol(callerType) as INamedTypeSymbol;
                    var callerComponent = callerSymbol?.Name ?? (relPath.EndsWith("/Program.cs", StringComparison.OrdinalIgnoreCase) ? "Program" : "unknown");
                    var callerFullName = callerSymbol == null ? "Program" : CleanSymbol(callerSymbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
                    var callerMethod = ContainingMethodName(model, invocation);
                    var line = LineFor(tree, invocation);

                    if (IsDiRegistration(syntaxMethodName))
                    {
                        var registration = BuildDiRegistration(model, invocation, syntaxMethodName, callerComponent, relPath, line, row);
                        if (registration != null)
                        {
                            allDependencies.Add(registration);
                        }
                    }

                    var routeHint = BuildRouteHint(model, invocation, syntaxMethodName, callerComponent, relPath, line, row);
                    if (routeHint != null)
                    {
                        allRouteHints.Add(routeHint);
                    }

                    var methodSymbol = ResolveMethod(model, invocation);
                    if (methodSymbol == null)
                    {
                        unresolvedInvocations++;
                        continue;
                    }

                    var targetType = methodSymbol.ContainingType;
                    var targetTypeName = targetType?.Name ?? "unknown";
                    var targetFullName = targetType == null ? "unknown" : CleanSymbol(targetType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
                    var methodName = methodSymbol.Name;

                    var localTarget = localTypesByFullName.ContainsKey(targetFullName) || localTypesBySimpleName.ContainsKey(targetTypeName);
                    if (!localTarget || callerComponent == "unknown")
                    {
                        continue;
                    }

                    allDependencies.Add(new Dictionary<string, object?>
                    {
                        ["dependency_id"] = null,
                        ["kind"] = "roslyn_component_call",
                        ["from"] = callerComponent,
                        ["to"] = targetTypeName + "." + methodName,
                        ["relationship"] = "calls",
                        ["source_file"] = relPath,
                        ["line"] = line,
                        ["evidence"] = callerComponent + "." + callerMethod + " semantically resolves to " + targetFullName + "." + methodName + "()",
                        ["confidence"] = 0.94,
                        ["metadata"] = new Dictionary<string, object?>
                        {
                            ["parser_backend"] = "roslyn_semantic_model",
                            ["source_component"] = callerComponent,
                            ["source_symbol"] = callerFullName,
                            ["source_method"] = callerMethod,
                            ["target_component_or_type"] = targetTypeName,
                            ["target_symbol"] = targetFullName,
                            ["target_method"] = methodName,
                            ["resolution_quality"] = "roslyn_semantic_symbol_binding",
                            ["project"] = row.Project,
                            ["project_path"] = row.ProjectPath
                        }
                    });
                }
            }
        }

        var dedupedDependencies = DeduplicateDependencies(allDependencies)
            .Select((item, index) =>
            {
                item["dependency_id"] = "RDEP-" + (index + 1).ToString("D5");
                return item;
            })
            .ToList();

        var payload = new Dictionary<string, object?>
        {
            ["generated_at"] = DateTimeOffset.UtcNow.ToString("O"),
            ["extractor_version"] = "0.1.0",
            ["status"] = "active",
            ["parser_backend"] = "roslyn_semantic_model",
            ["summary"] = new Dictionary<string, object?>
            {
                ["source_file_count"] = sourceRows.Count,
                ["project_count"] = sourceRows.Select(row => row.Project).Distinct().Count(),
                ["semantic_component_count"] = allComponents.Count,
                ["semantic_dependency_count"] = dedupedDependencies.Count,
                ["semantic_component_call_count"] = dedupedDependencies.Count(item => Convert.ToString(item["kind"]) == "roslyn_component_call"),
                ["semantic_di_registration_count"] = dedupedDependencies.Count(item => Convert.ToString(item["kind"]) == "di_registration"),
                ["route_hint_count"] = allRouteHints.Count,
                ["unresolved_invocation_count"] = unresolvedInvocations,
                ["compilation_error_count_sampled"] = compilationDiagnostics.Count
            },
            ["semantic_components"] = allComponents,
            ["dependency_candidates"] = dedupedDependencies,
            ["route_hints"] = allRouteHints,
            ["diagnostics"] = compilationDiagnostics,
            ["limitations"] = new List<string>
            {
                "Roslyn semantic extraction compiles each project with project-reference source overlays where possible; package symbols may remain unresolved without restored package assemblies.",
                "Runtime dispatch, reflection, generated partial classes, and framework-generated endpoints still require runtime tracing or framework execution evidence."
            }
        };

        Directory.CreateDirectory(Path.GetDirectoryName(outputJson)!);
        File.WriteAllText(outputJson, JsonSerializer.Serialize(payload, JsonOptions) + Environment.NewLine, Encoding.UTF8);
        Console.WriteLine(JsonSerializer.Serialize(payload["summary"], JsonOptions));
        return 0;
    }

    private static Dictionary<string, object?> BuildComponent(INamedTypeSymbol symbol, BaseTypeDeclarationSyntax typeDecl, SyntaxTree tree, SourceFileRecord row)
    {
        var methods = new List<Dictionary<string, object?>>();
        foreach (var member in symbol.GetMembers().OfType<IMethodSymbol>())
        {
            if (member.MethodKind != MethodKind.Ordinary)
            {
                continue;
            }
            if (member.DeclaredAccessibility != Accessibility.Public && member.DeclaredAccessibility != Accessibility.Internal)
            {
                continue;
            }
            methods.Add(new Dictionary<string, object?>
            {
                ["name"] = member.Name,
                ["return_type"] = CleanSymbol(member.ReturnType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)),
                ["parameters"] = member.Parameters.Select(parameter => new Dictionary<string, object?>
                {
                    ["name"] = parameter.Name,
                    ["type"] = CleanSymbol(parameter.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat))
                }).ToList()
            });
        }

        var constructorDependencies = symbol.Constructors
            .Where(ctor => ctor.Parameters.Length > 0)
            .SelectMany(ctor => ctor.Parameters.Select(parameter => new Dictionary<string, object?>
            {
                ["name"] = parameter.Name,
                ["type"] = CleanSymbol(parameter.Type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)),
                ["constructor"] = symbol.Name
            }))
            .ToList();

        return new Dictionary<string, object?>
        {
            ["name"] = symbol.Name,
            ["full_name"] = CleanSymbol(symbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)),
            ["namespace"] = symbol.ContainingNamespace?.IsGlobalNamespace == false ? symbol.ContainingNamespace.ToDisplayString() : null,
            ["kind"] = symbol.TypeKind.ToString(),
            ["file"] = NormalizePath(tree.FilePath),
            ["line"] = LineFor(tree, typeDecl),
            ["project"] = row.Project,
            ["project_type"] = row.ProjectType,
            ["project_category"] = row.ProjectCategory,
            ["base_type"] = symbol.BaseType == null || symbol.BaseType.SpecialType == SpecialType.System_Object ? null : CleanSymbol(symbol.BaseType.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)),
            ["interfaces"] = symbol.Interfaces.Select(item => CleanSymbol(item.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat))).ToList(),
            ["attributes"] = symbol.GetAttributes().Select(attr => attr.AttributeClass?.Name ?? attr.ToString()).Where(value => !string.IsNullOrWhiteSpace(value)).Distinct().ToList(),
            ["public_or_internal_methods"] = methods,
            ["constructor_dependencies"] = constructorDependencies,
            ["confidence"] = 0.96,
            ["semantic_symbol_id"] = CleanSymbol(symbol.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat)),
            ["parser_backend"] = "roslyn_semantic_model"
        };
    }

    private static List<MetadataReference> MetadataReferences()
    {
        var trusted = Convert.ToString(AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES"));
        if (string.IsNullOrWhiteSpace(trusted))
        {
            return new List<MetadataReference>();
        }
        return trusted.Split(Path.PathSeparator)
            .Where(File.Exists)
            .Select(path => MetadataReference.CreateFromFile(path))
            .Cast<MetadataReference>()
            .ToList();
    }

    private static IMethodSymbol? ResolveMethod(SemanticModel model, InvocationExpressionSyntax invocation)
    {
        var info = model.GetSymbolInfo(invocation);
        return info.Symbol as IMethodSymbol ?? info.CandidateSymbols.OfType<IMethodSymbol>().FirstOrDefault();
    }

    private static string ContainingMethodName(SemanticModel model, SyntaxNode node)
    {
        var method = node.Ancestors().OfType<MethodDeclarationSyntax>().FirstOrDefault();
        if (method != null)
        {
            return model.GetDeclaredSymbol(method)?.Name ?? method.Identifier.Text;
        }
        var ctor = node.Ancestors().OfType<ConstructorDeclarationSyntax>().FirstOrDefault();
        if (ctor != null)
        {
            return model.GetDeclaredSymbol(ctor)?.Name ?? ctor.Identifier.Text;
        }
        return "top-level-statements";
    }

    private static string InvokedMethodName(ExpressionSyntax expression)
    {
        if (expression is MemberAccessExpressionSyntax memberAccess)
        {
            return memberAccess.Name switch
            {
                GenericNameSyntax generic => generic.Identifier.Text,
                IdentifierNameSyntax identifier => identifier.Identifier.Text,
                _ => memberAccess.Name.ToString()
            };
        }
        if (expression is GenericNameSyntax genericName)
        {
            return genericName.Identifier.Text;
        }
        if (expression is IdentifierNameSyntax identifierName)
        {
            return identifierName.Identifier.Text;
        }
        return expression.ToString();
    }

    private static bool IsDiRegistration(string methodName)
    {
        return methodName is "AddScoped" or "AddTransient" or "AddSingleton" or "AddDbContext" or "AddHostedService";
    }

    private static Dictionary<string, object?>? BuildDiRegistration(SemanticModel model, InvocationExpressionSyntax invocation, string methodName, string callerComponent, string relPath, int line, SourceFileRecord row)
    {
        var genericName = (invocation.Expression as MemberAccessExpressionSyntax)?.Name as GenericNameSyntax
            ?? invocation.Expression as GenericNameSyntax;
        var typeArgs = genericName?.TypeArgumentList.Arguments ?? default(SeparatedSyntaxList<TypeSyntax>);
        if (typeArgs.Count == 0)
        {
            return null;
        }

        var serviceType = TypeName(model, typeArgs[0]);
        var implementationType = typeArgs.Count > 1 ? TypeName(model, typeArgs[1]) : serviceType;
        var implementationSimple = SimpleName(implementationType);
        var serviceSimple = SimpleName(serviceType);
        return new Dictionary<string, object?>
        {
            ["dependency_id"] = null,
            ["kind"] = "di_registration",
            ["from"] = row.Project,
            ["to"] = implementationSimple,
            ["relationship"] = "registers",
            ["source_file"] = relPath,
            ["line"] = line,
            ["evidence"] = methodName + " semantically registers " + serviceType + " to " + implementationType,
            ["confidence"] = 0.95,
            ["metadata"] = new Dictionary<string, object?>
            {
                ["parser_backend"] = "roslyn_semantic_model",
                ["lifetime"] = methodName,
                ["service"] = serviceSimple,
                ["service_full_name"] = serviceType,
                ["implementation"] = implementationSimple,
                ["implementation_full_name"] = implementationType,
                ["source_component"] = callerComponent,
                ["resolution_quality"] = "roslyn_semantic_type_binding",
                ["project"] = row.Project,
                ["project_path"] = row.ProjectPath
            }
        };
    }

    private static Dictionary<string, object?>? BuildRouteHint(SemanticModel model, InvocationExpressionSyntax invocation, string methodName, string callerComponent, string relPath, int line, SourceFileRecord row)
    {
        if (!methodName.StartsWith("Map", StringComparison.Ordinal) && !methodName.StartsWith("Http", StringComparison.Ordinal))
        {
            return null;
        }
        var firstArg = invocation.ArgumentList.Arguments.FirstOrDefault()?.Expression;
        var constant = firstArg == null ? default(Optional<object?>) : model.GetConstantValue(firstArg);
        var path = constant.HasValue ? Convert.ToString(constant.Value) : null;
        if (string.IsNullOrWhiteSpace(path) && !methodName.Contains("Controller", StringComparison.OrdinalIgnoreCase) && !methodName.Contains("Razor", StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }
        return new Dictionary<string, object?>
        {
            ["kind"] = "roslyn_route_hint",
            ["method"] = methodName,
            ["path_or_name"] = path ?? methodName,
            ["owning_component"] = callerComponent,
            ["source_file"] = relPath,
            ["line"] = line,
            ["project"] = row.Project,
            ["confidence"] = string.IsNullOrWhiteSpace(path) ? 0.72 : 0.9,
            ["evidence"] = "Roslyn semantic invocation hint for " + methodName
        };
    }

    private static string TypeName(SemanticModel model, TypeSyntax syntax)
    {
        var type = model.GetTypeInfo(syntax).Type;
        return type == null ? syntax.ToString() : CleanSymbol(type.ToDisplayString(SymbolDisplayFormat.FullyQualifiedFormat));
    }

    private static string SimpleName(string value)
    {
        var cleaned = CleanSymbol(value);
        var generic = cleaned.IndexOf('<');
        if (generic >= 0)
        {
            cleaned = cleaned.Substring(0, generic);
        }
        var dot = cleaned.LastIndexOf('.');
        return dot >= 0 ? cleaned.Substring(dot + 1) : cleaned;
    }

    private static string CleanSymbol(string value)
    {
        return value.Replace("global::", "").Trim();
    }

    private static int LineFor(SyntaxTree tree, SyntaxNode node)
    {
        return tree.GetLineSpan(node.Span).StartLinePosition.Line + 1;
    }

    private static string NormalizePath(string path)
    {
        return path.Replace('\\', '/');
    }

    private static string SafeId(string value)
    {
        return new string(value.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_').ToArray());
    }

    private static List<Dictionary<string, object?>> DeduplicateDependencies(List<Dictionary<string, object?>> dependencies)
    {
        var seen = new HashSet<string>();
        var result = new List<Dictionary<string, object?>>();
        foreach (var dependency in dependencies)
        {
            var marker = string.Join("|", new[]
            {
                Convert.ToString(dependency.GetValueOrDefault("kind")) ?? "",
                Convert.ToString(dependency.GetValueOrDefault("from")) ?? "",
                Convert.ToString(dependency.GetValueOrDefault("to")) ?? "",
                Convert.ToString(dependency.GetValueOrDefault("source_file")) ?? "",
                Convert.ToString(dependency.GetValueOrDefault("line")) ?? ""
            });
            if (seen.Add(marker))
            {
                result.Add(dependency);
            }
        }
        return result;
    }
}
'''


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def normalize_slashes(value: str) -> str:
    return value.replace("\\", "/")


def normalize_pure_posix(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def find_dotnet_executable(output_root: Path) -> Path | None:
    existing = shutil.which("dotnet")
    if existing:
        return Path(existing)
    candidates = [
        Path.home() / ".dotnet8" / "dotnet.exe",
        Path.home() / ".dotnet" / "dotnet.exe",
        output_root / "dotnet" / "dotnet.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def sdk_version_key(path: Path) -> tuple[int, ...]:
    parts = []
    for item in re.split(r"[.-]", path.name):
        try:
            parts.append(int(item))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def find_roslyn_bincore(dotnet: Path) -> Path | None:
    roots = [dotnet.parent]
    roots.append(Path.home() / ".dotnet8")
    roots.append(Path.home() / ".dotnet")
    for root in roots:
        sdk_root = root / "sdk"
        if not sdk_root.exists():
            continue
        for sdk_dir in sorted([item for item in sdk_root.iterdir() if item.is_dir()], key=sdk_version_key, reverse=True):
            bincore = sdk_dir / "Roslyn" / "bincore"
            if (bincore / "Microsoft.CodeAnalysis.dll").exists() and (bincore / "Microsoft.CodeAnalysis.CSharp.dll").exists():
                return bincore
    return None


def resolve_project_references(project_inventory: dict[str, Any]) -> dict[str, list[str]]:
    by_path = {normalize_slashes(project["path"]): project for project in project_inventory.get("projects", [])}
    by_name: dict[str, list[str]] = {}
    for project in project_inventory.get("projects", []):
        names: list[str] = []
        base = PurePosixPath(normalize_slashes(project.get("source_path", "")))
        for reference in project.get("project_references", []) or []:
            resolved = normalize_pure_posix(base / PurePosixPath(normalize_slashes(reference)))
            target = by_path.get(resolved)
            if target:
                names.append(target.get("name", "unknown"))
        by_name[project.get("name", "unknown")] = sorted(set(names))
    return by_name


def project_for_file(path: str, projects: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [
        project
        for project in projects
        if path == normalize_slashes(project.get("source_path", "")).rstrip("/")
        or path.startswith(normalize_slashes(project.get("source_path", "")).rstrip("/") + "/")
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda item: len(item.get("source_path", "")), reverse=True)[0]


def is_generated_or_low_value_csharp(path: str) -> bool:
    lower = "/" + normalize_slashes(path).lower()
    return (
        "/migrations/" in lower
        or lower.endswith("modelsnapshot.cs")
        or lower.endswith(".designer.cs")
        or lower.endswith(".g.cs")
        or lower.endswith(".generated.cs")
        or "/bin/" in lower
        or "/obj/" in lower
    )


def build_source_rows(file_inventory: dict[str, Any], project_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    projects = project_inventory.get("projects", [])
    references_by_project = resolve_project_references(project_inventory)
    rows: list[dict[str, Any]] = []
    for record in file_inventory.get("files", []):
        path = normalize_slashes(record.get("path", ""))
        if record.get("language") != "csharp" or not path.endswith(".cs") or is_generated_or_low_value_csharp(path):
            continue
        project = project_for_file(path, projects)
        rows.append(
            {
                "path": path,
                "project": project.get("name", "unknown") if project else "unknown",
                "projectPath": normalize_slashes(project.get("path", "unknown")) if project else "unknown",
                "projectType": project.get("type", "unknown") if project else "unknown",
                "projectCategory": project.get("category", "unknown") if project else "unknown",
                "projectReferences": references_by_project.get(project.get("name", "unknown") if project else "unknown", []),
            }
        )
    return rows


def unavailable_payload(status: str, reason: str, source_file_count: int = 0) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "extractor_version": EXTRACTOR_VERSION,
        "status": status,
        "parser_backend": "roslyn_semantic_model",
        "summary": {
            "source_file_count": source_file_count,
            "project_count": 0,
            "semantic_component_count": 0,
            "semantic_dependency_count": 0,
            "semantic_component_call_count": 0,
            "semantic_di_registration_count": 0,
            "route_hint_count": 0,
            "unresolved_invocation_count": 0,
            "compilation_error_count_sampled": 0,
        },
        "semantic_components": [],
        "dependency_candidates": [],
        "route_hints": [],
        "diagnostics": [],
        "limitations": [reason],
    }


def write_extractor_project(tool_dir: Path, roslyn_bincore: Path) -> Path:
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "Program.cs").write_text(CSHARP_EXTRACTOR_SOURCE, encoding="utf-8")
    code_analysis = html.escape(str(roslyn_bincore / "Microsoft.CodeAnalysis.dll"))
    code_analysis_csharp = html.escape(str(roslyn_bincore / "Microsoft.CodeAnalysis.CSharp.dll"))
    csproj = f"""<Project Sdk=\"Microsoft.NET.Sdk\">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <RestoreIgnoreFailedSources>true</RestoreIgnoreFailedSources>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include=\"Microsoft.CodeAnalysis\" HintPath=\"{code_analysis}\" />
    <Reference Include=\"Microsoft.CodeAnalysis.CSharp\" HintPath=\"{code_analysis_csharp}\" />
  </ItemGroup>
</Project>
"""
    (tool_dir / "RoslynSemanticExtractor.csproj").write_text(csproj, encoding="utf-8")
    return tool_dir / "RoslynSemanticExtractor.csproj"


def run_roslyn_extractor(
    dotnet: Path,
    roslyn_bincore: Path,
    repo_root: Path,
    output_root: Path,
    source_rows: list[dict[str, Any]],
) -> tuple[int, str, str]:
    cache_root = output_root / "tool-cache" / "roslyn-semantic-extractor"
    csproj = write_extractor_project(cache_root, roslyn_bincore)
    source_list = output_root / "tool-cache" / "roslyn-source-files.json"
    write_json(source_list, source_rows)
    output_file = output_root / "parsed" / "roslyn-semantic-facts.json"
    env = os.environ.copy()
    env["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    result = subprocess.run(
        [
            str(dotnet),
            "run",
            "--project",
            str(csproj),
            "--",
            str(repo_root),
            str(output_file),
            str(source_list),
        ],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
        env=env,
        timeout=180,
    )
    return result.returncode, result.stdout[-4000:], result.stderr[-4000:]


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    inventory_root = output_root / "inventory"
    parsed_root = output_root / "parsed"
    output_file = parsed_root / "roslyn-semantic-facts.json"

    file_inventory = load_json(inventory_root / "file-inventory.json")
    project_inventory = load_json(inventory_root / "project-inventory.json")
    language_summary = load_json(inventory_root / "language-summary.json")
    languages = {item.get("language") for item in language_summary.get("languages", [])}
    source_rows = build_source_rows(file_inventory, project_inventory)

    if "csharp" not in languages or not source_rows:
        write_json(output_file, unavailable_payload("not_applicable", "No C# source files were detected by inventory.", len(source_rows)))
        print(json.dumps({"status": "not_applicable", "semantic_component_count": 0}, indent=2))
        return 0

    dotnet = find_dotnet_executable(output_root)
    if dotnet is None:
        write_json(output_file, unavailable_payload("unavailable", "dotnet executable was not found; Roslyn semantic extraction was skipped.", len(source_rows)))
        print(json.dumps({"status": "unavailable", "reason": "dotnet executable was not found"}, indent=2))
        return 0

    roslyn_bincore = find_roslyn_bincore(dotnet)
    if roslyn_bincore is None:
        write_json(output_file, unavailable_payload("unavailable", "Roslyn compiler assemblies were not found in the local .NET SDK.", len(source_rows)))
        print(json.dumps({"status": "unavailable", "reason": "Roslyn compiler assemblies were not found"}, indent=2))
        return 0

    try:
        returncode, stdout, stderr = run_roslyn_extractor(dotnet, roslyn_bincore, repo_root, output_root, source_rows)
    except Exception as exc:  # noqa: BLE001 - preserve pipeline artifact on semantic extractor failure.
        payload = unavailable_payload("error", f"Roslyn semantic extraction failed: {exc}", len(source_rows))
        payload["diagnostics"].append({"error": str(exc), "type": exc.__class__.__name__})
        write_json(output_file, payload)
        print(json.dumps({"status": "error", "reason": str(exc)}, indent=2))
        return 0

    if returncode != 0 or not output_file.exists():
        payload = unavailable_payload("error", "Roslyn semantic extractor returned a non-zero exit code.", len(source_rows))
        payload["diagnostics"].append({"returncode": returncode, "stdout": stdout, "stderr": stderr})
        write_json(output_file, payload)
        print(json.dumps({"status": "error", "returncode": returncode, "stderr": stderr[-1000:]}, indent=2))
        return 0

    payload = load_json(output_file)
    payload["dotnet_executable"] = str(dotnet)
    payload["roslyn_bincore"] = str(roslyn_bincore)
    payload["tool_cache"] = str(output_root / "tool-cache" / "roslyn-semantic-extractor")
    write_json(output_file, payload)
    print(json.dumps({"status": payload.get("status"), "summary": payload.get("summary", {})}, indent=2))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract C# semantic facts with Roslyn when a local .NET SDK is available.")
    parser.add_argument("--repo-root", default=".", help="Legacy repository root. Defaults to current directory.")
    parser.add_argument("--output-root", default="architecture-output", help="Architecture output root.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
