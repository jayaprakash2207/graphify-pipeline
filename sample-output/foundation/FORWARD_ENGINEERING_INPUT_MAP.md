# Forward Engineering Input Map — eShopOnWeb
**Foundation Layer — Every Graph Node Mapped to FE Documents 01-20 (Wave 1-5)**  
**Generated:** 2026-06-30  
**Pipeline Stage:** Foundation Synthesis (Layer 5 — Final)  
**Purpose:** This document maps each enterprise knowledge graph node to the specific Forward Engineering (FE) documents that will consume it during code generation. Every FE document is listed with its wave, input nodes, and constraints from this pipeline.

---

## FE Document Wave Reference

| Wave | Documents | Focus |
|---|---|---|
| Wave 1 (Foundation) | FE-01, FE-02, FE-03, FE-04 | Domain model, project structure, shared kernel, EF Core contexts |
| Wave 2 (Domain Logic) | FE-05, FE-06, FE-07, FE-08 | Domain aggregates, value objects, business rules, domain events |
| Wave 3 (Application Layer) | FE-09, FE-10, FE-11, FE-12 | Application services, CQRS handlers, use cases, validations |
| Wave 4 (Infrastructure + API) | FE-13, FE-14, FE-15, FE-16 | Repositories, EF configurations, REST endpoints, auth |
| Wave 5 (Cross-Cutting + FE Delivery) | FE-17, FE-18, FE-19, FE-20 | Security, observability, caching, deployment / Docker |

---

## Section 1 — Wave 1: Foundation Documents

### FE-01 — Domain Model and Project Structure

**Purpose:** Generate the clean architecture project scaffolding and define top-level namespaces.

**Input Nodes:**

| Node ID | Node Name | Type | Key Input |
|---|---|---|---|
| APP-IF-004 | ApplicationCore | Deployable Unit | Zero outbound references — domain isolation rule |
| APP-IF-005 | Infrastructure | Deployable Unit | EF Core, Identity, JWT — all infrastructure concerns here |
| APP-IF-001 | eshopwebmvc | Deployable Unit | Web MVC + Blazor host — host adapter |
| APP-IF-002 | eshoppublicapi | Deployable Unit | REST API host adapter |
| APP-IF-006 | BlazorShared | Deployable Unit | Shared contracts — reference from PublicApi and BlazorAdmin only; NOT from ApplicationCore (ARCH-VIOL-011 must NOT be replicated) |
| DATA-ENT-013 | BaseEntity | Domain Entity | Base int Id for all entities |
| ASMP-007 | System name assumption | Assumption | System name = eShopOnWeb |

**Critical Constraint:** ApplicationCore must NOT reference BlazorShared, PublicApi, Infrastructure, or Web projects. This constraint was violated in the source (ARCH-VIOL-011) — do NOT carry forward.

---

### FE-02 — Shared Kernel and Value Objects

**Purpose:** Generate Shared Kernel types, value objects, guard clauses, and base types.

**Input Nodes:**

| Node ID | Node Name | Type | Key Input |
|---|---|---|---|
| DATA-ENT-011 | Address | Value Object (Owned Entity) | Fields: Street nvarchar(180) NOT NULL, City nvarchar(100) NOT NULL, State nvarchar(60) nullable, Country nvarchar(90) NOT NULL, ZipCode nvarchar(18) NOT NULL |
| DATA-ENT-012 | CatalogItemOrdered | Value Object (Owned Entity) | Fields: CatalogItemId int, ProductName nvarchar(50), PictureUri nvarchar(max) |
| DATA-ENT-013 | BaseEntity | Abstract Base | int Id property |
| TECH-CUR-020 | Ardalis.GuardClauses + Ardalis.Result | Technology | Guard clauses used in all entity constructors and domain services |
| BIZ-RULE-014 | Guard clause invariant enforcement | Business Rule | All domain constructors use GuardExtensions before DB persistence |
| BIZ-RULE-033 | Shipping address field max lengths | Business Rule | Enforced at domain level, not just DB |

**Generate:** Address VO with validation, CatalogItemOrdered VO (immutable — no setters), BaseEntity abstract class, GuardExtensions.

---

### FE-03 — EF Core Data Contexts

**Purpose:** Generate EF Core DbContext classes, connection configuration, and startup wiring.

**Input Nodes:**

| Node ID | Node Name | Type | Key Input |
|---|---|---|---|
| DATA-REPO-001 | CatalogDatabase | Repository | CatalogContext; CatalogConnection string; tables: Catalog, CatalogBrands, CatalogTypes, Baskets, BasketItems, Orders, OrderItems |
| DATA-REPO-002 | IdentityDatabase | Repository | AppIdentityDbContext; IdentityConnection string; standard ASP.NET Core Identity schema |
| DATA-ENT-008 | Buyer (DORMANT) | Domain Entity | DO NOT add to DbContext — ARCH-VIOL-003 would be replicated if Buyer added without service layer |
| DATA-ENT-009 | PaymentMethod (DORMANT) | Domain Entity | DO NOT add to DbContext |
| DATA-AGG-003 | BuyerAggregate (DORMANT) | Aggregate | Dormant — no DbSet; only add when payment integration (AO-05) is implemented |
| DISC-010 | HiLo sequence correction | Normalization Log | CatalogItem/Brand/Type IDs use HiLo sequences (not IDENTITY) — use .UseHiLo("catalog_hilo") etc. |
| OQ-003 | Data retention policy | Open Question | No retention/purge job found — leave Orders/OrderItems without soft-delete; flag for legal review |

**Generate:** CatalogContext (7 tables, HiLo config, owned entity config), AppIdentityDbContext (standard Identity), IEntityTypeConfiguration files for all 7 catalog tables, connection string wiring in Program.cs.

**IMPORTANT HiLo Config:**
- `CatalogItem.Id` — `.UseHiLo("catalog_hilo")`
- `CatalogBrand.Id` — `.UseHiLo("catalog_brand_hilo")`
- `CatalogType.Id` — `.UseHiLo("catalog_type_hilo")`
- All other PKs (Basket, Order etc.) — standard IDENTITY

---

### FE-04 — EF Core Entity Type Configurations

**Purpose:** Generate all IEntityTypeConfiguration<T> files with exact column lengths and constraints.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| DATA-ENT-001 | CatalogItem | Entity | Name nvarchar(50); PictureUri nvarchar(max); Price decimal(18,2); AvailableStock int; FK to Brand (RESTRICT), FK to Type (RESTRICT) |
| DATA-ENT-002 | CatalogBrand | Entity | Brand nvarchar(100) |
| DATA-ENT-003 | CatalogType | Entity | Type nvarchar(100) |
| DATA-ENT-004 | Basket | Entity | BuyerId nvarchar(256); cascade delete to BasketItems |
| DATA-ENT-005 | BasketItem | Entity | BasketId FK (CASCADE); CatalogItemId int (soft ref — no FK constraint); UnitPrice decimal; Quantity int >= 0 |
| DATA-ENT-006 | Order | Entity | BuyerId nvarchar(256) NOT NULL; OrderDate datetimeoffset; ShipToAddress_* owned entity |
| DATA-ENT-007 | OrderItem | Entity | OrderId FK (CASCADE); ItemOrdered_* owned entity; UnitPrice decimal(18,2) NOT NULL |
| DATA-ENT-011 | Address | Value Object | Owned by Order — inline columns ShipToAddress_Street(180), _City(100), _State(60 nullable), _Country(90), _ZipCode(18); 4 of 5 are NOT NULL |
| DATA-ENT-012 | CatalogItemOrdered | Value Object | Owned by OrderItem — inline columns ItemOrdered_CatalogItemId, _ProductName(50), _PictureUri(max) |
| DISC-002 | Column length corrections | Normalization Log | All column lengths confirmed from EF IEntityTypeConfiguration files by DA Agent 2 |

---

## Section 2 — Wave 2: Domain Logic Documents

### FE-05 — Domain Aggregates: BasketAggregate and OrderAggregate

**Purpose:** Generate the two primary active aggregates with their invariant enforcement.

**Input Nodes:**

| Node ID | Node Name | Type | Key Behaviour |
|---|---|---|---|
| DATA-AGG-001 | BasketAggregate | Aggregate | Root: Basket; Child: BasketItem; private constructor; encapsulated AddItem method |
| DATA-ENT-004 | Basket | Entity | BuyerId string (nvarchar 256); private Items collection |
| DATA-ENT-005 | BasketItem | Entity | UnitPrice locked at add-time; Quantity int >= 0 |
| BIZ-RULE-004 | Default quantity 1 | Business Rule | AddItemToBasket without quantity defaults to 1 |
| DISC-007 | Auto-merge on duplicate | Normalization Log | If same CatalogItemId already in basket, increment quantity; do NOT throw exception; do NOT update price |
| DATA-AGG-002 | OrderAggregate | Aggregate | Root: Order; Child: OrderItem + Address VO + CatalogItemOrdered VO; immutable after creation |
| DATA-ENT-006 | Order | Entity | No status field; immutable; BuyerId + ShipToAddress + OrderDate at creation |
| DATA-ENT-007 | OrderItem | Entity | Contains CatalogItemOrdered snapshot (immutable); UnitPrice at time of order |
| BIZ-RULE-012 | Order immutability | Business Rule | No status field; no update methods; orders cannot be cancelled or modified |
| BIZ-RULE-001 | Snapshot principle | Business Rule | OrderItem captures product name + picture + price at checkout — must not update post-creation |

---

### FE-06 — Domain Aggregate: CatalogAggregate

**Purpose:** Generate CatalogItem, CatalogBrand, CatalogType entities with admin invariants.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| DATA-ENT-001 | CatalogItem | Entity | HiLo PK; Name nvarchar(50); Price > 0; unique name enforcement; default image on creation |
| DATA-ENT-002 | CatalogBrand | Entity | HiLo PK; Brand nvarchar(100) |
| DATA-ENT-003 | CatalogType | Entity | HiLo PK; Type nvarchar(100) |
| BIZ-RULE-020 | Product name uniqueness | Business Rule | Name must be unique — checked in CreateCatalogItemEndpoint |
| BIZ-RULE-021 | Price > 0 | Business Rule | Guard.Against.NegativeOrZero on price |
| BIZ-RULE-022 | Non-empty name and description | Business Rule | Guard.Against.NullOrEmpty on name + description |
| BIZ-RULE-023 | Default placeholder image | Business Rule | New items always get default image — admin image upload permanently disabled |
| DISC-010 | HiLo sequence | Normalization Log | IDs generated via HiLo — affects test factories and bulk insert strategies |

---

### FE-07 — Dormant Domain: BuyerAggregate (Scaffold for AO-05)

**Purpose:** Scaffold BuyerAggregate for future activation — do NOT wire into DbContext or any service until payment integration (AO-05) is implemented.

**Input Nodes:**

| Node ID | Node Name | Type | Key Note |
|---|---|---|---|
| DATA-AGG-003 | BuyerAggregate (DORMANT) | Aggregate | DORMANT — scaffold class files only; no DbSet; no service |
| DATA-ENT-008 | Buyer | Entity | IdentityGuid links to AspNetUsers.Id by string value convention; no FK |
| DATA-ENT-009 | PaymentMethod | Entity | CardId = PCI token only (Stripe or equivalent); never store raw card details; PCI comment from source preserved |
| BIZ-RULE-034 | PCI compliance | Business Rule | PaymentMethod.CardId is token only — no raw card data ever; code comment must be preserved |
| BIZ-RULE-035 | Dormancy | Business Rule | No active service — scaffold only; activate as part of AO-05 |
| OQ-008 | Payment processor decision | Open Question | Stripe vs Braintree vs other — unresolved; PaymentMethod.CardId format depends on this choice |

---

### FE-08 — Business Rules as Domain Invariants

**Purpose:** Generate guard extensions, specification classes, and domain exception types encoding all hard-constraint business rules.

**Input Nodes:**

| Node ID | Node Name | Type | Implementation Approach |
|---|---|---|---|
| BIZ-RULE-003 | Non-empty basket at checkout | Hard Constraint | GuardExtensions.EmptyBasketOnCheckout — throw if basket empty |
| BIZ-RULE-006 | Auth required for checkout | Hard Constraint | [Authorize] on Checkout.cshtml.cs |
| BIZ-RULE-005 | ADMINISTRATORS role for admin writes | Hard Constraint | [Authorize(Roles="ADMINISTRATORS")] on all catalog write endpoints |
| BIZ-RULE-014 | Guard clause invariants | Hard Constraint | Guard.Against.* in all entity constructors |
| BIZ-RULE-019 | Non-empty basket guard | Hard Constraint | Guard.Against in OrderService.CreateOrderAsync |
| BIZ-RULE-021 | Price > 0 | Hard Constraint | Guard.Against.NegativeOrZero |
| BIZ-RULE-022 | Non-empty name/description | Hard Constraint | Guard.Against.NullOrEmpty |
| BIZ-RULE-017 | GUID validation on basket cookie | Soft Constraint | Guid.TryParse() before TransferBasketAsync |

---

## Section 3 — Wave 3: Application Layer Documents

### FE-09 — Basket Application Services

**Purpose:** Generate BasketService, BasketQueryService, and BasketViewModelService with full interface contracts.

**Input Nodes:**

| Node ID | Node Name | Type | Key Behaviour |
|---|---|---|---|
| APP-SVC-001 | BasketService | Service | AddItemToBasket (auto-merge, price lock), DeleteBasketAsync, TransferBasketAsync (Web login only), SetQuantities |
| APP-SVC-002 | BasketQueryService | Service | Item count query for navigation header |
| APP-SVC-003 | BasketViewModelService | Service | View model assembly with product details join |
| BIZ-RULE-002 | Basket transfer trigger | Business Rule | Only Web login (Login.cshtml.cs) triggers transfer — NOT API login (AuthenticateEndpoint) |
| BIZ-RULE-004 | Default quantity 1 | Business Rule | AddItemToBasket default |
| BIZ-RULE-010 | Price lock on merge | Business Rule | Merging duplicate item does NOT update price |
| BIZ-RULE-016 | Essential GUID cookie | Business Rule | 10-year essential cookie; GUID as anonymous BuyerId |
| DISC-007 | Auto-merge confirmation | Normalization Log | Basket.AddItem() increments quantity — no DuplicateException |
| OQ-001 | BuyerId = email or GUID? | Open Question | Resolution affects PII sensitivity — generate with BuyerId as string and document this ambiguity |

---

### FE-10 — Order Application Services

**Purpose:** Generate OrderService, GetMyOrdersHandler, and GetOrderDetailsHandler.

**Input Nodes:**

| Node ID | Node Name | Type | Key Behaviour |
|---|---|---|---|
| APP-SVC-004 | OrderService | Service | CreateOrderAsync — snapshot products, create Order + OrderItems, delete basket |
| APP-SVC-005 | GetMyOrdersHandler | MediatR Handler | Return all orders for current BuyerId only |
| APP-SVC-006 | GetOrderDetailsHandler | MediatR Handler | Return single order for current BuyerId — 404 if not owner |
| BIZ-RULE-001 | Snapshot invariant | Business Rule | CatalogItemOrdered must capture name + picture + price at checkout time |
| BIZ-RULE-003 | Basket delete after order | Business Rule | Basket permanently deleted after order saved |
| BIZ-RULE-015 | Shipping address gap | Business Rule | CURRENT: hardcoded address — MUST be replaced with user-provided address input (AO-01) |
| BIZ-RULE-030 | Per-owner order access | Business Rule | GetMyOrders and GetOrderDetails return 404 for orders owned by other users |
| BIZ-RULE-012 | Order immutability | Business Rule | No update service; no cancel service; Orders are append-only |

**CRITICAL INSTRUCTION for AO-01 compliance:** Do NOT hardcode 123 Main St. Generate OrderService.CreateOrderAsync to accept shipToAddress as a parameter from the caller — caller must collect this from the user.

---

### FE-11 — Catalog Application Services (Web MVC Read Path)

**Purpose:** Generate CatalogViewModelService and CachedCatalogViewModelService (IMemoryCache decorator).

**Input Nodes:**

| Node ID | Node Name | Type | Key Behaviour |
|---|---|---|---|
| APP-SVC-014 | CachedCatalogViewModelService | Service (Decorator) | IMemoryCache 30-second sliding TTL wrapping all catalog reads in Web MVC |
| CACHE-001 | Web MVC IMemoryCache | Cache | 30s sliding TTL; server-side in-process; NOT invalidated by admin writes |
| BIZ-RULE-010 | Cache TTL (server-side) | Business Rule | Web storefront may show stale catalogue for up to 30s after any admin write |
| DISC-006 | Missed cache layer | Normalization Log | DA Agent 1 missed this cache entirely — it is real and must be generated |

**Generate:** CatalogViewModelService (direct EF read), CachedCatalogViewModelService (decorator with IMemoryCache), CacheHelpers (cache key constants), wired as decorator in Program.cs.

---

### FE-12 — BlazorAdmin Catalog Services (Admin Read/Write Path)

**Purpose:** Generate CachedCatalogItemServiceDecorator (Blazored.LocalStorage) and supporting admin services.

**Input Nodes:**

| Node ID | Node Name | Type | Key Behaviour |
|---|---|---|---|
| APP-SVC-009 | CachedCatalogItemServiceDecorator | Service (Decorator) | Blazored.LocalStorage; 1-minute TTL; write-through for items; TTL-only for brands/types |
| CACHE-002 | BlazorAdmin localStorage Cache | Cache | 1 minute DateCreated.AddMinutes(1); browser localStorage; XSS-accessible |
| APP-SVC-013 | CustomAuthStateProvider | Service | 60-second poll interval for JWT expiry check |
| TECH-CUR-012 | Blazored.LocalStorage | Technology | Browser localStorage — JWT token stored here (XSS risk TD-03 — flag in generated code comments) |
| BIZ-RULE-010 | Cache write-through | Business Rule | On Create/Edit/Delete: call RefreshLocalStorageList() immediately |
| DISC-004 | Cache technology correction | Normalization Log | Cache is browser localStorage — NOT server-side in-process memory |

---

## Section 4 — Wave 4: Infrastructure and API Documents

### FE-13 — Generic Repository and EF Infrastructure

**Purpose:** Generate EfRepository<T>, IRepository<T>, IReadRepository<T>, and Ardalis.Specification wiring.

**Input Nodes:**

| Node ID | Node Name | Type | Key Note |
|---|---|---|---|
| APP-SVC-008 | EfRepository | Service | Generic IRepository<T> and IReadRepository<T> using Ardalis.Specification pattern |
| TECH-CUR-009 | Ardalis.Specification | Technology | Specification pattern for all repository queries |
| ARCH-VIOL-001 through ARCH-VIOL-007 | Direct EfRepository injection | Architecture Violation | Source had 6 API endpoints inject EfRepository directly — DO NOT replicate; generate domain service interfaces instead |
| ARCH-VIOL-009 | EfRepository coupling=16 | Architecture Violation | Must be consumed via IRepository<T> interface — never inject EfRepository concrete type outside Infrastructure |

**CRITICAL INSTRUCTION:** All PublicApi endpoints must receive `IRepository<T>` or `IReadRepository<T>` (or a domain service interface) — never the concrete `EfRepository`. This resolves ARCH-VIOL-001 through ARCH-VIOL-007.

---

### FE-14 — PublicApi REST Endpoints

**Purpose:** Generate all 8 REST API endpoints using Ardalis.ApiEndpoints pattern.

**Input Nodes:**

| Node ID | Endpoint | Auth | Key Constraint |
|---|---|---|---|
| APP-API-001 | POST /api/authenticate | None (issues JWT) | Use IdentityTokenClaimService; JWT key must come from config — NOT hardcoded (AO-03) |
| APP-API-002 | GET /api/catalog-brands | None (public) | Remove direct EfRepository dependency; use ICatalogBrandService or IReadRepository |
| APP-API-003 | GET /api/catalog-items/{id} | None (public) | Same as APP-API-002 |
| APP-API-004 | GET /api/catalog-items | None (public) | REMOVE await Task.Delay(1000) — this line must not exist in generated code (AO-04) |
| APP-API-005 | POST /api/catalog-items | [Authorize(Roles="ADMINISTRATORS")] | Remove direct EfRepository dependency; unique name check required (BIZ-RULE-020) |
| APP-API-006 | DELETE /api/catalog-items/{id} | [Authorize(Roles="ADMINISTRATORS")] | Remove direct EfRepository dependency |
| APP-API-007 | PUT /api/catalog-items | [Authorize(Roles="ADMINISTRATORS")] | Remove direct EfRepository dependency; price > 0 required (BIZ-RULE-021) |
| APP-API-008 | GET /api/catalog-types | None (public) | Remove direct EfRepository dependency |

**CRITICAL INSTRUCTION for AO-04:** Generated CatalogItemListPagedEndpoint must NOT contain `await Task.Delay(1000)`. This is the removal of BR-09 production blocker.

---

### FE-15 — Identity Infrastructure (JWT + Cookie)

**Purpose:** Generate IdentityTokenClaimService, Identity configuration, and seeding — with secret externalisation.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| APP-SVC-007 | IdentityTokenClaimService | Service | Reads user + roles from Identity; builds JWT claims; 7-day expiry (BIZ-RULE-024) |
| APP-SVC-011 | AppIdentityDbContextSeed | Service | Seed ADMINISTRATORS role + admin/demo accounts; fix idempotency bug (AO-09: check role exists before creating) |
| TECH-SEC-001 | Cookie Auth | Security | Web MVC — standard Identity cookie config |
| TECH-SEC-002 | JWT Bearer | Security | PublicApi — JWT key MUST come from config/environment/Key Vault (AO-03) — NOT hardcoded |
| BIZ-RULE-024 | JWT 7-day expiry | Business Rule | Token expires = DateTime.UtcNow.AddDays(7) |
| BIZ-RULE-025 | Account lockout | Business Rule | Enabled for both Web and API login |
| BIZ-RULE-028 | Registration validation | Business Rule | Email required; password 6-100 chars; matching confirmation |
| BIZ-RULE-029 | Seeded passwords | Security Rule | AO-03: default passwords must be read from config/env — NOT hardcoded constants |
| BIZ-RULE-032 | JWT key | Security Rule | AO-03: JWT key must be read from config/env/Key Vault — NOT from AuthorizationConstants.cs |
| BIZ-RULE-037 | Seeding idempotency | Bug Fix (AO-09) | Wrap role creation in existence check: if (!await roleManager.RoleExistsAsync(role)) |

---

### FE-16 — Authentication, Authorization, and CORS

**Purpose:** Generate Program.cs startup wiring for auth, authorisation policies, and CORS.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| TECH-SEC-003 | Claims-Based Authorisation | Security | Authorisation policies for ADMINISTRATORS role |
| TECH-SEC-005 | User Secrets (dev) | Security | Dev secrets for JWT key and connection strings |
| TECH-SEC-004 | Azure Managed Identity | Security | Production secrets via DefaultAzureCredential + Key Vault |
| TECH-SEC-006 | CSRF Anti-Forgery | Security | Wire anti-forgery tokens for all MVC forms |
| ASMP-004 | CORS policy (unconfirmed) | Assumption | CORS policy for BlazorAdmin -> PublicApi cross-origin calls must be generated explicitly — do NOT use AllowAnyOrigin |
| TECH-INF-001 | eshopwebmvc | Infrastructure | CORS origin for PublicApi: allow https://localhost:44315 in dev, Azure host in prod |
| TD-21 | Password min length | Technical Debt | Set minimum password length to 8 (NIST 800-63B) — not the current 6 |
| ASMP-005 | Swagger gating | Assumption | Swagger middleware must be gated behind app.Environment.IsDevelopment() |

---

## Section 5 — Wave 5: Cross-Cutting and Delivery Documents

### FE-17 — Security Hardening Configuration

**Purpose:** Remove all hardcoded secrets; generate secure configuration patterns.

**Input Nodes:**

| Node ID | Node Name | Type | Key Action |
|---|---|---|---|
| TECH-SEC-007 | SA Password Hardcoded (CRITICAL) | Vulnerability | Remove @someThingComplicated1234 from docker-compose.yml; use Docker secrets or env var |
| BIZ-RULE-032 | JWT key hardcoded (CRITICAL) | Security Rule | Read JWT key from IConfiguration["Auth:JwtKey"] — never from AuthorizationConstants.cs:12 |
| BIZ-RULE-029 | Seeded passwords hardcoded (CRITICAL) | Security Rule | Read default passwords from IConfiguration["Seeding:AdminPassword"] — never from constants |
| TD-01 | SA password | Technical Debt | Replace hardcoded SA password with Docker environment variable |
| TD-02 | No secret scanning | Technical Debt | Add Gitleaks or TruffleHog step to GitHub Actions CI workflow |
| TD-03 | JWT in localStorage | Technical Debt | Migrate BlazorAdmin JWT storage from localStorage to httpOnly cookie (high effort — flag as follow-on) |
| TECH-INF-004 | Azure Key Vault | Infrastructure | Wire Azure Key Vault for sqlAdminPassword + appUserPassword on Azure deployment path |
| TECH-SEC-004 | DefaultAzureCredential | Security | Use DefaultAzureCredential for Key Vault access in production |

---

### FE-18 — Observability and Health Checks

**Purpose:** Generate health check endpoints and observability scaffolding.

**Input Nodes:**

| Node ID | Node Name | Type | Key Action |
|---|---|---|---|
| TD-08 | No health checks | Technical Debt | Add /health (liveness + readiness) endpoints to both Web and PublicApi |
| TD-11 | Docker Compose race condition | Technical Debt | Add healthcheck: test and condition: service_healthy to docker-compose depends_on |
| TD-07 | No retry/circuit breaker | Technical Debt | Add Polly retry + circuit breaker policies to BlazorAdmin HttpClient for PublicApi calls |
| TD-09 | No EF Core retry | Technical Debt | Add EnableRetryOnFailure() to EF Core SQL Server provider options |
| TECH-INF-003 | sqlserver container | Infrastructure | Add health gate so Web/API containers wait for SQL Server to be ready before starting |

---

### FE-19 — Caching Configuration and Invalidation

**Purpose:** Generate caching infrastructure with explicit invalidation strategies and gap remediation.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| CACHE-001 | Web MVC IMemoryCache | Cache | 30s sliding TTL; server-side in-process only; must document that admin writes do NOT invalidate this cache |
| CACHE-002 | BlazorAdmin localStorage | Cache | 1-minute TTL; write-through for items; TTL-only for brands/types; JWT stored here (flag XSS risk) |
| TD-12 | No distributed cache | Technical Debt | Flag: current IMemoryCache is per-instance; Redis required for horizontal scaling (OQ-007) |
| DISC-006 | Missed IMemoryCache layer | Normalization Log | DA Agent 1 missed this — ensure it is explicitly generated and wired in Program.cs |
| DISC-004 | BlazorAdmin cache technology | Normalization Log | Blazored.LocalStorage — client-side browser storage (not server-side memory) |

---

### FE-20 — Docker Compose, CI/CD, and Azure Deployment

**Purpose:** Generate docker-compose.yml, GitHub Actions workflow, and Azure IaC scaffolding.

**Input Nodes:**

| Node ID | Node Name | Type | Key Constraint |
|---|---|---|---|
| TECH-INF-001 | eshopwebmvc Container | Infrastructure | mcr.microsoft.com/dotnet/aspnet:8.0; port 5106:8080; no SA password in compose file |
| TECH-INF-002 | eshoppublicapi Container | Infrastructure | mcr.microsoft.com/dotnet/aspnet:8.0; port 5200:8080 |
| TECH-INF-003 | sqlserver Container | Infrastructure | Replace mcr.microsoft.com/azure-sql-edge with mcr.microsoft.com/mssql/server:2022-latest (EOL fix); pin version tag; SA password via env var or Docker secret |
| TECH-INF-004 | Azure Key Vault | Infrastructure | Wired via azure.yaml + main.parameters.json for azd deploy path |
| TECH-INF-006 | azd IaC | Infrastructure | infra/main.parameters.json — sqlAdminPassword + appUserPassword from Key Vault |
| TECH-CUR-017 | GitHub Actions CI | Technology | Add secret scanning step; keep build + test on ubuntu-latest dotnet 8.0.x |
| TD-02 | No secret scanning in CI | Technical Debt | Add Gitleaks or similar to .github/workflows/dotnetcore.yml |
| TD-04 | Azure SQL Edge EOL | Technical Debt | Replace image — see TECH-INF-003 |
| TD-05 | No version pin | Technical Debt | Pin SQL Server image to specific version tag |

**Docker Compose Generation Rules:**
- Use Docker environment variables or Docker secrets for SA_PASSWORD — never inline in compose file
- Add healthcheck + condition: service_healthy to all depends_on entries (resolves TD-11)
- Use exact version pin on SQL Server image (resolves TD-05)

---

## Section 6 — Open Questions That Block Specific FE Documents

| OQ-ID | Question | Blocks | Recommendation |
|---|---|---|---|
| OQ-001 | BuyerId = email or GUID? | FE-09 (basket service), FE-10 (order service), FE-17 (PII sensitivity) | Generate with string BuyerId; add comment flagging OQ-001; resolve before production deployment |
| OQ-002 | GDPR erasure workflow? | FE-10 (order service), FE-15 (identity service) | Scaffold placeholder IUserDeletionService with TODO; do not implement until legal review |
| OQ-005 | Demo credentials rotated before deployment? | FE-15 (identity seeding), FE-16 (auth config) | AO-03 must be implemented; FE-15 must read passwords from config — not constants |
| OQ-007 | Redis planned? | FE-19 (caching) | Generate with IMemoryCache; flag in comments that IDistributedCache (Redis) is needed for multi-instance |
| OQ-008 | Which payment processor (Stripe vs Braintree)? | FE-07 (BuyerAggregate scaffold) | Scaffold with payment token string field; comment references Stripe per existing code comment; AO-05 deferred |

---

## Section 7 — Architecture Violations — Do Not Replicate

The following violations exist in the source codebase. The forward engineering pipeline MUST NOT replicate any of them.

| Violation ID | Description | FE Document Affected | Correct Approach |
|---|---|---|---|
| ARCH-VIOL-001 through ARCH-VIOL-007 | 6 API endpoints inject EfRepository directly | FE-13, FE-14 | Inject IRepository<T> or domain service interface — never concrete EfRepository |
| ARCH-VIOL-008 | Module dependency cycle (Admin -> ... -> Web) | FE-01, FE-14 | Design clean module boundaries in project structure; no circular references |
| ARCH-VIOL-009 | EfRepository coupling score = 16 | FE-13 | Keep EfRepository behind interface; do not add more direct consumers |
| ARCH-VIOL-010 | UriComposer coupling score = 8 | FE-01, FE-11 | UriComposer belongs in Infrastructure — not shared across all layers |
| ARCH-VIOL-011 | ApplicationCore references BlazorShared | FE-01, FE-02 | ApplicationCore must NOT reference BlazorShared; shared types belong in SharedContracts or ApplicationCore itself |

---

## Section 8 — Node Count by FE Document (Summary)

| Wave | FE Doc | Nodes Consumed | Primary Layer | Key Output |
|---|---|---|---|---|
| 1 | FE-01 | APP-IF-001,002,003,004,005,006 + ASMP-007 | AA | Clean Architecture project scaffolding |
| 1 | FE-02 | DATA-ENT-011,012,013 + TECH-CUR-020 + 2 rules | DA | Value objects and shared kernel |
| 1 | FE-03 | DATA-REPO-001,002 + DATA-ENT-008,009 + DISC-010 + OQ-003 | DA | EF Core DbContexts with HiLo sequences |
| 1 | FE-04 | DATA-ENT-001-007,011,012 + DISC-002 | DA | IEntityTypeConfiguration files |
| 2 | FE-05 | DATA-AGG-001,002 + DATA-ENT-004,005,006,007 + 4 rules + DISC-007 | DA + BA | Basket and Order aggregates |
| 2 | FE-06 | DATA-ENT-001,002,003 + 4 rules + DISC-010 | DA + BA | Catalog entities with HiLo |
| 2 | FE-07 | DATA-AGG-003 + DATA-ENT-008,009 + 2 rules + OQ-008 | DA + BA | BuyerAggregate scaffold (dormant) |
| 2 | FE-08 | 8 BIZ-RULE nodes | BA | Guard extensions and domain exceptions |
| 3 | FE-09 | APP-SVC-001,002,003 + 4 rules + DISC-007 + OQ-001 | AA + BA | Basket application services |
| 3 | FE-10 | APP-SVC-004,005,006 + 5 rules | AA + BA | Order application services (AO-01 fix) |
| 3 | FE-11 | APP-SVC-014 + CACHE-001 + DISC-006 | AA + DA | Web MVC cached catalog service |
| 3 | FE-12 | APP-SVC-009,013 + CACHE-002 + DISC-004 | AA + DA | BlazorAdmin cached catalog service |
| 4 | FE-13 | APP-SVC-008 + TECH-CUR-009 + 7 ARCH-VIOL | AA + TA | Generic EF repository |
| 4 | FE-14 | APP-API-001 to APP-API-008 | AA | All 8 REST API endpoints (AO-04 fix: no Task.Delay) |
| 4 | FE-15 | APP-SVC-007,011 + TECH-SEC-001,002 + 6 rules | AA + TA | JWT/Cookie auth + seeding (AO-03, AO-09 fixes) |
| 4 | FE-16 | TECH-SEC-003-006 + ASMP-004,005 + TD-21 | TA | Auth/CORS/startup wiring |
| 5 | FE-17 | TECH-SEC-007 + 4 BIZ-RULE security items + 3 TD | TA | Secret externalisation (AO-03) |
| 5 | FE-18 | TD-07,008,009,011 + TECH-INF-003 | TA | Health checks and reliability |
| 5 | FE-19 | CACHE-001,002 + TD-12 + DISC-004,006 | DA + TA | Cache configuration |
| 5 | FE-20 | TECH-INF-001,002,003,004,006 + TECH-CUR-017 + TD-02,04,05 | TA | Docker Compose, CI/CD, Azure IaC |

---

## Section 9 — Wave Execution Order and Gate Conditions

```
WAVE 1 (Foundation — no dependencies)
  FE-01 -> FE-02 -> FE-03 -> FE-04
  Gate: All DbContexts compile with no build errors before proceeding.

WAVE 2 (Domain Logic — depends on Wave 1)
  FE-05 -> FE-06 -> FE-07 (can be parallel)
  FE-08 (depends on FE-05, FE-06)
  Gate: All domain unit tests pass before proceeding.

WAVE 3 (Application Layer — depends on Wave 2)
  FE-09 -> FE-10 -> FE-11 -> FE-12
  Gate: Integration tests for basket, order, and catalog pass.

WAVE 4 (Infrastructure + API — depends on Wave 3)
  FE-13 -> FE-14 (sequential)
  FE-15 -> FE-16 (sequential)
  FE-13/FE-14 can run parallel with FE-15/FE-16.
  Gate: All API endpoint integration tests pass; swagger renders correctly.

WAVE 5 (Cross-Cutting — depends on Wave 4)
  FE-17 -> FE-18 -> FE-19 -> FE-20
  Gate: Docker Compose brings up all 3 services; health checks return 200;
        CI pipeline passes including secret scanning step.
```

---

## Section 10 — Production-Readiness Mapping (AO-01 through AO-10)

| Roadmap Item | Description | FE Document(s) | Wave |
|---|---|---|---|
| AO-01 | Collect shipping address at checkout | FE-10 (OrderService signature change) | Wave 3 |
| AO-02 | Implement transactional email delivery | FE-15 (wire real IEmailSender implementation) | Wave 4 |
| AO-03 | Externalise JWT key and passwords to config/Key Vault | FE-15 (seeding), FE-16 (JWT config), FE-17 (secret removal) | Wave 4+5 |
| AO-04 | Remove await Task.Delay(1000) from catalogue endpoint | FE-14 (CatalogItemListPagedEndpoint) | Wave 4 |
| AO-05 | Integrate payment processing (activate BuyerAggregate) | FE-07 (activate scaffold), new FE-21 (payment service) | Post-Wave 5 |
| AO-06 | Add order status lifecycle | FE-10 (OrderService extension), new status enum | Post-Wave 5 |
| AO-07 | Inventory management (StockQuantity checkout validation) | FE-05 (CatalogItem), FE-10 (checkout guard) | Post-Wave 5 |
| AO-08 | Enforce email confirmation | FE-15 (Register.cshtml.cs — requires AO-02 first) | Post-Wave 5 |
| AO-09 | Fix identity seeding idempotency | FE-15 (AppIdentityDbContextSeed) | Wave 4 |
| AO-10 | Cache brand and type lookups separately in BlazorAdmin | FE-12 (CachedCatalogItemServiceDecorator) | Wave 3 |

---

*Forward Engineering Input Map — every graph node traceable to an FE document consumption point.*  
*Architecture violations from source are explicitly listed as DO NOT REPLICATE constraints.*  
*Production-readiness gaps (AO-01 through AO-10) are mapped to the exact FE documents that resolve them.*
