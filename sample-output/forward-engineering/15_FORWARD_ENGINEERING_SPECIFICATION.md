# 15. Forward Engineering Master Specification — eShopOnWeb

**Forward Engineering Document 15 of 20**
**Generated:** 2026-06-30
**Pipeline Stage:** Forward Engineering (Layer 6)
**Source Foundation:** ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md + CANONICAL_ENTERPRISE_MODEL.md + FORWARD_ENGINEERING_INPUT_MAP.md
**Authority:** This document is the master specification. It governs all 20 FE documents (FE-01 through FE-20). In any conflict between this document and a specific FE document, this document takes precedence.

---

## Document Purpose

This is the master specification that ties all 14 preceding forward engineering documents together (FE-01 through FE-14) and defines the governance rules for the remaining 5 code-generation documents (FE-15 through FE-20). It specifies:
1. The Wave 1-5 execution order for code generation
2. The GR-08 blocking gate and resolution criteria
3. All 11 architecture violations that must NOT be carried forward
4. The production-readiness remediation plan (AO-01 through AO-10)
5. Code generation readiness status per bounded context
6. The complete rule grammar and validation checklist

---

## 15.0 Governing Principles

### 15.0.1 Authority Hierarchy

| Level | Document | Authority |
|---|---|---|
| 1 (Highest) | This document (FE-15 Master Spec) | Overrides all other FE documents on conflicts |
| 2 | FE-13 Security Architecture | Overrides tech decisions on security matters |
| 3 | FE-14 NFR Specification | Overrides tech decisions on quality targets |
| 4 | FE-11 API Contract Specification | Governs all endpoint/schema decisions |
| 5 | FE-12 Technology Blueprint | Governs stack selection decisions |
| 6–14 | FE-01 through FE-10 | Domain and application layer specs |
| 15–20 | FE-15 through FE-20 | Infrastructure and delivery specs |

### 15.0.2 Rule Grammar

| Keyword | Meaning |
|---|---|
| MUST | Mandatory. Non-compliance blocks release. |
| MUST NOT | Prohibited. Non-compliance blocks release. |
| SHOULD | Strongly recommended. Deviation requires documented justification. |
| MAY | Optional. Implementation team's discretion. |
| `[GATE]` | This rule is release-blocking. No code generation wave proceeds past this point until the gate condition is satisfied. |
| `[NEUTRAL-OPTION]` | A human decision is required. No default is imposed. Code generation is blocked until selection is recorded. |

### 15.0.3 Status Flags

All generated artifacts carry status flags from the foundation. Code generators MUST honor these:

| Flag | Meaning | Action |
|---|---|---|
| `Active` | Production-grade; fully implemented | Generate normally |
| `Active — Immutable` | Active but append-only; no update methods | Generate without update operations |
| `DORMANT` | Structurally defined; not wired into runtime | Scaffold class files only; no DbSet, no service registration |
| `STUB` | Placeholder with empty implementation | Generate with TODO comment; do not call in integration tests |
| `[GATE]` | Blocks wave progression | Must be resolved before next wave begins |

---

## 15.1 Bounded Context Registry

The following bounded contexts (BCs) are the unit of code generation. Each maps to a graph domain cluster:

| BC | Name | Primary Entities | Status | Generation Priority |
|---|---|---|---|---|
| BC-01 | Identity | DATA-ENT-010 (ApplicationUser), ASP.NET Roles | Active | 2nd (after BC-04) |
| BC-02 | Basket | DATA-AGG-001 (Basket, BasketItem) | Active | 3rd |
| BC-03 | Order | DATA-AGG-002 (Order, OrderItem, Address VO, CatalogItemOrdered VO) | Active — Immutable | 4th |
| BC-04 | Catalog | DATA-ENT-001/002/003 (CatalogItem, CatalogBrand, CatalogType) | Active | **1st — generate first** |
| BC-05 | Admin (BlazorAdmin) | APP-IF-003, APP-SVC-009, APP-SVC-013 | Active | 5th |
| BC-06 | Buyer | DATA-AGG-003 (DORMANT), DATA-ENT-008/009 | **DORMANT** | Last / Skip (DORMANT) |
| BC-07 | Infrastructure | APP-SVC-008, APP-SVC-010..012 | Active — Cross-cutting | 6th |

**Generation priority rationale:**
- BC-04 (Catalog) first — has the most self-contained public API surface and lowest cross-BC coupling
- BC-01 (Identity) second — Catalog write endpoints depend on authentication
- BC-02 (Basket) third — depends on Identity (authenticated BuyerId) and Catalog (product price)
- BC-03 (Order) fourth — depends on Basket (checkout input) and Catalog (snapshot source)
- BC-05 (Admin) fifth — depends on BC-04, BC-01 for its full API surface
- BC-07 (Infrastructure) sixth — cross-cutting; repository and seeding wired last
- BC-06 (Buyer) last / skip — DORMANT; scaffold only when AO-05 payment integration begins

---

## 15.2 Wave 1-5 Execution Order

### Wave 1 — Foundation (No Dependencies)

```
FE-01 → FE-02 → FE-03 → FE-04

FE-01: Domain Model and Project Structure
  Output: Clean Architecture project scaffolding
  Key constraint: ApplicationCore must NOT reference BlazorShared (ARCH-VIOL-011 fix)
  Nodes: APP-IF-001..006

FE-02: Shared Kernel and Value Objects
  Output: Address VO, CatalogItemOrdered VO, BaseEntity
  Key constraint: VOs are immutable (no public setters)
  Nodes: DATA-ENT-011, 012, 013

FE-03: EF Core Data Contexts
  Output: CatalogContext + AppIdentityDbContext with HiLo sequences
  Key constraint: Buyer/PaymentMethod NOT in DbContext (DORMANT)
  Nodes: DATA-REPO-001, DATA-REPO-002

FE-04: EF Core Entity Type Configurations
  Output: IEntityTypeConfiguration<T> for all 7 catalog tables
  Key constraint: Exact column lengths from DA evidence
  Nodes: DATA-ENT-001..007, 011, 012

[WAVE 1 GATE]: All DbContexts compile; EF Core migrations run; seeded data loads.
```

### Wave 2 — Domain Logic (Depends on Wave 1)

```
FE-05 → FE-06 → FE-07 (can run parallel after FE-05/06)
FE-08 depends on FE-05, FE-06

FE-05: Domain Aggregates: BasketAggregate and OrderAggregate
  Output: Basket, BasketItem, Order, OrderItem entities with invariants
  Key constraint: Order is immutable after creation (no status field)
  Nodes: DATA-AGG-001, DATA-AGG-002

FE-06: Domain Aggregate: CatalogAggregate
  Output: CatalogItem, CatalogBrand, CatalogType with HiLo IDs
  Key constraint: Unique name (BIZ-RULE-020); Price > 0 (BIZ-RULE-021)
  Nodes: DATA-ENT-001, 002, 003

FE-07: Dormant Domain: BuyerAggregate (Scaffold Only)
  Output: Buyer + PaymentMethod class files; no DbSet; no DI registration
  Key constraint: DORMANT — scaffold only; PCI comment preserved (BIZ-RULE-034)
  Nodes: DATA-AGG-003, DATA-ENT-008, 009

FE-08: Business Rules as Domain Invariants
  Output: GuardExtensions, domain exceptions, specification classes
  Key constraint: All entity constructors use Guard.Against.*
  Nodes: BIZ-RULE-003, 005, 006, 014, 019, 021, 022

[WAVE 2 GATE]: All domain unit tests pass; aggregate invariants enforced; no build errors.
```

### Wave 3 — Application Layer (Depends on Wave 2)

```
FE-09 → FE-10 → FE-11 → FE-12

FE-09: Basket Application Services
  Output: BasketService, BasketQueryService, BasketViewModelService
  Key constraint: Auto-merge on duplicate (DISC-007); price lock; BuyerId = string (OQ-001)
  Nodes: APP-SVC-001, 002, 003

FE-10: Order Application Services
  Output: OrderService (accepts shipToAddress parameter — AO-01 fix), GetMyOrders/GetOrderDetails handlers
  Key constraint: AO-01 CRITICAL — OrderService.CreateOrderAsync must accept Address parameter; do NOT hardcode 123 Main St.
  Nodes: APP-SVC-004, 005, 006

FE-11: Catalog Application Services (Web MVC Read Path)
  Output: CatalogViewModelService + CachedCatalogViewModelService (IMemoryCache decorator)
  Key constraint: 30s sliding TTL; cache is NOT invalidated on admin writes
  Nodes: APP-SVC-014, CACHE-001

FE-12: BlazorAdmin Catalog Services
  Output: CachedCatalogItemServiceDecorator (Blazored.LocalStorage), CustomAuthStateProvider
  Key constraint: Write-through on Create/Edit/Delete; 1-minute TTL for brands/types
  Nodes: APP-SVC-009, 013, CACHE-002

[WAVE 3 GATE]: Integration tests for basket, order, and catalog pass. AO-01 verified (no hardcoded address).
```

### Wave 4 — Infrastructure and API (Depends on Wave 3)

```
Track A: FE-13 → FE-14 (sequential)
Track B: FE-15 → FE-16 (sequential)
Tracks A and B can run in parallel.

FE-13: Generic Repository and EF Infrastructure
  Output: EfRepository<T>, IRepository<T>, IReadRepository<T>
  Key constraint: ARCH-VIOL-001..007 fix — no endpoint injects EfRepository directly
  Nodes: APP-SVC-008, TECH-CUR-009

FE-14: PublicApi REST Endpoints (All 8)
  Output: All 8 REST API endpoints using Ardalis.ApiEndpoints
  Key constraint: AO-04 CRITICAL — NO await Task.Delay in CatalogItemListPagedEndpoint; ADMINISTRATORS role on writes
  Nodes: APP-API-001..008

FE-15: Identity Infrastructure (JWT + Cookie + Seeding)
  Output: IdentityTokenClaimService, AppIdentityDbContextSeed (with AO-09 idempotency fix), JWT config
  Key constraint: AO-03 CRITICAL — JWT key from IConfiguration["Auth:JwtKey"], not hardcoded; passwords from config
  Nodes: APP-SVC-007, 011, TECH-SEC-001, 002

FE-16: Auth, Authorization, and CORS
  Output: Program.cs startup wiring for auth, authorization policies, CORS allow-list
  Key constraint: CORS allow-list only (no AllowAnyOrigin); Swagger gated behind IsDevelopment(); password min 8 chars
  Nodes: TECH-SEC-003..006, ASMP-004, TD-21

[WAVE 4 GATE]: All API endpoint integration tests pass (8 endpoints); Swagger renders correctly; JWT auth verified; no hardcoded secrets.
```

### Wave 5 — Cross-Cutting and Delivery (Depends on Wave 4)

```
FE-17 → FE-18 → FE-19 → FE-20

FE-17: Security Hardening Configuration
  Output: Secret externalisation; remove all hardcoded values from codebase
  Key constraint: SA_PASSWORD via Docker secret/env var; JWT key in config; seeded passwords in config
  Nodes: TECH-SEC-007, BIZ-RULE-032, BIZ-RULE-029, TD-01, 02, 03

FE-18: Observability and Health Checks
  Output: /health + /health/ready endpoints; Polly retry policies; EF Core retry; structured logging scaffold
  Key constraint: Both app containers + sqlserver container have health checks; depends_on uses condition: service_healthy
  Nodes: TD-07, 08, 09, 11, TECH-INF-003

FE-19: Caching Configuration and Invalidation
  Output: IMemoryCache wiring (Wave 5 initial); Redis migration TODO; explicit cache invalidation documentation
  Key constraint: Document per-instance limitation; flag Redis migration for OQ-007 resolution
  Nodes: CACHE-001, 002, TD-12, DISC-004, 006

FE-20: Docker Compose, CI/CD, and Azure Deployment
  Output: Hardened docker-compose.yml; GitHub Actions with secret scanning; Azure IaC wiring
  Key constraint: SQL Server 2022 image (TD-04 fix); version-pinned; SA_PASSWORD via env var; health gates
  Nodes: TECH-INF-001..006, TECH-CUR-017, TD-02, 04, 05

[WAVE 5 GATE]: Docker Compose brings up all 3 services; health checks return 200; CI pipeline passes including secret scanning; no secrets committed.
```

---

## 15.3 GR-08 — Blocking Gate: Target Stack Selection

### Gate Definition

**GR-08:** "The target technology stack must be explicitly selected and documented before any Wave 1 code generation begins. FE-01 through FE-20 assume a single consistent target stack. Mixing stacks (e.g., .NET for some services, Node.js for others) requires an explicit microservices architecture decision first."

**Current state:** GR-08 is **OPEN (NEUTRAL-OPTION)**. The foundation evidence contains zero TECH-TGT nodes. No target stack has been selected.

### Gate Condition

GR-08 is resolved when a human architect records the following decisions in a `STACK_DECISION.md` file in the project root:

```markdown
# Stack Decision — eShopOnWeb Forward Engineering

**Resolved by:** [Architect name]
**Date:** [Resolution date]

## Target Stack Selections

| Layer | Selected Technology |
|---|---|
| Backend runtime | [.NET 8 / Java 21 / Node.js 22 / Python 3.12] |
| API framework | [ASP.NET Core / Spring Boot / NestJS / FastAPI] |
| ORM | [EF Core / Hibernate / Prisma / SQLAlchemy] |
| Database engine | [SQL Server 2022 / PostgreSQL 16 / MySQL 8] |
| Auth mechanism | [ASP.NET Identity+JWT / Spring Security / Passport / fastapi-users] |
| Deployment | [Docker Compose / Kubernetes / Azure Container Apps] |
| Architecture style | [Modular Monolith / Microservices] |

## Rationale
[One paragraph explaining the selection rationale]
```

**Until `STACK_DECISION.md` exists and is complete, Wave 1 code generation MUST NOT begin.**

### Recommended Default (Lowest Delta)

If no organization-specific constraints apply, the recommended default that preserves maximum fidelity to source architecture is:

| Layer | Recommended |
|---|---|
| Backend runtime | .NET 8 (TECH-CUR-001) |
| API framework | ASP.NET Core + Ardalis.ApiEndpoints (TECH-CUR-004) |
| ORM | Entity Framework Core + SQL Server provider (TECH-CUR-006) |
| Database | SQL Server 2022 (replacing EOL Azure SQL Edge, TECH-INF-003) |
| Auth | ASP.NET Core Identity + JWT Bearer (TECH-CUR-007, 008) |
| Deployment | Docker Compose (hardened) → Azure Container Apps |
| Architecture style | Modular Monolith → strangler-fig microservices extraction |

---

## 15.4 Architecture Violations — DO NOT CARRY FORWARD

The following 11 violations exist in the source codebase. The forward engineering pipeline MUST NOT replicate any of them. Each violation is explicitly blocked.

| ID | Violation | Impact | Correct Approach |
|---|---|---|---|
| ARCH-VIOL-001 | CatalogBrandListEndpoint injects EfRepository directly | Bypasses domain service abstraction | Inject IReadRepository<CatalogBrand> or ICatalogBrandService |
| ARCH-VIOL-002 | CatalogItemGetByIdEndpoint injects EfRepository directly | Same | Inject IReadRepository<CatalogItem> or ICatalogItemService |
| ARCH-VIOL-003 | CreateCatalogItemEndpoint injects EfRepository directly | Same | Inject IRepository<CatalogItem> via domain service |
| ARCH-VIOL-004 | DeleteCatalogItemEndpoint injects EfRepository directly | Same | Inject IRepository<CatalogItem> via domain service |
| ARCH-VIOL-005 | UpdateCatalogItemEndpoint injects EfRepository directly | Same | Inject IRepository<CatalogItem> via domain service |
| ARCH-VIOL-006 | CatalogTypeListEndpoint injects EfRepository directly | Same | Inject IReadRepository<CatalogType> or ICatalogTypeService |
| ARCH-VIOL-007 | IndexModel (Web) injects EfRepository directly | Same | Inject ICatalogViewModelService |
| ARCH-VIOL-008 | Module dependency cycle: Admin→Core→Basket→Catalog→DataAccess→Identity→Order→Web→Admin | Prevents independent module extraction | Enforce directed acyclic dependency graph; use domain event interfaces to break cycles |
| ARCH-VIOL-009 | EfRepository coupling score = 16 (highest in codebase) | Excessive concrete coupling | Consume only via IRepository<T> / IReadRepository<T> interfaces; never inject concrete EfRepository outside Infrastructure |
| ARCH-VIOL-010 | UriComposer coupling score = 8 | Infrastructure concern leaked across layers | UriComposer belongs in Infrastructure only; no direct dependency from ApplicationCore or PublicApi |
| ARCH-VIOL-011 | ApplicationCore references BlazorShared | Domain layer depends on UI-shared library | ApplicationCore must NOT reference BlazorShared; shared types move to ApplicationCore itself or a dedicated SharedKernel project |

---

## 15.5 Production-Readiness Remediation Plan

### AO-01 — Collect Shipping Address at Checkout (CRITICAL)

**Current:** `Checkout.cshtml.cs:57` hardcodes `"123 Main St., Kent, OH, United States, 44240"` as the shipping address for every order.
**Fix:** OrderService.CreateOrderAsync must accept `shipToAddress` as a parameter. Checkout page must collect real address from user.
**FE Document:** FE-10
**Wave:** Wave 3
**Validation:** No instance of `"123 Main"` or `"Kent, OH"` may appear in generated OrderService code.

### AO-02 — Implement Transactional Email Delivery (CRITICAL)

**Current:** `EmailSender.cs` returns `Task.CompletedTask` without any email delivery (BR-08).
**Fix:** Implement IEmailSender with real SMTP or transactional provider (SendGrid/SMTP). Credentials from configuration.
**FE Document:** FE-15
**Wave:** Wave 4
**Validation:** EmailSender.SendEmailAsync must make an actual outbound call; not return Task.CompletedTask.

### AO-03 — Externalise JWT Key and Passwords (CRITICAL)

**Current:** JWT key `SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes` and password `Pass@word1` hardcoded in `AuthorizationConstants.cs` (BR-32, BR-29).
**Fix:** Read from `IConfiguration["Auth:JwtKey"]`, `IConfiguration["Seeding:AdminPassword"]`, `IConfiguration["Seeding:DemoPassword"]`. Store in User Secrets / env var / Azure Key Vault.
**FE Documents:** FE-15, FE-16, FE-17
**Wave:** Wave 4 + Wave 5
**Validation:** `AuthorizationConstants.cs` must not exist in generated code. No string literal matching the old JWT key or password may appear in any generated file.

### AO-04 — Remove Artificial Catalogue Delay (CRITICAL)

**Current:** `await Task.Delay(1000)` at `CatalogItemListPagedEndpoint.cs:42` adds 1 second to every catalog browse request (BR-09).
**Fix:** Delete the line. Generated CatalogItemListPagedEndpoint must not contain any Task.Delay call.
**FE Document:** FE-14
**Wave:** Wave 4
**Validation:** Generated `CatalogItemListPagedEndpoint` contains zero occurrences of `Task.Delay`.

### AO-05 — Integrate Payment Processing (High)

**Current:** BuyerAggregate (DATA-AGG-003) and PaymentMethod (DATA-ENT-009) are dormant (no DbContext, no service).
**Fix:** Activate BuyerAggregate when a payment processor is selected (OQ-008 — Stripe vs Braintree vs other). Scaffold only in Wave 2 (FE-07); activate post-Wave 5.
**FE Document:** FE-07 (scaffold), future FE-21 (activation)
**Wave:** Post-Wave 5
**Validation:** FE-07 generated code has no DbSet<Buyer>, no service registration, no API endpoint. PCI comment preserved.

### AO-06 — Add Order Status Lifecycle (High)

**Current:** Orders have no status field — once created, orders are immutable (BIZ-RULE-012).
**Fix:** Add OrderStatus enum (PLACED → PROCESSING → SHIPPED → DELIVERED → CANCELLED). Activate post-Wave 5.
**FE Document:** FE-10 extension (post-Wave 5)
**Wave:** Post-Wave 5
**Validation:** Wave 1-5 generated Order entity has no status field. Status lifecycle is deferred.

### AO-07 — Inventory Management (High)

**Current:** No stock validation at checkout. `CatalogItem.AvailableStock` field is not present in eShopOnWeb source (DISC-001 — verified discrepancy).
**Fix:** Requires adding inventory tracking as a new capability. Post-Wave 5.
**FE Document:** Post-Wave 5
**Wave:** Post-Wave 5
**Note:** DISC-001 confirms AvailableStock is NOT in the source. Do NOT add it to generated Wave 1-5 code.

### AO-08 — Enforce Email Confirmation (High)

**Current:** New user registration activates accounts immediately without email confirmation (BR-27). Depends on AO-02 (email service).
**Fix:** `RequireConfirmedEmail = true`; send confirmation email on registration; block login until confirmed.
**FE Document:** FE-15 (post AO-02)
**Wave:** Post-Wave 5 (requires AO-02 first)

### AO-09 — Fix Identity Seeding Idempotency (Medium)

**Current:** `AppIdentityDbContextSeed` may throw if run more than once (role creation without existence check).
**Fix:** Wrap role creation in `if (!await roleManager.RoleExistsAsync(role))`. Wrap user creation in email existence check.
**FE Document:** FE-15
**Wave:** Wave 4
**Validation:** AppIdentityDbContextSeed runs idempotently on repeated startup without exceptions.

### AO-10 — Cache Brand and Type Lookups Separately in BlazorAdmin (Medium)

**Current:** BlazorAdmin localStorage cache invalidates all catalog data (items, brands, types) on any write. Brands and types should have TTL-only invalidation.
**Fix:** Separate cache keys for items, brands, and types in CachedCatalogItemServiceDecorator.
**FE Document:** FE-12
**Wave:** Wave 3

---

## 15.6 Code Generation Rules (GR-01 through GR-08)

### GR-01 — Generation Priority Order [GATE]

Generate in this BC order: BC-04 (Catalog) → BC-01 (Identity) → BC-02 (Basket) → BC-03 (Order) → BC-07 (Infrastructure) → BC-05 (Admin) → BC-06 (Buyer — DORMANT/last/skip).

**Rationale:** BC-04 has the most self-contained public API surface. BC-01 is required by BC-04 (authentication). BC-02/03 form the checkout pipeline. BC-06 is dormant and should not be activated in Waves 1-5.

### GR-02 — One Service Per BC [GATE]

Each bounded context maps to exactly one deployable service boundary in the forward-engineered system (for Modular Monolith: one well-defined module). No BC spans multiple services. No service spans multiple BCs.

### GR-03 — Scaffold Order Within Each BC [GATE]

Within each BC, generate in this order:
1. Domain entities and value objects
2. Aggregate root with invariants
3. Repository interfaces
4. Application service interfaces
5. Application service implementations
6. API endpoint handlers
7. EF Core entity type configurations
8. Startup wiring (DI registrations)

### GR-04 — Mandatory Trace Tags [GATE]

Every generated class, interface, and configuration must carry a code comment header referencing its primary source node:
```csharp
// Source: APP-SVC-001 (BasketService) | BIZ-CAP-010,011,012,013 | FE-09
```

This enables bidirectional traceability from generated code back to the enterprise knowledge graph.

### GR-05 — Honor Status Flags [GATE]

- `DORMANT` components: scaffold class files only; zero DI registrations; zero DbSet entries; zero API routes
- `STUB` components: generate with TODO comment; do not call in integration tests
- `Active — Immutable`: generate without update/delete methods; repository returns read-only results

### GR-06 — Functional vs Physical Ownership [GATE]

The functional owner of a capability (the domain service) determines the code generation target, not the physical file location in the source monolith. For example, `CachedCatalogViewModelService` lives in `src/Web/Services/` in the source but functionally belongs to the Catalog BC — generate it in the Catalog application layer.

### GR-07 — No Invention [GATE]

**The code generator MUST NOT invent:**
- New endpoints not in APP-API-001..008
- New entities not in DATA-ENT-001..013
- New business rules not in BIZ-RULE-001..037
- New capabilities not in BIZ-CAP-001..031
- Stock/inventory fields (DISC-001 — explicitly excluded from eShopOnWeb source)

If a required piece of functionality is not evidenced in the foundation, it must be scaffolded as a `TODO` with a reference to the open question or gap, not invented.

### GR-08 — Target Stack Must Be Explicitly Selected [NEUTRAL-OPTION → GATE]

**See §15.3 (GR-08 Resolution) for full gate specification.**

Code generation for all waves is blocked until `STACK_DECISION.md` is committed to the repository. This is the only NEUTRAL-OPTION that becomes a GATE upon wave initiation.

---

## 15.7 Architecture Rules (AR Series)

### AR-01 — Onion/Hexagonal Layering [GATE]

Dependency direction: Domain (ApplicationCore) ← Application Services ← Infrastructure ← Presentation/API.
ApplicationCore must have zero outbound project references (verified in source — must be preserved).

### AR-02 — Dependency Direction [GATE]

Inner layers must not reference outer layers:
- ApplicationCore: zero outbound references (MUST)
- Infrastructure: may reference ApplicationCore only
- Web/PublicApi: may reference ApplicationCore and Infrastructure
- BlazorShared: referenced only by BlazorAdmin and PublicApi — NEVER by ApplicationCore (ARCH-VIOL-011 fix)

### AR-03 — No Legacy Dependency Cycles [GATE]

The module dependency cycle (ARCH-VIOL-008) must be eliminated. Forward-engineered dependency graph must be a DAG.

### AR-04 — No Endpoint-to-Repository Shortcut [GATE]

API endpoint handlers must not directly inject `EfRepository<T>`. All data access flows through domain service interfaces or repository abstractions (ARCH-VIOL-001..007 fix).

### AR-05 — BC Isolation [GATE]

Each bounded context communicates with other BCs through well-defined interfaces or domain events. No direct entity-to-entity cross-BC object reference (except read-only snapshots: CatalogItemOrdered captures Catalog data at checkout time — this is intentional).

### AR-06 — Shared Kernel Minimization

The shared kernel contains only: BaseEntity, value objects (Address, CatalogItemOrdered), guard utilities. No business logic in shared kernel.

---

## 15.8 DDD Rules (DR Series)

### DR-01 — Aggregate Boundaries Authoritative [GATE]

The four aggregates defined in DATA-AGG-001..004 are the authoritative aggregate boundaries:
- DATA-AGG-001: BasketAggregate (root: Basket, child: BasketItem)
- DATA-AGG-002: OrderAggregate (root: Order, children: OrderItem, Address VO, CatalogItemOrdered VO)
- DATA-AGG-003: BuyerAggregate (DORMANT — scaffold only)
- DATA-AGG-004: CatalogAggregate (informal root: CatalogItem)

No new aggregates may be invented. No existing aggregate boundary may be changed without a documented architectural decision.

### DR-02 — One Repository Per Aggregate Root [GATE]

Each aggregate root has exactly one repository:
- Basket → IRepository<Basket>
- Order → IRepository<Order>
- CatalogItem → IRepository<CatalogItem>
- ApplicationUser → managed by ASP.NET Core Identity framework (not a custom repository)

No repository for non-root entities (BasketItem, OrderItem, Address, CatalogItemOrdered).

### DR-03 — Invariants in Domain [GATE]

Business rule invariants live in domain entity constructors and aggregate methods, enforced by Guard.Against.* (TECH-CUR-020). Invariants are not delegated to application services or API handlers.

### DR-04 — Value Objects Are Immutable [GATE]

Address (DATA-ENT-011) and CatalogItemOrdered (DATA-ENT-012) are value objects — no public setters. All fields set at construction time. EF Core owned entities configuration reflects this (no update methods generated).

### DR-05 — No Cross-Aggregate Object References [GATE]

Aggregates reference other aggregates by ID only, not by object reference:
- BasketItem.CatalogItemId (int — soft reference, no FK) — correct
- BasketItem holding a CatalogItem navigation property — PROHIBITED
- Order.BuyerId (string — soft reference) — correct

### DR-06 — Snapshot Semantics [GATE] (BIZ-RULE-001)

OrderItem.ItemOrdered contains an immutable snapshot of CatalogItem data at checkout time. These values MUST NOT be updated after order creation. Generated code must not expose update methods on CatalogItemOrdered.

### DR-07 — Domain Events

The following domain events are defined in the system but their delivery mechanism depends on architecture style choice (GR-08):

| Event | Trigger | BC Source | BC Target |
|---|---|---|---|
| BasketCheckoutEvent | Checkout completion | BC-02 (Basket) | BC-03 (Order) |
| OrderStartedDomainEvent | Order created | BC-03 (Order) | BC-01 (Identity), BC-07 (Email stub) |

For Modular Monolith: implement as MediatR INotification (in-process).
For Microservices: implement as message bus events (out-of-process, transactional outbox pattern).

### DR-08 — Ubiquitous Language

Generated code must use the domain's ubiquitous language. Key terms (case-sensitive as used in source):
- `Basket` (not `Cart` or `ShoppingCart`)
- `CatalogItem` (not `Product` or `Item`)
- `CatalogBrand` (not `Brand` or `Manufacturer`)
- `BuyerId` (not `UserId` or `CustomerId`)
- `ADMINISTRATORS` (all-caps — confirmed role name from source)

---

## 15.9 API Standards (API Series)

### API-01 — Preserve Contract Surface [GATE]

All 8 REST endpoint paths and HTTP methods from APP-API-001..008 must be preserved exactly in the forward-engineered system. No endpoint may be removed or renamed without a version increment.

### API-02 — Problem-Detail Error Envelope [GATE]

All error responses must use RFC 9457 problem-detail format (see Document 11, §11.6). No ad-hoc error response shapes.

### API-03 — Pagination on List Endpoints [GATE]

GET /api/catalog-items must support `pageIndex` + `pageSize` query parameters. Response must include `count` (total matching items) for pagination UI. (APP-API-004)

### API-04 — Auth on Protected Endpoints [GATE]

POST, PUT, DELETE /api/catalog-items must require and verify `[Authorize(Roles="ADMINISTRATORS")]` JWT. Requests without valid JWT must return 401. Requests with valid JWT but wrong role must return 403.

---

## 15.10 Validation Checklist (Pre-Release)

All items below must pass before any code is considered release-ready. Items marked `[GATE]` block deployment.

| VR-ID | Check | Status | Gate |
|---|---|---|---|
| VR-01 | GR-08 resolved — STACK_DECISION.md committed | Must verify | [GATE] |
| VR-02 | No hardcoded JWT key in any generated file | Must verify | [GATE] |
| VR-03 | No hardcoded passwords in any generated file | Must verify | [GATE] |
| VR-04 | No hardcoded SA_PASSWORD in docker-compose.yml | Must verify | [GATE] |
| VR-05 | GET /api/catalog-items contains no Task.Delay | Must verify | [GATE] |
| VR-06 | OrderService.CreateOrderAsync accepts Address parameter (not hardcoded) | Must verify | [GATE] |
| VR-07 | All 8 REST endpoints generated and tested | Must verify | [GATE] |
| VR-08 | All ARCH-VIOL-001..011 are absent from generated code | Must verify | [GATE] |
| VR-09 | BuyerAggregate has no DbSet, no service, no API (DORMANT enforced) | Must verify | [GATE] |
| VR-10 | ApplicationCore has zero outbound project references | Must verify | [GATE] |
| VR-11 | All Wave gate conditions passed sequentially | Must verify | [GATE] |
| VR-12 | Health checks return 200 for both app containers | Must verify | [GATE] |
| VR-13 | Docker Compose brings up all 3 services without race conditions | Must verify | [GATE] |
| VR-14 | CI pipeline passes including secret scanning step | Must verify | [GATE] |

---

## 15.11 Implementation Guidelines

### Mandatory Rules (M-1 through M-14)

| Rule | Description |
|---|---|
| M-1 | ApplicationCore has zero outbound project references |
| M-2 | No endpoint injects EfRepository directly |
| M-3 | All JWT configuration from IConfiguration, never from code constants |
| M-4 | No `await Task.Delay` in any generated file |
| M-5 | OrderService.CreateOrderAsync accepts Address as parameter |
| M-6 | BuyerAggregate: class files only, no DbSet, no DI |
| M-7 | All entity constructors use Guard.Against.* invariants |
| M-8 | All 8 REST endpoints carry trace tags (GR-04) |
| M-9 | Order entity has no status field in Wave 1-5 output |
| M-10 | CatalogItem name uniqueness checked before insert |
| M-11 | CatalogItem price > 0 enforced in domain constructor |
| M-12 | AppIdentityDbContextSeed wrapped in existence checks (AO-09) |
| M-13 | Swagger middleware gated behind IsDevelopment() |
| M-14 | CORS policy specifies explicit origin list, not AllowAnyOrigin |

### Forbidden Patterns

| Pattern | Reason |
|---|---|
| `services.AddDbContext<T>()` without explicit connection string source | Prevents secret externalization |
| `options.AllowAnyOrigin()` | CORS security violation |
| `await Task.Delay(...)` in any endpoint | Performance violation (BR-09) |
| `new EfRepository<T>()` in endpoint constructors | ARCH-VIOL-001..007 |
| Any navigation property from Order to CatalogItem | Cross-aggregate object reference violation |
| `AvailableStock`, `RestockThreshold`, `MaxStockThreshold`, `OnReorder` fields on CatalogItem | DISC-001 — not in source |
| Hardcoded string addresses in OrderService | AO-01 violation |

---

## 15.12 Master Traceability Summary

```
Enterprise Knowledge Graph Nodes
         │
         ├── Business Layer (31 BIZ-CAP, 7 BIZ-PROC, 37 BIZ-RULE)
         │   └──► Wave 2-3 FE Documents (FE-05 through FE-12)
         │
         ├── Data Layer (13 DATA-ENT, 4 DATA-AGG, 2 DATA-REPO, 2 CACHE)
         │   └──► Wave 1 FE Documents (FE-01 through FE-04)
         │
         ├── Application Layer (14 APP-SVC, 8 APP-API, 6 APP-IF)
         │   └──► Wave 3-4 FE Documents (FE-09 through FE-16)
         │
         └── Technology Layer (22 TECH-CUR, 6 TECH-INF, 7 TECH-SEC)
             └──► Wave 5 FE Documents (FE-17 through FE-20)
                 + Document 12 (Blueprint) + Document 13 (Security) + Document 14 (NFR)

Rule Sets → Validation Checklist (VR-01 through VR-14)
Production Gaps (AO-01..10) → FE Documents → Wave Execution → SHIP
```

### Node Coverage Summary

| Domain | Nodes | FE Documents | Wave |
|---|---|---|---|
| Business capabilities | BIZ-CAP-001..031 (29 active, 2 dormant) | FE-05..12 | 2-3 |
| Business rules | BIZ-RULE-001..037 | FE-05..16 | 2-4 |
| Domain entities | DATA-ENT-001..013 | FE-02..06 | 1-2 |
| DDD aggregates | DATA-AGG-001..004 | FE-05..07 | 2 |
| Databases | DATA-REPO-001..002 | FE-03 | 1 |
| Caches | CACHE-001..002 | FE-11..12, FE-19 | 3, 5 |
| Application services | APP-SVC-001..014 | FE-09..15 | 3-4 |
| REST API endpoints | APP-API-001..008 | FE-14 | 4 |
| Deployable units | APP-IF-001..006 | FE-01, FE-20 | 1, 5 |
| Tech stack | TECH-CUR-001..022 | FE-01, FE-20 | 1, 5 |
| Infrastructure | TECH-INF-001..006 | FE-20 | 5 |
| Security | TECH-SEC-001..007 | FE-15..17 | 4-5 |

### Production Readiness Map

| Wave | AO Items Resolved | Documents |
|---|---|---|
| Wave 3 | AO-01 (shipping address), AO-10 (cache brands/types) | FE-10, FE-12 |
| Wave 4 | AO-03 (JWT key/passwords), AO-04 (Task.Delay), AO-09 (seeding idempotency) | FE-14, FE-15 |
| Wave 4 + 5 | AO-02 (email — requires provider decision) | FE-15, FE-17 |
| Post-Wave 5 | AO-05 (payment), AO-06 (order status), AO-07 (inventory), AO-08 (email confirm) | Future FE-21+ |

---

## 15.13 Assumptions and Open Questions

| ID | Statement | Impact |
|---|---|---|
| ASMP-FE-150 | BuyerId is a string in both Basket and Order; OQ-001 (email vs GUID) left unresolved in Wave 1-5 | Generate with string BuyerId; add OQ-001 comment |
| ASMP-FE-151 | GDPR erasure workflow (OQ-002) not implemented in Wave 1-5 | Scaffold `IUserDeletionService` with TODO in FE-15 |
| ASMP-FE-152 | Redis (OQ-007) is deferred; IMemoryCache used in Wave 5 initial delivery | Flag in FE-19 comments; NFR-SCAL-003 |
| ASMP-FE-153 | Payment processor (OQ-008) unresolved; BuyerAggregate dormant in all 5 waves | FE-07 scaffold only; no activation |
| ASMP-FE-154 | Email provider (AO-02) selection is deferred from Wave 5 FE document scope | FE-15 generates interface + stub; provider wired as follow-on |
| ASMP-FE-155 | Target stack selection (GR-08) is the single most critical prerequisite for all Wave 1-5 generation | Block code generation until STACK_DECISION.md exists |

---

*Document 15 of 20 — Forward Engineering Master Specification*
*This document is the authoritative governance reference for the eShopOnWeb forward engineering pipeline.*
*All 11 architecture violations, 6 production blockers, 10 AO remediation items, and 5 code generation waves are fully specified with node ID traceability.*
*GR-08 remains OPEN — target stack selection required before Wave 1 begins.*
