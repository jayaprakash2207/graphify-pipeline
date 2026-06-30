# Architecture Inventory — eShopOnWeb
**Foundation Layer — Every Component in Table Format**  
**Generated:** 2026-06-30  
**Pipeline Stage:** Foundation Synthesis (Layer 5 — Final)  
**Confidence Schema:** HIGH = direct code evidence; MEDIUM = inferred from structure; LOW = assumed from convention

---

## Section 1 — Deployable Units (Applications)

| ID | Name | Type | Source Path | Ports (host:container) | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| APP-IF-001 | eshopwebmvc | ASP.NET Core MVC App + BlazorAdmin host | src/Web/ | 5106:8080 (Docker), 44315 (dev HTTPS) | AA | HIGH | AA:component-service-map.md; docker-compose.yml |
| APP-IF-002 | eshoppublicapi | ASP.NET Core REST API | src/PublicApi/ | 5200:8080 (Docker), 5099 (dev HTTPS) | AA | HIGH | AA:component-service-map.md; docker-compose.yml |
| APP-IF-003 | BlazorAdmin | Blazor WebAssembly SPA (embedded in Web host) | src/BlazorAdmin/ | N/A (served from APP-IF-001) | AA | HIGH | TA:component-service-map.md; AP-07 |
| APP-IF-004 | ApplicationCore | Domain library — zero outbound project references | src/ApplicationCore/ | N/A | AA | HIGH | TA:component-service-map.md; Clean Architecture core |
| APP-IF-005 | Infrastructure | Infrastructure library (EF Core, Identity, JWT) | src/Infrastructure/ | N/A | AA | HIGH | TA:component-service-map.md |
| APP-IF-006 | BlazorShared | Shared contracts library (BlazorAdmin + PublicApi) | src/BlazorShared/ | N/A | AA | HIGH | TA:technical-debt-risk-register.md TD-13 — ApplicationCore references this (ARCH-VIOL-011) |

---

## Section 2 — REST API Endpoints (APP-API-###)

| ID | HTTP Method + Path | Handler Class | Source File | Auth | Module | Preserve in FE | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| APP-API-001 | POST /api/authenticate | AuthenticateEndpoint | src/PublicApi/AuthEndpoints/AuthenticateEndpoint.cs:36 | None (issues JWT) | Identity | YES | AA | HIGH | AA:INT-001 |
| APP-API-002 | GET /api/catalog-brands | CatalogBrandListEndpoint | src/PublicApi/CatalogBrandEndpoints/CatalogBrandListEndpoint.cs:27 | None (public) | Catalog | YES | AA | HIGH | AA:INT-002; ARCH-VIOL-001 |
| APP-API-003 | GET /api/catalog-items/{catalogItemId} | CatalogItemGetByIdEndpoint | src/PublicApi/CatalogItemEndpoints/CatalogItemGetByIdEndpoint.cs:25 | None (public) | Catalog | YES | AA | HIGH | AA:INT-003; ARCH-VIOL-002 |
| APP-API-004 | GET /api/catalog-items | CatalogItemListPagedEndpoint | src/PublicApi/CatalogItemEndpoints/CatalogItemListPagedEndpoint.cs:31 | None (public) | Catalog | YES — remove Task.Delay | AA | HIGH | AA:INT-004; BR-09 |
| APP-API-005 | POST /api/catalog-items | CreateCatalogItemEndpoint | src/PublicApi/CatalogItemEndpoints/CreateCatalogItemEndpoint.cs:29 | [Authorize(Roles=ADMINISTRATORS)] | Catalog | YES | AA | HIGH | AA:INT-005; ARCH-VIOL-003 |
| APP-API-006 | DELETE /api/catalog-items/{catalogItemId} | DeleteCatalogItemEndpoint | src/PublicApi/CatalogItemEndpoints/DeleteCatalogItemEndpoint.cs:20 | [Authorize(Roles=ADMINISTRATORS)] | Catalog | YES | AA | HIGH | AA:INT-006; ARCH-VIOL-004 |
| APP-API-007 | PUT /api/catalog-items | UpdateCatalogItemEndpoint | src/PublicApi/CatalogItemEndpoints/UpdateCatalogItemEndpoint.cs:27 | [Authorize(Roles=ADMINISTRATORS)] | Catalog | YES | AA | HIGH | AA:INT-007; ARCH-VIOL-005 |
| APP-API-008 | GET /api/catalog-types | CatalogTypeListEndpoint | src/PublicApi/CatalogTypeEndpoints/CatalogTypeListEndpoint.cs:27 | None (public) | Catalog | YES | AA | HIGH | AA:INT-008; ARCH-VIOL-006 |

---

## Section 3 — Application Services (APP-SVC-###)

| ID | Name | Module | Source Path | Capabilities Served | Interface | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|
| APP-SVC-001 | BasketService | Basket | src/ApplicationCore/Services/BasketService.cs | BIZ-CAP-010,011,012,013 | IBasketService | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-002 | BasketQueryService | Basket | src/ApplicationCore/Services/BasketQueryService.cs | BIZ-CAP-014 | IBasketQueryService | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-003 | BasketViewModelService | Basket | src/Web/Services/BasketViewModelService.cs | BIZ-CAP-015,016 | IBasketViewModelService | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-004 | OrderService | Order | src/ApplicationCore/Services/OrderService.cs | BIZ-CAP-017,018 | IOrderService | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-005 | GetMyOrdersHandler | Order | src/Web/Features/MyOrders/GetMyOrdersHandler.cs | BIZ-CAP-019 | MediatR IRequestHandler | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-006 | GetOrderDetailsHandler | Order | src/Web/Features/OrderDetails/GetOrderDetailsHandler.cs | BIZ-CAP-020 | MediatR IRequestHandler | AA | HIGH | BA:01_capability_map.md |
| APP-SVC-007 | IdentityTokenClaimService | Identity | src/Infrastructure/Identity/IdentityTokenClaimService.cs | BIZ-CAP-023 | ITokenClaimService | AA | HIGH | TA:security-architecture-assessment.md |
| APP-SVC-008 | EfRepository (Generic) | DataAccess | src/Infrastructure/Data/EfRepository.cs | BIZ-CAP-028 | IRepository<T>, IReadRepository<T> | AA | HIGH | BA:01_capability_map.md; ARCH-VIOL-009 (coupling=16) |
| APP-SVC-009 | CachedCatalogItemServiceDecorator | Catalog | src/BlazorAdmin/Services/CachedCatalogItemServiceDecorator.cs | BIZ-CAP-008 | ICatalogItemService (decorator) | AA | HIGH | DA:review-summary CORRECTED-3 |
| APP-SVC-010 | CatalogContextSeed | Infrastructure | src/Infrastructure/Data/CatalogContextSeed.cs | BIZ-CAP-009,029 | N/A (startup seed) | AA | HIGH | BA:01_capability_map.md; BR-36 |
| APP-SVC-011 | AppIdentityDbContextSeed | Identity | src/Infrastructure/Identity/AppIdentityDbContextSeed.cs | BIZ-CAP-026,029 | N/A (startup seed) | AA | HIGH | BR-13,37 |
| APP-SVC-012 | EmailSender (STUB) | Infrastructure | src/Infrastructure/Services/EmailSender.cs | BIZ-CAP-027 | IEmailSender | AA | HIGH | BR-08 — returns Task.CompletedTask |
| APP-SVC-013 | CustomAuthStateProvider | Identity | src/BlazorAdmin/CustomAuthStateProvider.cs | BIZ-CAP-025 | AuthenticationStateProvider | AA | HIGH | BA:01_capability_map.md; 60s poll |
| APP-SVC-014 | CachedCatalogViewModelService | Catalog | src/Web/Services/CachedCatalogViewModelService.cs | BIZ-CAP-001 | ICatalogViewModelService (decorator) | AA | HIGH | DA:review-summary CORRECTED-5; IMemoryCache 30s |

---

## Section 4 — Domain Entities (DATA-ENT-###)

| ID | Name | Business Concept | DB Table | DB | Domain | Aggregate Root? | Status | Owner Layer | Confidence | Key Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| DATA-ENT-001 | CatalogItem | Product | Catalog | CatalogDatabase | Catalog | No (root of CatalogAggregate informally) | Active | DA | HIGH | HiLo PK (catalog_hilo); Name nvarchar(50); Price decimal(18,2) |
| DATA-ENT-002 | CatalogBrand | Brand | CatalogBrands | CatalogDatabase | Catalog | No | Active | DA | HIGH | HiLo PK (catalog_brand_hilo); Brand nvarchar(100) |
| DATA-ENT-003 | CatalogType | Category (Product Type) | CatalogTypes | CatalogDatabase | Catalog | No | Active | DA | HIGH | HiLo PK (catalog_type_hilo); Type nvarchar(100) |
| DATA-ENT-004 | Basket | Shopping Basket | Baskets | CatalogDatabase | Basket | YES | Active | DA | HIGH | BuyerId nvarchar(256); IDENTITY PK |
| DATA-ENT-005 | BasketItem | Basket Line Item | BasketItems | CatalogDatabase | Basket | No | Active | DA | HIGH | UnitPrice locked at add-time; soft ref to CatalogItem (no FK) |
| DATA-ENT-006 | Order | Confirmed Purchase | Orders | CatalogDatabase | Order | YES | Active — Immutable | DA | HIGH | BuyerId nvarchar(256); ShipToAddress_* columns; no status field |
| DATA-ENT-007 | OrderItem | Order Line Item | OrderItems | CatalogDatabase | Order | No | Active | DA | HIGH | ItemOrdered_ProductName nvarchar(50) snapshot; UnitPrice decimal(18,2) |
| DATA-ENT-008 | Buyer | Buyer Profile | NONE (not persisted) | N/A | Buyer | YES | DORMANT | DA | HIGH | Not registered in CatalogContext; IdentityGuid string links to AspNetUsers |
| DATA-ENT-009 | PaymentMethod | Payment Method Record | NONE (not persisted) | N/A | Buyer | No | DORMANT | DA | HIGH | PCI comment references Stripe; CardId is token only; no raw card data |
| DATA-ENT-010 | ApplicationUser | Shopper / Buyer Identity | AspNetUsers | IdentityDatabase | Identity | YES | Active | DA | HIGH | Email HIGH PII; PasswordHash HIGH PII; PBKDF2/SHA-256 |
| DATA-ENT-011 | Address | Shipping Address | Orders (inlined) | CatalogDatabase | Order | No (value object) | Active | DA | HIGH | Owned entity — not a separate table |
| DATA-ENT-012 | CatalogItemOrdered | Purchase-Time Product Snapshot | OrderItems (inlined) | CatalogDatabase | Order | No (value object) | Active | DA | HIGH | Immutable snapshot; immune to future catalogue changes |
| DATA-ENT-013 | BaseEntity | Shared Kernel Base | NONE (abstract) | N/A | SharedKernel | N/A | Active | DA | HIGH | Provides int Id to all domain entities |

---

## Section 5 — DDD Aggregates (DATA-AGG-###)

| ID | Name | Root Entity | Child Entities | Status | Confidence | Evidence |
|---|---|---|---|---|---|---|
| DATA-AGG-001 | BasketAggregate | DATA-ENT-004 (Basket) | DATA-ENT-005 (BasketItem) | Active | HIGH | BA:05_data_model.md; DA:erd.md |
| DATA-AGG-002 | OrderAggregate | DATA-ENT-006 (Order) | DATA-ENT-007 (OrderItem), DATA-ENT-011 (Address VO), DATA-ENT-012 (CatalogItemOrdered VO) | Active — Immutable | HIGH | BA:05_data_model.md; DA:erd.md |
| DATA-AGG-003 | BuyerAggregate | DATA-ENT-008 (Buyer) | DATA-ENT-009 (PaymentMethod) | DORMANT | HIGH | DA:erd.md CONFIRMED DEAD — no DbSet in CatalogContext |
| DATA-AGG-004 | CatalogAggregate (informal) | DATA-ENT-001 (CatalogItem) | DATA-ENT-002 (CatalogBrand ref), DATA-ENT-003 (CatalogType ref) | Active | HIGH | BA:05_data_model.md; DA:erd.md |

---

## Section 6 — Data Repositories / Databases (DATA-REPO-###)

| ID | Name | Technology | Context Class | Connection Key | Tables | ID Strategy | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| DATA-REPO-001 | CatalogDatabase | SQL Server (Azure SQL Edge in Docker — EOL; LocalDB in dev) | CatalogContext | CatalogConnection | Catalog, CatalogBrands, CatalogTypes, Baskets, BasketItems, Orders, OrderItems | HiLo for CatalogItem/Brand/Type; IDENTITY for Basket/Order | DA | HIGH | DA:data-store-registry.md |
| DATA-REPO-002 | IdentityDatabase | SQL Server (Azure SQL Edge in Docker — EOL; LocalDB in dev) | AppIdentityDbContext | IdentityConnection | AspNetUsers, AspNetRoles, AspNetUserRoles, AspNetUserClaims, AspNetRoleClaims, AspNetUserLogins, AspNetUserTokens | Standard Identity (string GUIDs) | DA | HIGH | DA:data-store-registry.md |

---

## Section 7 — Caching Components

| ID | Name | Technology | TTL | Scope | Location | Invalidation | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| CACHE-001 | Web MVC Catalog Browse Cache | ASP.NET Core IMemoryCache (server-side in-process) | 30 seconds sliding | Web server process memory | eshopwebmvc container | TTL only — NOT invalidated by admin writes | DA | HIGH | CachedCatalogViewModelService.cs + CacheHelpers.cs |
| CACHE-002 | BlazorAdmin Catalog List Cache | Blazored.LocalStorage (browser localStorage) | 1 minute (DateCreated.AddMinutes(1)) | User's browser | Browser localStorage | Write-through for items (RefreshLocalStorageList); TTL-only for brands/types | DA | HIGH | CachedCatalogItemServiceDecorator.cs |

---

## Section 8 — Current Technology Stack (TECH-CUR-###)

| ID | Technology | Version | Category | EOL / Risk | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| TECH-CUR-001 | .NET 8 / ASP.NET Core SDK | 8.0.x | Runtime/SDK | LTS until November 2026 | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-002 | C# (LangVersion=latest) | C# 12 | Language | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-003 | ASP.NET Core MVC | 8.0 | Web Framework | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-004 | ASP.NET Core Web API + Ardalis.ApiEndpoints | 8.0 | API Framework | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-005 | Blazor WebAssembly | 8.0 | Frontend Framework | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-006 | Entity Framework Core (SQL Server provider) | UNKNOWN (Directory.Packages.props) | ORM | Current | TA | MEDIUM | TA:technology-stack-assessment.md |
| TECH-CUR-007 | ASP.NET Core Identity (EntityFrameworkCore) | UNKNOWN | Auth Framework | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-008 | JWT Bearer Authentication | UNKNOWN | Auth | Current — key hardcoded (BR-32) | TA | HIGH | TA:security-architecture-assessment.md |
| TECH-CUR-009 | Ardalis.Specification + EFCore provider | UNKNOWN | Repository Pattern | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-010 | MediatR | UNKNOWN | CQRS Mediator (Web layer only — NOT PublicApi) | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-011 | AutoMapper | UNKNOWN | DTO Mapping | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-012 | Blazored.LocalStorage | UNKNOWN | Browser Storage | Current — XSS risk (JWT in localStorage) | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-013 | FluentValidation (BlazorShared) | UNKNOWN | Validation | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-014 | Swashbuckle.AspNetCore (Swagger/OpenAPI) | UNKNOWN | API Documentation | Current — gate behind IsDevelopment() (ASMP-005) | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-015 | Azure.Identity + Azure Key Vault config | UNKNOWN | Cloud Secret Management | Current — Azure path only | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-016 | Docker Compose v3.4 + .NET 8 multi-stage build | 3.4 | Container Orchestration | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-017 | GitHub Actions CI (ubuntu-latest, dotnet 8.0.x) | N/A | CI/CD | Current — no secret scanning (TD-02) | TA | HIGH | TA:infrastructure-deployment-blueprint.md |
| TECH-CUR-018 | xUnit + NSubstitute (3 test projects) | UNKNOWN | Test Framework (primary) | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-019 | MSTest (PublicApiIntegrationTests only) | UNKNOWN | Test Framework (inconsistent — mixed with xUnit) | Current | TA | HIGH | TA:technology-stack-assessment.md; TD-18 |
| TECH-CUR-020 | Ardalis.GuardClauses + Ardalis.Result | UNKNOWN | Domain Utilities | Current | TA | HIGH | TA:technology-stack-assessment.md |
| TECH-CUR-021 | BlazorInputFile (superseded package) | UNKNOWN | UI Component | SUPERSEDED by .NET 5+ built-in InputFile | TA | HIGH | TD-16 |
| TECH-CUR-022 | BuildBundlerMinifier (deprecated) | UNKNOWN | Build Tool | DEPRECATED by Microsoft | TA | HIGH | TD-15 |

---

## Section 9 — Infrastructure Components (TECH-INF-###)

| ID | Name | Type | Image / Provider | Ports (host:container) | Owner Layer | Confidence | Evidence | Risk |
|---|---|---|---|---|---|---|---|---|
| TECH-INF-001 | eshopwebmvc Container | Docker Container | mcr.microsoft.com/dotnet/aspnet:8.0 | 5106:8080 | TA | HIGH | TA:infrastructure-deployment-blueprint.md | None |
| TECH-INF-002 | eshoppublicapi Container | Docker Container | mcr.microsoft.com/dotnet/aspnet:8.0 | 5200:8080 | TA | HIGH | TA:infrastructure-deployment-blueprint.md | None |
| TECH-INF-003 | sqlserver Container | Docker Container — SQL Server | mcr.microsoft.com/azure-sql-edge (no version pin) | 1433:1433 | TA | HIGH | TA:data-store-registry.md; TD-04, TD-05 | CRITICAL: EOL March 2025; no version pin; SA_PASSWORD hardcoded |
| TECH-INF-004 | Azure Key Vault | Cloud Secret Management | Azure | N/A | TA | HIGH | TA:infrastructure-deployment-blueprint.md | Active on Azure deployment path only |
| TECH-INF-005 | Azure App Service / Container Apps | Cloud Compute (inferred) | Azure | N/A | TA | LOW | TA:infrastructure-deployment-blueprint.md — inferred from abbreviations.json | No Bicep templates extracted to confirm |
| TECH-INF-006 | Azure Developer CLI (azd) IaC | Infrastructure as Code | Azure | N/A | TA | HIGH | TA:infrastructure-deployment-blueprint.md; infra/main.parameters.json | Bicep templates not extracted |

---

## Section 10 — Security Components (TECH-SEC-###)

| ID | Name | Type | Location | Owner Layer | Confidence | Evidence | Risk Level |
|---|---|---|---|---|---|---|---|
| TECH-SEC-001 | ASP.NET Core Identity (Cookie Auth) | Authentication — Cookie | Web MVC startup / Program.cs | TA | HIGH | TA:security-architecture-assessment.md | Low (standard) |
| TECH-SEC-002 | JWT Bearer Authentication | Authentication — Token | PublicApi / IdentityTokenClaimService.cs | TA | HIGH | TA:security-architecture-assessment.md | CRITICAL — key hardcoded in source |
| TECH-SEC-003 | Claims-Based Authorisation | Authorisation — Claims | ApplicationCore (System.Security.Claims) | TA | HIGH | TA:security-architecture-assessment.md | Low (standard) |
| TECH-SEC-004 | Azure Managed Identity / DefaultAzureCredential | Cloud Identity | Azure.Identity — active on Azure path only | TA | HIGH | TA:security-architecture-assessment.md | Low (standard) |
| TECH-SEC-005 | ASP.NET Core User Secrets (dev) | Dev Secret Management | Development environment only | TA | HIGH | TA:security-architecture-assessment.md | Low |
| TECH-SEC-006 | CSRF Anti-Forgery Tokens | Request Forgery Protection | Web MVC forms + Identity UI | TA | HIGH | TA:security-architecture-assessment.md | Low (standard) |
| TECH-SEC-007 | SA Password Hardcoded | Security VULNERABILITY | docker-compose.yml — SA_PASSWORD=@someThingComplicated1234 | TA | HIGH | TA:technical-debt-risk-register.md TD-01 | CRITICAL |

---

## Section 11 — Architecture Modules (MOD-###)

| ID | Name | Source Path | Boundary Strength | Migration Readiness | Component Count | Entry Points | Coupling Score | Owner Layer | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| MOD-001 | Admin | src/BlazorAdmin/ | Weak | Blocked | 23 | 2 | 5 | AA | HIGH |
| MOD-002 | ApplicationCore | src/ApplicationCore/ | Weak | Blocked | 13 | 0 | N/A | AA | HIGH |
| MOD-003 | Basket | src/ (basket files across Web+Core) | Weak | Blocked | 23 | 3 | 9 | AA | HIGH |
| MOD-004 | Catalog | src/ (catalog files across Web+Core+PublicApi) | Weak | Blocked | 66 | 9 | 13 | AA | HIGH |
| MOD-005 | CrossCutting | src/ (cross-cutting concerns) | Medium | Needs Refactoring | 10 | 7 | N/A | AA | HIGH |
| MOD-006 | DataAccess | src/Infrastructure/Data/ | Weak | Blocked | 2 | 0 | 5 | AA | HIGH |
| MOD-007 | Identity | src/ (identity files across Web+Infra+PublicApi) | Weak | Blocked | 66 | 20 | 6 | AA | HIGH |
| MOD-008 | Infrastructure | src/Infrastructure/ | Medium | Needs Refactoring | 3 | 0 | N/A | AA | HIGH |
| MOD-009 | Order | src/ (order files across Web+Core) | Weak | Blocked | 21 | 2 | 4 | AA | HIGH |
| MOD-010 | PublicApi | src/PublicApi/ | Strong | Needs Refactoring | 5 | 0 | N/A | AA | HIGH |
| MOD-011 | SharedContracts | src/BlazorShared/ | Medium | Needs Refactoring | 12 | 0 | N/A | AA | HIGH |
| MOD-012 | Verification (Tests) | tests/ | Medium | Needs Refactoring | 45 | 0 | N/A | AA | HIGH |
| MOD-013 | Web | src/Web/ | Weak | Blocked | 21 | 3 | 5 | AA | HIGH |

---

## Section 12 — PII Inventory Summary

| PII-ID | Table | Column | Sensitivity | GDPR Concern | Owner Layer | Confidence | Evidence |
|---|---|---|---|---|---|---|---|
| PII-01 | AspNetUsers | Email | HIGH | Core PII — right to erasure applies | DA | HIGH | DA:pii-inventory.json |
| PII-02 | AspNetUsers | UserName | MEDIUM | Likely = email (ASMP-001) | DA | HIGH | DA:pii-inventory.json |
| PII-03 | AspNetUsers | PasswordHash | HIGH | PBKDF2/SHA-256 — not reversible; must not be logged | DA | HIGH | DA:pii-inventory.json |
| PII-04 | AspNetUsers | PhoneNumber | MEDIUM | Optional field; right to erasure applies if populated | DA | HIGH | DA:pii-inventory.json |
| PII-05 | Orders | BuyerId | MEDIUM (escalates to HIGH if email — OQ-001) | Order records preserved post-user-deletion; erasure complexity | DA | HIGH | DA:pii-inventory.json |
| PII-06 | Orders | ShipToAddress_Street + _City + _State + _Country + _ZipCode | HIGH | Full physical address; right to erasure applies | DA | HIGH | DA:pii-inventory.json |
| PII-07 | Baskets | BuyerId | LOW (escalates to MEDIUM/HIGH if email — OQ-001) | Orphan baskets on user deletion | DA | HIGH | DA:pii-inventory.json |
| PII-08 | AspNetUserTokens | Value | HIGH | Auth token — right to erasure applies | DA | HIGH | DA:pii-inventory.json |

---

## Section 13 — Technical Debt Register (Critical and High items)

| TD-ID | Title | Severity | Category | Effort to Resolve | Owner Layer | Evidence |
|---|---|---|---|---|---|---|
| TD-01 | SA password hardcoded in docker-compose.yml | Critical | Security | Low (env var) | TA | docker-compose.yml; TA:technical-debt-risk-register.md |
| TD-02 | No secret scanning in CI pipeline | Critical | Security | Low (add Gitleaks/TruffleHog step) | TA | TA:technical-debt-risk-register.md |
| TD-03 | JWT token stored in browser localStorage (XSS accessible) | Critical | Security | High (migrate to httpOnly cookie) | TA | TA:technical-debt-risk-register.md |
| TD-04 | Azure SQL Edge container image at EOL (March 2025) | High | Infrastructure | Medium | TA | TA:data-store-registry.md |
| TD-05 | SQL Server container image has no version pin | High | Infrastructure | Low | TA | docker-compose.yml |
| TD-06 | CORS policy absent or AllowAnyOrigin (unconfirmed) | High | Security | Medium | TA | TA:security-architecture-assessment.md |
| TD-07 | No retry or circuit breaker on BlazorAdmin HTTP calls | High | Reliability | Medium | TA | TA:technical-debt-risk-register.md |
| TD-08 | No health check endpoints confirmed | High | Operations | Low-Medium | TA | TA:technical-debt-risk-register.md |
| TD-09 | No EF Core retry strategy for transient SQL errors | High | Reliability | Low | TA | TA:technical-debt-risk-register.md |
| TD-10 | 1-second artificial delay in catalogue browse endpoint | High | Performance | Minimal (delete 1 line) | TA | CatalogItemListPagedEndpoint.cs:42 |
| TD-11 | Docker Compose depends_on has no health-gate (startup race) | High | Operations | Low | TA | docker-compose.yml |
| TD-12 | No distributed cache — IMemoryCache is per-instance only | High | Scalability | High (Redis) | TA | TA:technical-debt-risk-register.md |
| TD-13 | ApplicationCore references BlazorShared (Clean Architecture violation) | High | Architecture | Medium | TA | TA:technical-debt-risk-register.md |
| TD-21 | Identity password minimum 6 chars — below NIST 800-63B minimum of 8 | Medium | Security | Low | TA | TA:nfr-registry.md |
| TD-22 | Swagger UI may not be gated behind IsDevelopment() | Medium | Security | Low | TA | TA:technical-debt-risk-register.md |

---

*Architecture Inventory — derived from 30+ source files across all 4 pipeline layers.*  
*Every row is traceable to source evidence. Confidence ratings reflect direct code evidence (HIGH) vs structural inference (MEDIUM/LOW).*
