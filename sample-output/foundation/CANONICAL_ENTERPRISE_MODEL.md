# Canonical Enterprise Model — eShopOnWeb
**Foundation Layer — Human-Readable Architecture**  
**Generated:** 2026-06-30  
**Pipeline Stage:** Foundation Synthesis (Layer 5 — Final)  
**Source Layers:** BA (Business Architecture) + DA (Data Architecture) + TA (Technology Architecture) + AA (Application Architecture)  
**Confidence Schema:** HIGH = direct code evidence confirmed by Agent 2; MEDIUM = inferred from structure; LOW = assumed from convention

---

## 1. Executive Summary

eShopOnWeb is the official Microsoft ASP.NET Core reference e-commerce implementation demonstrating Clean Architecture (Onion Architecture), Domain-Driven Design aggregates, and the Repository pattern. It is a **teaching codebase, not a production system**. Multiple production-blocking gaps are documented throughout this model.

**What it is:** A layered monolith (AA confidence 0.78) with Clean Architecture structural intent — four projects (ApplicationCore, Infrastructure, Web, PublicApi) with a dependency inversion rule where only ApplicationCore has zero outbound project references.

**What it includes:**
- A public-facing MVC storefront (Web) where shoppers browse products, add to basket, and complete checkout
- An admin REST API (PublicApi) consumed exclusively by a Blazor WebAssembly single-page admin panel (BlazorAdmin) embedded in the Web host
- Two SQL Server databases: CatalogDatabase (products, baskets, orders) and IdentityDatabase (users, roles)
- JWT-based authentication for PublicApi; cookie-based authentication for the MVC Web storefront

**Primary production blockers (must resolve before any real-world deployment):**
1. Hardcoded SA database password in docker-compose.yml (`@someThingComplicated1234`) — CRITICAL
2. Hardcoded JWT signing key in source code (`SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes`) — CRITICAL
3. Hardcoded seeded account passwords (`Pass@word1` for both demo and admin accounts) — CRITICAL
4. All orders record the same hardcoded shipping address (123 Main St., Kent, OH, 44240) — CRITICAL
5. Email notification system is entirely non-functional (EmailSender.cs returns immediately) — CRITICAL
6. Every catalogue browse request includes an artificial 1-second delay (`await Task.Delay(1000)`) — CRITICAL

---

## 2. Domain Model

### 2.1 Domain Boundary Map

```
+---------------------------------------------------------------------------+
|                           eShopOnWeb System                               |
|                                                                           |
|  +--------------------+     +--------------------+     +---------------+ |
|  |  CATALOG DOMAIN    |     |  BASKET DOMAIN     |     |  ORDER DOMAIN | |
|  |  (Active)          |     |  (Active)          |     |  (Active)     | |
|  |                    |---->|                    |---->|               | |
|  |  CatalogItem       |     |  Basket            |     |  Order        | |
|  |  CatalogBrand      |     |  BasketItem        |     |  OrderItem    | |
|  |  CatalogType       |     |                    |     |  Address VO   | |
|  |                    |     |  Price locked      |     |  Snapshot VO  | |
|  +--------------------+     |  at add-time       |     |               | |
|                             +--------------------+     +---------------+ |
|                                                                           |
|  +--------------------+     +--------------------+                       |
|  | IDENTITY DOMAIN    |     |  BUYER DOMAIN      |                       |
|  |  (Active)          |     |  (DORMANT)         |                       |
|  |                    |     |                    |                       |
|  |  ApplicationUser   |     |  BuyerAggregate    | <- not in DbContext   |
|  |  Roles (Identity)  |     |  PaymentMethod     | <- no service layer   |
|  |  JWT / Cookie      |     |  (PCI comment)     |                       |
|  +--------------------+     +--------------------+                       |
|                                                                           |
|  +-----------------------------------------------------------------------+|
|  |                    INFRASTRUCTURE / SHARED                            ||
|  |  EfRepository (generic) * EmailSender (STUB) * CatalogContextSeed    ||
|  |  AppIdentityDbContextSeed * IMemoryCache * localStorage cache         ||
|  +-----------------------------------------------------------------------+|
+---------------------------------------------------------------------------+
```

### 2.2 DDD Aggregate Inventory

| Aggregate | Root Entity | Child Entities / Value Objects | Status | Confidence |
|---|---|---|---|---|
| BasketAggregate | Basket | BasketItem | Active | HIGH |
| OrderAggregate | Order | OrderItem, Address (VO), CatalogItemOrdered (VO) | Active — Immutable after creation | HIGH |
| BuyerAggregate | Buyer | PaymentMethod | DORMANT — not in DbContext | HIGH |
| CatalogAggregate (informal) | CatalogItem | CatalogBrand (ref), CatalogType (ref) | Active | HIGH |

### 2.3 Cross-Domain Data Flows

**Flow: Shopper Purchase Journey**
```
1. Guest arrives -> GUID cookie assigned (10-year, essential, no consent required)
2. Shopper browses CatalogItem list -> price read from CatalogDatabase
3. Add to Basket -> BasketItem.UnitPrice locked at CatalogItem.Price at add-time
   (If item already in basket -> quantity incremented; original price preserved)
4. Shopper logs in (Web path) -> anonymous basket transferred to user basket
   (API login path does NOT trigger basket transfer)
5. Checkout -> OrderService creates Order with CatalogItemOrdered snapshot
   (Product name + PictureUri + price captured at checkout -- immune to future catalogue changes)
6. Basket permanently deleted after order saved
7. Email notification attempted -> EmailSender returns immediately (non-functional stub)
```

**Flow: Admin Catalogue Management**
```
1. Admin authenticates via POST /api/authenticate -> JWT issued (7-day expiry)
   (JWT key is hardcoded -- CRITICAL security gap)
2. BlazorAdmin stores JWT in browser localStorage (XSS accessible -- HIGH risk)
3. Admin reads catalogue -> CachedCatalogItemServiceDecorator checks localStorage (1-min TTL)
4. On cache miss -> HTTP GET /api/catalog-items -> PublicApi -> CatalogDatabase
5. Admin writes catalogue -> HTTP POST/PUT/DELETE /api/catalog-items -> PublicApi
   -> CatalogDatabase updated
   -> BlazorAdmin localStorage cache immediately refreshed (write-through)
   -> Web MVC IMemoryCache (30s) NOT invalidated -- storefront may show stale data for up to 30s
```

---

## 3. Capability Inventory

### 3.1 Active Capabilities

| ID | Capability | Domain | API / Handler | Status |
|---|---|---|---|---|
| BIZ-CAP-001 | Catalogue Discovery (Paged Browse) | Catalog | GET /api/catalog-items | Active — has mandatory 1-second delay (BR-09) |
| BIZ-CAP-002 | Single Product Retrieval | Catalog | GET /api/catalog-items/{id} | Active |
| BIZ-CAP-003 | Admin Product Creation | Catalog | POST /api/catalog-items | Active — Admin only |
| BIZ-CAP-004 | Admin Product Update | Catalog | PUT /api/catalog-items | Active — Admin only |
| BIZ-CAP-005 | Admin Product Deletion | Catalog | DELETE /api/catalog-items/{id} | Active — Admin only |
| BIZ-CAP-006 | Brand List Retrieval | Catalog | GET /api/catalog-brands | Active |
| BIZ-CAP-007 | Type List Retrieval | Catalog | GET /api/catalog-types | Active |
| BIZ-CAP-008 | Admin Browser-Cached Catalogue View | Catalog | CachedCatalogItemServiceDecorator | Active — 1-min localStorage |
| BIZ-CAP-009 | Database Catalogue Seeding | Catalog | CatalogContextSeed | Active |
| BIZ-CAP-010 | Basket Item Addition | Basket | BasketService | Active — auto-merge on duplicate |
| BIZ-CAP-011 | Basket Deletion | Basket | BasketService | Active |
| BIZ-CAP-012 | Anonymous-to-User Basket Transfer | Basket | BasketService.TransferBasketAsync | Active — Web login only |
| BIZ-CAP-013 | Basket Item Quantity Update | Basket | BasketService | Active |
| BIZ-CAP-014 | Basket Item Count Query | Basket | BasketQueryService | Active |
| BIZ-CAP-015 | Basket View with Product Details | Basket | BasketViewModelService | Active |
| BIZ-CAP-016 | Get or Create Basket | Basket | BasketViewModelService | Active |
| BIZ-CAP-017 | Order Creation from Basket | Order | OrderService | Active — hardcoded address gap (BR-15) |
| BIZ-CAP-018 | Order Total Calculation | Order | Order.Total() | Active — computed from OrderItems |
| BIZ-CAP-019 | Order History Retrieval | Order | GetMyOrdersHandler | Active |
| BIZ-CAP-020 | Order Detail View | Order | GetOrderDetailsHandler | Active |
| BIZ-CAP-021 | User Authentication (Web — Cookie) | Identity | ASP.NET Identity SignInManager | Active |
| BIZ-CAP-022 | User Authentication (API — JWT) | Identity | AuthenticateEndpoint | Active — does NOT trigger basket transfer |
| BIZ-CAP-023 | JWT Token Generation | Identity | IdentityTokenClaimService | Active — key hardcoded (BR-32) |
| BIZ-CAP-024 | New User Registration | Identity | Register.cshtml.cs | Active — email confirmation silently dropped (BR-27) |
| BIZ-CAP-025 | BlazorAdmin Auth State (60s poll) | Identity | CustomAuthStateProvider | Active |
| BIZ-CAP-026 | Identity and Role Seeding | Identity | AppIdentityDbContextSeed | Active — hardcoded passwords (BR-29, BR-37) |
| BIZ-CAP-028 | Generic Data Repository (EF Core) | Infrastructure | EfRepository | Active — 6 API endpoints violate Clean Arch |
| BIZ-CAP-029 | Database Seed and Migration on Startup | Infrastructure | Seed classes | Active — 10 retries before abort |

### 3.2 Non-Functional / Dormant Capabilities

| ID | Capability | Domain | Reason |
|---|---|---|---|
| BIZ-CAP-027 | Email Notification (Stub) | Infrastructure | EmailSender.cs returns Task.CompletedTask immediately |
| BIZ-CAP-030 | Buyer Account Structure | Buyer | BuyerAggregate not in DbContext; no service layer |
| BIZ-CAP-031 | Payment Method Record | Buyer | PaymentMethod not in DbContext; no checkout integration |

---

## 4. Key Business Rules

### 4.1 Critical Severity — Production Blockers

| Rule ID | Summary | Location |
|---|---|---|
| BR-08 | Email sending entirely non-functional — EmailSender.SendEmailAsync() returns Task.CompletedTask without any delivery | EmailSender.cs |
| BR-09 | Every catalogue browse request has a mandatory 1-second artificial delay | CatalogItemListPagedEndpoint.cs:42 |
| BR-15 | All orders record hardcoded shipping address: 123 Main St., Kent, OH, United States, 44240 | Checkout.cshtml.cs:57 |
| BR-27 | New user registration does not require email confirmation — account activated immediately | Register.cshtml.cs:77-88 |
| BR-29 | Default seeded account passwords hardcoded as plaintext in source (Pass@word1) | AuthorizationConstants.cs:8 |
| BR-32 | JWT signing key hardcoded as plaintext in source | AuthorizationConstants.cs:12 |

> Note: Both BR-29 and BR-32 carry explicit TODO comments in source code warning against production use.

### 4.2 High Severity — Functional Rules

| Rule ID | Summary |
|---|---|
| BR-01 | Orders snapshot product name, picture, and catalogue ID at purchase time — order history is immune to future catalogue changes |
| BR-02 | Login (Web path) merges anonymous basket into user basket; anonymous basket permanently deleted |
| BR-03 | Order creation requires non-empty basket; basket permanently deleted after order saved |
| BR-05 | Only ADMINISTRATORS role may create, update, or delete catalogue products |
| BR-06 | Only authenticated shoppers may proceed to checkout |
| BR-07 | Admin API JWT tokens carry user name and all assigned roles as claims |
| BR-12 | Orders have no status field — once created, orders are immutable |
| BR-14 | Domain entity constructors use guard clauses (Ardalis.GuardClauses) to enforce invariants |
| BR-18 | Checkout page requires authentication — [Authorize] on Checkout.cshtml.cs |
| BR-19 | Guard checks basket is non-empty before order creation |
| BR-20 | Catalogue product names must be unique |
| BR-21 | Catalogue product price must be greater than zero |
| BR-24 | JWT tokens expire 7 days after issue |
| BR-25 | Account lockout enabled on repeated failed password attempts |
| BR-30 | Shoppers can only view their own order history — cross-account access returns not-found |

### 4.3 Data Integrity Rules

| Rule ID | Summary |
|---|---|
| BR-04 | Basket add without explicit quantity defaults to 1 |
| BR-10 | Admin panel caches product list in browser localStorage for 1 minute; any write immediately clears and reloads |
| BR-11 | Order.BuyerId matches Buyer.IdentityGuid by string value convention — no database foreign key |
| BR-16 | Anonymous shoppers identified by 10-year GUID cookie marked as essential |
| BR-17 | Basket transfer at login only occurs if cookie value is a valid GUID |
| BR-23 | New catalogue products always receive a default placeholder image — direct admin image upload permanently disabled |
| BR-26 | Checkout form submission updates basket quantities before order is created |
| BR-33 | Shipping address field max lengths: postcode 18, street 180, state 60, country 90, city 100 characters |
| BR-34 | Payment method must never store full card details — PCI-compliant token, alias, and last 4 digits only |
| BR-35 | Buyer aggregate and PaymentMethod are structurally defined but entirely dormant |

---

## 5. Cross-Domain Flows

### 5.1 Place an Order (BIZ-PROC-001) — Primary Value Flow

```
ACTOR: Registered Shopper (BIZ-ACT-002)
ENTRY: POST /basket/checkout (Web MVC -- authenticated)

Step 1  Checkout.cshtml.cs reads basket -> BasketViewModelService
Step 2  Checkout form submits updated quantities -> BasketService.SetQuantities()
Step 3  [GAP] Shipping address: hardcoded "123 Main St." -- not collected from user (BR-15)
Step 4  OrderService.CreateOrderAsync(buyerId, Address, basket.Items)
         -> For each item: CatalogItemOrdered snapshot created
         -> Order entity assembled with all OrderItems
         -> IRepository<Order>.AddAsync() -> CatalogContext -> CatalogDatabase.Orders + OrderItems
Step 5  BasketService.DeleteBasketAsync(buyerId)
         -> Basket + all BasketItems permanently deleted
Step 6  IEmailSender.SendEmailAsync() -> returns immediately (non-functional stub)
Step 7  Redirect to Order Confirmation page

CROSS-DOMAIN REFERENCES:
  CatalogItem.Name + PictureUri + Id -> snapshotted into OrderItem (Catalog -> Order)
  Basket.BuyerId -> reused as Order.BuyerId (Basket -> Order via Identity reference)
  IdentityDatabase user -> referenced by BuyerId string convention (no FK)
```

### 5.2 Anonymous-to-User Basket Transfer (BIZ-PROC-004) — Cross-Domain Merge

```
ACTOR: Guest becoming Registered Shopper (Web path only)
ENTRY: POST /account/login (Web MVC only -- NOT API login)

Step 1  Login.cshtml.cs reads anonymous GUID from basket cookie
Step 2  Validate GUID format (BR-17) -- skip if invalid
Step 3  BasketService.TransferBasketAsync(anonymousId, username)
         -> Load anonymous basket + authenticated basket
         -> Merge anonymous items into user basket (increment quantity on duplicates)
         -> Original UnitPrice from first add preserved -- NOT refreshed from catalogue
         -> Delete anonymous basket
Step 4  ASP.NET Core Identity SignInManager.PasswordSignInAsync()
Step 5  Delete basket cookie

NOTE: API login (POST /api/authenticate) does NOT trigger this flow.
      BlazorAdmin users authenticating via API never get their anonymous basket merged.
```

### 5.3 Admin Catalogue Write (BIZ-PROC-005) — Write-Through Cache Invalidation

```
ACTOR: Product Administrator (BIZ-ACT-003) via BlazorAdmin
ENTRY: HTTP POST/PUT/DELETE /api/catalog-items (JWT required -- Administrators role)

Step 1  BlazorAdmin CachedCatalogItemServiceDecorator.Create/Update/DeleteAsync()
Step 2  HTTP call to PublicApi endpoint (JWT Bearer header)
Step 3  PublicApi endpoint writes to CatalogDatabase via EfRepository
Step 4  CachedCatalogItemServiceDecorator.RefreshLocalStorageList()
         -> Items cleared and reloaded; brands/types NOT refreshed (TTL-only for those)
Step 5  Web MVC IMemoryCache (30s sliding) is NOT invalidated
         -> Storefront may show stale catalogue for up to 30s after any admin write

ARCHITECTURE NOTE: 6 PublicApi endpoints depend directly on EfRepository
                   rather than domain services -- Clean Architecture violation
                   (ARCH-VIOL-001 through ARCH-VIOL-007)
```

---

## 6. Architectural Characteristics

### 6.1 Primary Architecture Pattern

**Clean Architecture (Onion / Ports-and-Adapters) — Intent**
- ApplicationCore project has zero outbound project references — the dependency rule is structurally enforced
- Domain entities (Order, Basket, CatalogItem) and service interfaces live in ApplicationCore
- EF Core, ASP.NET Identity, JWT helpers live in Infrastructure
- Web (MVC) and PublicApi (REST) are host adapters

**Layered Monolith — Observed Reality (AA confidence 0.78)**
- All projects build into a single deployable (Web) plus one companion API deployable (PublicApi)
- All 13 modules have weak or medium boundaries — no module qualifies for independent extraction
- Module dependency cycle detected: Admin -> ApplicationCore -> Basket -> Catalog -> DataAccess -> Identity -> Order -> Web
- ApplicationCore references BlazorShared — domain layer depends on UI-shared library (ARCH-VIOL-011)

### 6.2 Architecture Violations (Do Not Carry Forward)

| ID | Violation | Impact |
|---|---|---|
| ARCH-VIOL-001 | CatalogBrandListEndpoint depends directly on EfRepository | Bypasses domain service abstraction |
| ARCH-VIOL-002 | CatalogItemGetByIdEndpoint depends directly on EfRepository | Same |
| ARCH-VIOL-003 | CreateCatalogItemEndpoint depends directly on EfRepository | Same |
| ARCH-VIOL-004 | DeleteCatalogItemEndpoint depends directly on EfRepository | Same |
| ARCH-VIOL-005 | UpdateCatalogItemEndpoint depends directly on EfRepository | Same |
| ARCH-VIOL-006 | CatalogTypeListEndpoint depends directly on EfRepository | Same |
| ARCH-VIOL-007 | IndexModel depends directly on EfRepository | Same |
| ARCH-VIOL-008 | Module dependency cycle (Admin -> ... -> Web) | Prevents independent module extraction |
| ARCH-VIOL-009 | EfRepository coupling score = 16 | Highest coupling in codebase |
| ARCH-VIOL-010 | UriComposer coupling score = 8 | Infrastructure concern leaked across layers |
| ARCH-VIOL-011 | ApplicationCore references BlazorShared | Domain layer depends on UI-shared library |

### 6.3 Deployment Architecture

```
Docker Compose (docker-compose.yml v3.4):

  eshopwebmvc      <- Web MVC + BlazorAdmin host
  port 5106:8080   <- dev port on host, container port 8080

  eshoppublicapi   <- REST API
  port 5200:8080   <- dev port on host, container port 8080

  sqlserver        <- Azure SQL Edge (EOL March 2025 -- replace with SQL Server 2022)
  port 1433:1433   <- SA_PASSWORD hardcoded @someThingComplicated1234

Production path:
  Azure App Service / Container Apps (inferred from abbreviations.json -- no Bicep extracted)
  Azure Key Vault for secrets (sqlAdminPassword, appUserPassword)
  Azure Managed Identity / DefaultAzureCredential for Key Vault access

CI/CD:
  GitHub Actions -- dotnetcore.yml (build + test on ubuntu-latest, dotnet 8.0.x)
  No secret scanning step in CI pipeline (TD-02)
```

### 6.4 Authentication and Authorization Architecture

| Surface | Mechanism | Session Duration | Basket Transfer on Login |
|---|---|---|---|
| Web MVC Storefront | ASP.NET Core Identity Cookie | Browser session | YES — triggers anonymous basket merge |
| PublicApi (BlazorAdmin) | JWT Bearer (Authorization header) | 7 days | NO — does not trigger basket merge |
| Anonymous Shopper | GUID cookie (10-year, essential) | 10 years | N/A — converted on login |

**Known security gaps:**
- JWT secret key hardcoded in source (BR-32) — anyone with repo access can forge tokens
- JWT stored in browser localStorage (TD-03) — XSS attack can exfiltrate admin token
- Seeded account passwords hardcoded (BR-29) — use only for local development
- No CORS policy confirmed in extracted code (ASMP-004) — may be AllowAnyOrigin or absent
- Docker SA password hardcoded (TECH-SEC-007) — CRITICAL vulnerability in any networked environment
- Identity password minimum length of 6 characters — below NIST SP 800-63B minimum of 8

### 6.5 Caching Architecture

| Cache | Technology | TTL | Location | Invalidation |
|---|---|---|---|---|
| Web MVC Catalog Browse | ASP.NET Core IMemoryCache (server-side in-process) | 30 seconds sliding | Web server process | TTL only — NOT invalidated on admin writes |
| BlazorAdmin Catalog List | Blazored.LocalStorage (browser localStorage — client-side) | 1 minute | User's browser | Write-through for items; TTL-only for brands/types |

**Gap:** No distributed cache (Redis); IMemoryCache is per-instance. Horizontal scaling will cause stale-cache divergence across instances.

### 6.6 Data Architecture Summary

**Two SQL Server databases (distinct connection strings):**

| Database | Context Class | Domains | ID Strategy |
|---|---|---|---|
| CatalogDatabase (CatalogConnection) | CatalogContext | Catalog, Basket, Order | HiLo sequences for Catalog entities; IDENTITY for Basket/Order |
| IdentityDatabase (IdentityConnection) | AppIdentityDbContext | Identity (ASP.NET Core Identity) | Standard Identity |

**Cross-database soft references (no FK enforcement):**
- `Baskets.BuyerId` -> `AspNetUsers.Id` (cross-DB, application code only)
- `Orders.BuyerId` -> `AspNetUsers.Id` (cross-DB, application code only)

**Snapshot pattern (intentional immutability):**
- `OrderItem.ItemOrdered_ProductName` + `ItemOrdered_PictureUri` — frozen at checkout
- `BasketItem.UnitPrice` — frozen at basket-add time

### 6.7 Technology Maturity and Risks

| Component | Risk Level | Issue |
|---|---|---|
| Azure SQL Edge (sqlserver container) | CRITICAL | End-of-life March 2025 — replace with SQL Server 2022 |
| JWT key (AuthorizationConstants.cs) | CRITICAL | Hardcoded plaintext — must move to Key Vault or env var |
| SA password (docker-compose.yml) | CRITICAL | Hardcoded plaintext — must move to Docker secrets or env var |
| BlazorInputFile package | MEDIUM | Superseded by .NET 5+ built-in InputFile — remove package |
| BuildBundlerMinifier | MEDIUM | Deprecated by Microsoft — migrate to Webpack/esbuild |
| Mixed test frameworks (xUnit + MSTest) | LOW | Inconsistency across 4 test projects — standardise on xUnit |
| No retry/circuit breaker (BlazorAdmin HTTP) | HIGH | Transient HTTP failures cause immediate user-facing errors |
| No health check endpoints confirmed | HIGH | Cannot distinguish healthy/unhealthy containers in orchestration |

---

## 7. Production-Readiness Gap Summary

| Wave | ID | Gap | Priority |
|---|---|---|---|
| 1 (Critical) | AO-01 | Collect shipping address at checkout | Must-Have |
| 1 (Critical) | AO-02 | Implement transactional email delivery (SendGrid or SMTP) | Must-Have |
| 1 (Critical) | AO-03 | Externalise JWT key and default passwords to env vars or Azure Key Vault | Must-Have |
| 1 (Critical) | AO-04 | Remove await Task.Delay(1000) from CatalogItemListPagedEndpoint.cs:42 | Must-Have |
| 1 (Critical) | AO-05 | Integrate payment processing — activate Buyer aggregate | Must-Have |
| 2 (High) | AO-06 | Add order status lifecycle (PLACED -> PROCESSING -> SHIPPED -> DELIVERED -> CANCELLED) | High |
| 2 (High) | AO-07 | Add inventory management — StockQuantity validation at checkout | High |
| 2 (High) | AO-08 | Enforce email confirmation after AO-02 complete | High |
| 3 (Medium) | AO-09 | Fix identity seeding idempotency (role creation existence check) | Medium |
| 3 (Medium) | AO-10 | Cache brand and type lookups separately in BlazorAdmin | Medium |

---

*Canonical Enterprise Model — synthesised from 30+ layer output files across BA, DA, TA, AA pipeline stages.*  
*Every fact in this model is traceable to a specific source file and evidence reference.*  
*This document is the human-readable companion to ENTERPRISE_KNOWLEDGE_GRAPH.json.*
