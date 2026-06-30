# 12. Technology Blueprint — eShopOnWeb

**Forward Engineering Document 12 of 20**
**Generated:** 2026-06-30
**Pipeline Stage:** Forward Engineering (Layer 6)
**Source Foundation:** ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md
**Confidence Schema:** HIGH = direct code evidence; MEDIUM = structural inference; LOW = convention assumption.

---

## Document Purpose

This document records the complete current technology stack (22 TECH-CUR nodes + 6 TECH-INF nodes), documents security components (7 TECH-SEC nodes), presents technology-neutral target stack options for each layer, and provides a concrete migration path. It also resolves **GR-08** — the open gate requiring explicit target stack selection before code generation can begin.

**Key principle:** Sections 2–4 describe the *current (legacy)* state with evidence. Sections 5–7 present *neutral target options* — no technology named in those sections exists in the foundation evidence as a confirmed target. Section 8 resolves GR-08 with the recommended stack decision.

---

## 12.1 Current Architecture Overview

eShopOnWeb is a **.NET 8 layered monolith** with three deployable runtime units:

| Unit | Node | Type | Port |
|---|---|---|---|
| eshopwebmvc | APP-IF-001 | ASP.NET Core MVC + BlazorAdmin WASM host | 5106:8080 (Docker), 44315 (dev HTTPS) |
| eshoppublicapi | APP-IF-002 | ASP.NET Core REST API | 5200:8080 (Docker), 5099 (dev HTTPS) |
| sqlserver | TECH-INF-003 | SQL Server (Azure SQL Edge — EOL) | 1433:1433 |

Supporting non-deployable libraries:
- APP-IF-004 (ApplicationCore) — zero outbound project references (domain isolation)
- APP-IF-005 (Infrastructure) — EF Core, Identity, JWT
- APP-IF-003 (BlazorAdmin) — WASM SPA served from APP-IF-001
- APP-IF-006 (BlazorShared) — shared contracts for BlazorAdmin + PublicApi

---

## 12.2 Current Technology Stack — All 22 TECH-CUR Nodes

### 12.2.1 Runtime and Language

| ID | Technology | Version | Category | EOL / Risk | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-001 | .NET 8 / ASP.NET Core SDK | 8.0.x | Runtime/SDK | LTS until November 2026 | HIGH |
| TECH-CUR-002 | C# (LangVersion=latest) | C# 12 | Language | Current | HIGH |

### 12.2.2 Web and API Frameworks

| ID | Technology | Version | Category | Notes | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-003 | ASP.NET Core MVC | 8.0 | Web Framework | Powers eshopwebmvc storefront | HIGH |
| TECH-CUR-004 | ASP.NET Core Web API + Ardalis.ApiEndpoints | 8.0 | API Framework | Powers eshoppublicapi (APP-IF-002) | HIGH |
| TECH-CUR-005 | Blazor WebAssembly | 8.0 | Frontend Framework | BlazorAdmin SPA (APP-IF-003) served from Web host | HIGH |

### 12.2.3 Data Access

| ID | Technology | Version | Category | Notes | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-006 | Entity Framework Core (SQL Server provider) | UNKNOWN | ORM | CatalogContext + AppIdentityDbContext; HiLo sequences for Catalog entities | MEDIUM |
| TECH-CUR-009 | Ardalis.Specification + EFCore provider | UNKNOWN | Repository Pattern | All repository queries use specification pattern | HIGH |

### 12.2.4 Authentication and Authorization

| ID | Technology | Version | Category | Notes | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-007 | ASP.NET Core Identity (EntityFrameworkCore) | UNKNOWN | Auth Framework | Cookie auth for Web MVC; Identity store in IdentityDatabase | HIGH |
| TECH-CUR-008 | JWT Bearer Authentication | UNKNOWN | Auth | Token auth for PublicApi; **key hardcoded — CRITICAL (BR-32)** | HIGH |

### 12.2.5 Application Layer Libraries

| ID | Technology | Version | Category | Notes | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-010 | MediatR | UNKNOWN | CQRS Mediator | Used in Web layer only — NOT in PublicApi | HIGH |
| TECH-CUR-011 | AutoMapper | UNKNOWN | DTO Mapping | Object mapping across application layers | HIGH |
| TECH-CUR-020 | Ardalis.GuardClauses + Ardalis.Result | UNKNOWN | Domain Utilities | Guard clauses in all entity constructors | HIGH |

### 12.2.6 Frontend and Validation

| ID | Technology | Version | Category | Risk | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-012 | Blazored.LocalStorage | UNKNOWN | Browser Storage | XSS risk — JWT token stored here (TD-03) | HIGH |
| TECH-CUR-013 | FluentValidation (BlazorShared) | UNKNOWN | Validation | Shared request validation | HIGH |

### 12.2.7 API Documentation

| ID | Technology | Version | Category | Risk | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-014 | Swashbuckle.AspNetCore (Swagger/OpenAPI) | UNKNOWN | API Documentation | Must be gated behind IsDevelopment() (ASMP-005) | HIGH |

### 12.2.8 Cloud and Secrets Management

| ID | Technology | Version | Category | Notes | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-015 | Azure.Identity + Azure Key Vault config | UNKNOWN | Cloud Secret Management | Active on Azure path only; not wired for local dev (TD gap) | HIGH |

### 12.2.9 Infrastructure and CI/CD

| ID | Technology | Version | Category | Risk | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-016 | Docker Compose v3.4 + .NET 8 multi-stage build | 3.4 | Container Orchestration | Current | HIGH |
| TECH-CUR-017 | GitHub Actions CI (ubuntu-latest, dotnet 8.0.x) | N/A | CI/CD | No secret scanning (TD-02) | HIGH |

### 12.2.10 Testing

| ID | Technology | Version | Category | Risk | Confidence |
|---|---|---|---|---|---|
| TECH-CUR-018 | xUnit + NSubstitute (3 test projects) | UNKNOWN | Test Framework (primary) | Current standard | HIGH |
| TECH-CUR-019 | MSTest (PublicApiIntegrationTests only) | UNKNOWN | Test Framework (inconsistent) | TD-18 — mixed with xUnit; standardize on xUnit | HIGH |

### 12.2.11 Deprecated / EOL Components (Action Required)

| ID | Technology | Category | Risk Level | Remediation |
|---|---|---|---|---|
| TECH-CUR-021 | BlazorInputFile (superseded package) | UI Component | MEDIUM | Replace with .NET 5+ built-in `InputFile` |
| TECH-CUR-022 | BuildBundlerMinifier (deprecated) | Build Tool | MEDIUM | Migrate to Webpack/esbuild |

---

## 12.3 Current Infrastructure Stack — All 6 TECH-INF Nodes

| ID | Name | Type | Image / Provider | Ports | Risk | Confidence |
|---|---|---|---|---|---|---|
| TECH-INF-001 | eshopwebmvc Container | Docker Container | mcr.microsoft.com/dotnet/aspnet:8.0 | 5106:8080 | None | HIGH |
| TECH-INF-002 | eshoppublicapi Container | Docker Container | mcr.microsoft.com/dotnet/aspnet:8.0 | 5200:8080 | None | HIGH |
| TECH-INF-003 | sqlserver Container | Docker — SQL Server | mcr.microsoft.com/azure-sql-edge (no version pin) | 1433:1433 | **CRITICAL: EOL March 2025; SA_PASSWORD hardcoded** | HIGH |
| TECH-INF-004 | Azure Key Vault | Cloud Secret Management | Azure | N/A | Active on Azure deploy path only | HIGH |
| TECH-INF-005 | Azure App Service / Container Apps | Cloud Compute (inferred) | Azure | N/A | LOW confidence — inferred from abbreviations.json | LOW |
| TECH-INF-006 | Azure Developer CLI (azd) IaC | Infrastructure as Code | Azure Bicep | N/A | Bicep templates present but not fully extracted | HIGH |

### 12.3.1 Infrastructure Critical Issues

**TECH-INF-003 — SQL Server container (3 distinct issues):**

1. **EOL engine (TD-04):** Azure SQL Edge reached end-of-life March 2025. Must replace with `mcr.microsoft.com/mssql/server:2022-latest`.
2. **No version pin (TD-05):** `latest`-style tag means builds are non-deterministic. Must pin to exact version tag.
3. **Hardcoded SA password (TECH-SEC-007, TD-01):** `SA_PASSWORD=@someThingComplicated1234` is committed in docker-compose.yml. CRITICAL — must move to Docker secret or environment variable.

---

## 12.4 Current Security Posture — All 7 TECH-SEC Nodes

| ID | Name | Type | Risk Level | Notes |
|---|---|---|---|---|
| TECH-SEC-001 | ASP.NET Core Identity (Cookie Auth) | Authentication | Low | Standard cookie auth for Web MVC; HIGH confidence |
| TECH-SEC-002 | JWT Bearer Authentication | Authentication — Token | **CRITICAL** | Key hardcoded in AuthorizationConstants.cs:12 (BR-32) |
| TECH-SEC-003 | Claims-Based Authorisation | Authorisation | Low | System.Security.Claims; standard |
| TECH-SEC-004 | Azure Managed Identity / DefaultAzureCredential | Cloud Identity | Low | Active on Azure path only |
| TECH-SEC-005 | ASP.NET Core User Secrets (dev) | Dev Secret Management | Low | Development environment only |
| TECH-SEC-006 | CSRF Anti-Forgery Tokens | Request Forgery Protection | Low | Web MVC forms + Identity UI |
| TECH-SEC-007 | SA Password Hardcoded | **VULNERABILITY** | **CRITICAL** | docker-compose.yml: SA_PASSWORD=@someThingComplicated1234 |

---

## 12.5 Target Backend Stack Options (Neutral — Not in Legacy Evidence)

The foundation evidence contains zero TECH-TGT nodes. The following options are offered as neutral choices covering the full supported candidate set. None is currently implemented.

### Option A — Lowest Delta (.NET 8 continued)

**Rationale:** Preserves the current runtime investment; requires no language migration; Clean Architecture boundaries are already partially established.

| Layer | Current | Target (Option A) |
|---|---|---|
| Runtime | .NET 8 (TECH-CUR-001) | .NET 9 LTS (when released) / remain .NET 8 |
| Language | C# 12 (TECH-CUR-002) | C# 13 |
| Web/API Framework | ASP.NET Core MVC + Web API (TECH-CUR-003, 004) | ASP.NET Core Minimal APIs or retained Web API |
| ORM | EF Core + SQL Server (TECH-CUR-006) | EF Core 9 with PostgreSQL or SQL Server |
| Auth | ASP.NET Core Identity + JWT (TECH-CUR-007, 008) | ASP.NET Core Identity + OpenIddict or Duende IdentityServer |
| CQRS | MediatR (TECH-CUR-010) | MediatR 12+ |
| Validation | FluentValidation (TECH-CUR-013) | FluentValidation 11+ |
| Mapping | AutoMapper (TECH-CUR-011) | AutoMapper or Mapperly (compile-time) |
| API Docs | Swashbuckle (TECH-CUR-014) | Microsoft.AspNetCore.OpenApi (built-in, .NET 9) |

### Option B — JVM Stack (Java Spring Boot)

| Concern | Current (legacy) | Java/Spring Target |
|---|---|---|
| Runtime | .NET 8 | JDK 21 LTS |
| Framework | ASP.NET Core | Spring Boot 3.x |
| ORM | EF Core | Spring Data JPA / Hibernate |
| DI Container | ASP.NET Core DI | Spring DI / @Component |
| Validation | FluentValidation | Jakarta Bean Validation (Hibernate Validator) |
| CQRS/Mediator | MediatR | Spring Application Events or Axon Framework |
| Auth | ASP.NET Core Identity + JWT | Spring Security + OAuth2 Resource Server |
| OpenAPI | Swashbuckle | springdoc-openapi |
| Testing | xUnit + NSubstitute | JUnit 5 + Mockito |

**Concept mapping for key patterns:**

| eShopOnWeb Concept | Java Equivalent |
|---|---|
| `IRepository<T>` (Ardalis) | `JpaRepository<T, ID>` (Spring Data) |
| `Ardalis.Specification` | Spring Data `Specification<T>` (JPA Criteria) |
| `IEntityTypeConfiguration<T>` | `@Entity` + `@Table` + Jakarta Persistence annotations |
| `GuardClauses` | Custom Preconditions or Guava |
| `HiLo ID strategy` | `@GenericGenerator(strategy="org.hibernate.id.enhanced.SequenceStyleGenerator")` with hilo optimizer |

### Option C — Node.js / TypeScript Stack

| Concern | Current (legacy) | Node.js Target |
|---|---|---|
| Runtime | .NET 8 | Node.js 22 LTS |
| Framework | ASP.NET Core | NestJS (TypeScript, DI, decorators) or Express + tRPC |
| ORM | EF Core | Prisma (SQL Server/PostgreSQL) or TypeORM |
| Auth | Identity + JWT | Passport.js + jsonwebtoken or Auth0 |
| Validation | FluentValidation | Zod or class-validator |
| Testing | xUnit | Jest + Supertest |

### Option D — Python Stack

| Concern | Current (legacy) | Python Target |
|---|---|---|
| Runtime | .NET 8 | Python 3.12 |
| Framework | ASP.NET Core | FastAPI (async, OpenAPI native) |
| ORM | EF Core | SQLAlchemy 2.0 + Alembic (migrations) |
| Auth | Identity + JWT | python-jose + fastapi-users |
| Validation | FluentValidation | Pydantic v2 |
| Testing | xUnit | pytest + httpx |

---

## 12.6 Target Database Options (Neutral)

Both DATA-REPO-001 (CatalogDatabase) and DATA-REPO-002 (IdentityDatabase) currently run on SQL Server (Azure SQL Edge EOL).

| Database Engine | Compatibility Notes | Migration Effort |
|---|---|---|
| **SQL Server 2022** (mcr.microsoft.com/mssql/server:2022-latest) | Drop-in replacement for current EOL image; HiLo sequences preserved; zero schema migration | **Lowest** — replace Docker image only |
| **PostgreSQL 16** | HiLo supported (Npgsql EF Core provider: `.UseHiLo()`); column types translate directly; IDENTITY becomes SERIAL/BIGSERIAL | Low-Medium — change EF Core provider + update column types |
| **MySQL 8** | HiLo not natively supported; must use sequence emulation; nvarchar → varchar; decimal(18,2) → DECIMAL(18,2) | Medium — provider swap + schema adjustments |

**Database constraints carried forward regardless of engine choice:**
- HiLo sequences for CatalogItem (`catalog_hilo`), CatalogBrand (`catalog_brand_hilo`), CatalogType (`catalog_type_hilo`) — DATA-REPO-001
- IDENTITY for Basket, Order entities
- Standard Identity string GUIDs for IdentityDatabase
- Two distinct connection strings: `CatalogConnection` and `IdentityConnection`
- Cross-database soft references (no FK): `Baskets.BuyerId` → `AspNetUsers.Id`, `Orders.BuyerId` → `AspNetUsers.Id`

---

## 12.7 Target Deployment Options (Neutral)

### Option 1 — Docker Compose (Evolves Current)

Minimal change from current. Resolves all 3 TECH-INF-003 critical issues:
- Replace `azure-sql-edge` with `mssql/server:2022-latest` (TD-04 fix)
- Pin exact version tag (TD-05 fix)
- Move SA_PASSWORD to Docker secret or environment variable (TD-01 / TECH-SEC-007 fix)
- Add health checks to all 3 containers (TD-08, TD-11 fix)

### Option 2 — Kubernetes

For teams requiring production-grade orchestration:
- Each deployable unit (APP-IF-001, APP-IF-002) becomes a Kubernetes Deployment
- Secrets managed via Kubernetes Secrets or External Secrets Operator + TECH-INF-004 (Azure Key Vault)
- Health probes: `livenessProbe` + `readinessProbe` on `/health` and `/health/ready`
- Horizontal Pod Autoscaler on CPU utilization

### Option 3 — Azure App Service / Container Apps (Inferred — TECH-INF-005, TECH-INF-006)

The foundation contains `infra/main.parameters.json` and `azure.yaml` (azd IaC). This path uses:
- Azure Developer CLI (TECH-INF-006) for infrastructure provisioning
- Azure Key Vault (TECH-INF-004) for all secrets
- Azure Managed Identity / DefaultAzureCredential (TECH-SEC-004) for Key Vault access
- **Note (LOW confidence):** No Bicep templates were fully extracted; Azure resources are inferred from `abbreviations.json`

---

## 12.8 Architecture Style Decision (Modular Monolith vs Microservices)

### Current State Assessment

| Module | Boundary Strength | Migration Readiness | Coupling Score |
|---|---|---|---|
| MOD-004 (Catalog) | Weak | Blocked | 13 |
| MOD-003 (Basket) | Weak | Blocked | 9 |
| MOD-009 (Order) | Weak | Blocked | 4 |
| MOD-007 (Identity) | Weak | Blocked | 6 |
| MOD-001 (Admin/BlazorAdmin) | Weak | Blocked | 5 |
| MOD-010 (PublicApi) | Strong | Needs Refactoring | N/A |

**Module dependency cycle (ARCH-VIOL-008):** Admin → ApplicationCore → Basket → Catalog → DataAccess → Identity → Order → Web → (back to Admin). All 13 modules have weak or medium boundaries. No module is currently ready for independent extraction.

### Option A — Modular Monolith (Recommended Starting Point)

**Rationale:** Given that all 13 modules are "Blocked" or "Needs Refactoring" for migration readiness, a modular monolith approach resolves architectural violations within a single deployable unit first, then allows strangler-fig extraction of individual BCs as boundaries harden.

Recommended sequence:
1. Resolve ARCH-VIOL-001..011 (clean module boundaries, remove cycles, enforce dependency direction)
2. Harden BC-04 (Catalog — largest, most independent) boundary first
3. Harden BC-01 (Identity) and BC-02 (Basket) next
4. Extract BC-03 (Order) once BC-02 boundary is stable
5. Defer BC-05 (Admin), BC-06 (Buyer — DORMANT), BC-07 (Infrastructure) until post-extraction

### Option B — Microservices

**Not recommended as starting point** given the current violation density. All 13 modules are "Blocked" — microservices would distribute the existing coupling debt across network boundaries, creating distributed monolith anti-patterns. Microservices extraction should begin only after Option A phases 1-2 are complete.

If microservices is the target, the extraction order (based on coupling scores, boundary strength, and business capability cohesion):
1. BC-04 (Catalog) — most self-contained public API surface; APP-API-002..008
2. BC-01 (Identity) — clear database boundary (IdentityDatabase separate from CatalogDatabase)
3. BC-02 (Basket) → BC-03 (Order) — require saga pattern for checkout flow (EVT-04/EVT-06)
4. BC-05 (Admin/BlazorAdmin) — last; depends on Catalog and Identity
5. BC-06 (Buyer) — DORMANT; defer until AO-05 payment integration

---

## 12.9 GR-08 Resolution — Target Stack Decision

**GR-08 Definition:** "The target technology stack must be explicitly selected and documented before forward engineering code generation (Waves 1-5) can begin. Code generation for FE-01 through FE-20 is BLOCKED until GR-08 is resolved."

**GR-08 is currently OPEN (NEUTRAL-OPTION) — selection required.**

### Decision Template

To resolve GR-08, a human architect must confirm one of the following combinations:

| Decision Point | Options | Selection Required |
|---|---|---|
| Backend runtime | .NET 8/9, Java 21, Node.js 22, Python 3.12 | [SELECT ONE] |
| Web/API framework | ASP.NET Core, Spring Boot, NestJS, FastAPI | [SELECT ONE] |
| ORM / Data access | EF Core, Hibernate, Prisma, SQLAlchemy | [SELECT ONE] |
| Database engine | SQL Server 2022, PostgreSQL 16, MySQL 8 | [SELECT ONE] |
| Auth mechanism | ASP.NET Identity+JWT, Spring Security, Passport.js, fastapi-users | [SELECT ONE] |
| Deployment target | Docker Compose, Kubernetes, Azure Container Apps | [SELECT ONE] |
| Architecture style | Modular Monolith (recommended), Microservices | [SELECT ONE] |

**Recommended default (lowest delta, maximum fidelity to source architecture):**

| Layer | Recommended Default |
|---|---|
| Backend runtime | .NET 8 (TECH-CUR-001) |
| API framework | ASP.NET Core + Ardalis.ApiEndpoints (TECH-CUR-004) |
| ORM | Entity Framework Core 8 + SQL Server provider (TECH-CUR-006) |
| Database | SQL Server 2022 (replaces EOL TECH-INF-003) |
| Auth | ASP.NET Core Identity + JWT Bearer (TECH-CUR-007, 008) |
| Deployment | Docker Compose (hardened) → Azure Container Apps |
| Architecture style | Modular Monolith → strangler-fig to microservices |

**Until GR-08 is explicitly resolved with a written stack decision, Wave 1 code generation (FE-01 through FE-04) MUST NOT begin.**

---

## 12.10 Migration Path Summary

### Phase 1 — Critical Fixes (Pre-Any-Code-Generation)

| Action | Node Reference | FE Document |
|---|---|---|
| Replace Azure SQL Edge with SQL Server 2022 image | TECH-INF-003, TD-04 | FE-20 |
| Pin SQL Server Docker image version | TD-05 | FE-20 |
| Remove hardcoded SA_PASSWORD from docker-compose.yml | TECH-SEC-007, TD-01 | FE-17, FE-20 |
| Remove hardcoded JWT key from AuthorizationConstants.cs | TECH-SEC-002, BR-32 | FE-15, FE-17 |
| Remove hardcoded seeded passwords | BR-29 | FE-15, FE-17 |
| Remove `await Task.Delay(1000)` from catalog endpoint | BR-09, APP-API-004 | FE-14 |

### Phase 2 — Architecture Violations (Wave 1-4)

| Action | Node Reference | FE Document |
|---|---|---|
| Replace direct EfRepository injection in 6 endpoints | ARCH-VIOL-001..007 | FE-13, FE-14 |
| Remove ApplicationCore → BlazorShared reference | ARCH-VIOL-011 | FE-01 |
| Resolve module dependency cycle | ARCH-VIOL-008 | FE-01 |

### Phase 3 — Deprecated Components (Wave 5)

| Action | Node Reference | FE Document |
|---|---|---|
| Replace BlazorInputFile with built-in InputFile | TECH-CUR-021, TD-16 | FE-20 |
| Replace BuildBundlerMinifier | TECH-CUR-022, TD-15 | FE-20 |
| Standardize on xUnit (remove MSTest) | TECH-CUR-019, TD-18 | FE-20 |
| Add secret scanning to GitHub Actions | TECH-CUR-017, TD-02 | FE-20 |

---

## 12.11 Node-to-Blueprint Traceability

| Node Range | Blueprint Section |
|---|---|
| TECH-CUR-001..022 | §12.2 Current Technology Stack |
| TECH-INF-001..006 | §12.3 Current Infrastructure Stack |
| TECH-SEC-001..007 | §12.4 Current Security Posture |
| APP-IF-001..006 | §12.1 Current Architecture Overview |
| DATA-REPO-001..002 | §12.6 Target Database Options |
| MOD-001..013 | §12.8 Architecture Style Decision |
| TD-01..22 (Critical/High) | §12.10 Migration Path |
| GR-08 | §12.9 GR-08 Resolution |

---

*Document 12 of 20 — Technology Blueprint*
*All current-state facts trace to TECH-CUR, TECH-INF, TECH-SEC node IDs in ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*Target options are neutral choices — none is a discovered fact from the foundation evidence.*
*GR-08 remains OPEN until a human architect selects the target stack.*
