# 09 — Data Flow Diagram (DFD)
**eShopOnWeb — Forward Engineering Package**
**Generated:** 2026-06-30
**Pipeline Stage:** Foundation Synthesis Output (Layer 5 — Final)
**Single source of truth:** `ENTERPRISE_KNOWLEDGE_GRAPH.json`
**Actors:** BIZ-ACT-001 through BIZ-ACT-006 | **Processes:** BIZ-PROC-001 through BIZ-PROC-007

---

## 1. Purpose, Scope, and Notation

### 1.1 Purpose

This Data Flow Diagram models how data moves between external actors, system processes, and data stores across four primary business flows in eShopOnWeb. It establishes:

- Where data **originates** (sources), where it **rests** (stores), who **consumes** it (sinks)
- Which data is **PII-bearing** and where it crosses trust boundaries
- How the two independent caching layers interact with the primary data stores
- Cross-domain handoffs and the snapshot pattern at checkout

### 1.2 Primary Flows Covered

| Flow | Process ID | Value Stream |
|---|---|---|
| Browse Catalog (public storefront) | BIZ-PROC-003 | VS-001 Stage 2 |
| Add to Basket | BIZ-PROC-003 | VS-001 Stage 3 |
| Checkout — Place an Order | BIZ-PROC-001 | VS-001 Stage 5 |
| Admin Catalog Management | BIZ-PROC-005 | VS-002 |

### 1.3 Actors

| Actor ID | Name | Auth Mechanism |
|---|---|---|
| BIZ-ACT-001 | Guest Shopper (Anonymous) | 10-year essential GUID cookie (BIZ-RULE-016) |
| BIZ-ACT-002 | Registered Shopper | ASP.NET Identity cookie (Web) or JWT (API) |
| BIZ-ACT-003 | Product Administrator | JWT token (7-day expiry; BIZ-RULE-024) |
| BIZ-ACT-004 | Demo Shopper (demouser@microsoft.com) | Seeded account — hardcoded password (BIZ-RULE-029 CRITICAL) |
| BIZ-ACT-005 | Seeded Administrator (admin@microsoft.com) | Seeded account — hardcoded password (BIZ-RULE-013 CRITICAL) |
| BIZ-ACT-006 | Application Startup Process (System) | Internal; runs CatalogContextSeed + AppIdentityDbContextSeed |

### 1.4 Data Stores

| Store ID | Name | Technology | Context |
|---|---|---|---|
| DATA-REPO-001 | CatalogDatabase | SQL Server via CatalogContext EF | Catalog, Basket, Order tables |
| DATA-REPO-002 | IdentityDatabase | SQL Server via AppIdentityDbContext | AspNetUsers, Roles |
| CACHE-001 | Web MVC IMemoryCache | ASP.NET Core IMemoryCache (server-side, in-process) | 30s sliding TTL; per Web server instance |
| CACHE-002 | BlazorAdmin localStorage | Blazored.LocalStorage (browser client-side) | 1-minute TTL; per browser session |

---

## 2. Context Diagram (Level 0)

The system as a single process box — all actors and all data stores.

```mermaid
flowchart LR
    ANON(["Guest Shopper\nBIZ-ACT-001\nGUID cookie"])
    REG(["Registered Shopper\nBIZ-ACT-002\nIdentity cookie"])
    ADM(["Administrator\nBIZ-ACT-003\nJWT token"])
    SYS(["Application Startup\nBIZ-ACT-006"])

    ESYS["eShopOnWeb System\nWeb MVC APP-IF-001\nPublicApi APP-IF-002\nBlazorAdmin APP-IF-003"]

    CATDB[("CatalogDatabase\nDATA-REPO-001\nSQL Server")]
    IDDB[("IdentityDatabase\nDATA-REPO-002\nSQL Server")]

    ANON -->|"browse, add to basket"| ESYS
    REG -->|"browse, basket, checkout, orders"| ESYS
    ADM -->|"JWT auth, CRUD catalog"| ESYS
    SYS -->|"seed catalog + identity on startup"| ESYS

    ESYS -->|"product pages, basket view, order confirmation"| ANON
    ESYS -->|"product pages, basket, orders, JWT"| REG
    ESYS -->|"admin catalog views, API responses"| ADM

    ESYS <-->|"r/w CatalogItem, CatalogBrand, CatalogType\nr/w Basket, BasketItem\nr/w Order, OrderItem"| CATDB
    ESYS <-->|"r/w AspNetUsers, Roles, Claims"| IDDB

    classDef store fill:#dde,stroke:#449
    class CATDB,IDDB store
```

**Architecture note:** Two SQL Server databases share one physical container (`TECH-INF-003`). CatalogDatabase holds Catalog + Basket + Order entities. IdentityDatabase holds the full ASP.NET Core Identity schema. Both connected via separate EF Core contexts with separate connection strings.

---

## 3. Flow 1 — Browse Catalog (VS-001 Stage 2)

**Capabilities:** BIZ-CAP-001 (Paged Browse), BIZ-CAP-002 (Single Product), BIZ-CAP-006 (Brands), BIZ-CAP-007 (Types)
**Services:** APP-SVC-014 (CachedCatalogViewModelService), APP-SVC-008 (EfRepository)
**Cache:** CACHE-001 (IMemoryCache, 30s sliding TTL)

```mermaid
flowchart TB
    SHOPPER(["Shopper\nBIZ-ACT-001 or BIZ-ACT-002"])

    subgraph WEB["Web MVC — APP-IF-001 (eshopwebmvc :5106)"]
        CAT_PAGE["Catalog Index Page\nGET /catalog"]
        CACHED_SVC["CachedCatalogViewModelService\nAPP-SVC-014\nDecorator — wraps direct EF reads"]
    end

    CACHE1[("IMemoryCache\nCACHE-001\n30-second sliding TTL\nper-server-instance")]
    CATDB[("CatalogDatabase\nDATA-REPO-001\nCatalog table")]

    SHOPPER -->|"GET /catalog?brandId=&typeId=&page="| CAT_PAGE
    CAT_PAGE --> CACHED_SVC

    CACHED_SVC -->|"cache key = brand+type+page"| CACHE1
    CACHE1 -->|"HIT: return cached product list"| CACHED_SVC
    CACHE1 -->|"MISS: query needed"| CATDB
    CATDB -->|"CatalogItem + Brand + Type data"| CACHED_SVC
    CACHED_SVC -->|"populate cache (30s TTL)"| CACHE1
    CACHED_SVC -->|"catalog view model"| CAT_PAGE
    CAT_PAGE -->|"HTML catalog page with product grid"| SHOPPER

    note1["DEFECT: BIZ-RULE-009\nCatalogItemListPagedEndpoint includes\nawait Task.Delay(1000) on every request\nAO-04: DELETE this line"]

    classDef store fill:#dde,stroke:#449
    classDef defect fill:#fdd,stroke:#a44
    class CACHE1,CATDB store
    class note1 defect
```

**Cache gap (DISC-006):** DA Agent 1 missed this cache layer entirely. CachedCatalogViewModelService (APP-SVC-014) wraps ALL Web MVC catalog reads with 30-second IMemoryCache. The 30-second window means the storefront may show stale catalog data for up to 30 seconds after any admin write — the admin's BlazorAdmin localStorage cache does NOT invalidate this server-side cache.

**Performance defect (BIZ-RULE-009 — CRITICAL):** `CatalogItemListPagedEndpoint.cs:42` contains `await Task.Delay(1000)` — a mandatory 1-second artificial delay on EVERY catalog browse request. This is a known production blocker. AO-04 fix: delete this one line.

---

## 4. Flow 2 — Add to Basket (BIZ-PROC-003)

**Capabilities:** BIZ-CAP-010 (Add Item), BIZ-CAP-013 (Update Quantity), BIZ-CAP-016 (Get/Create Basket)
**Service:** APP-SVC-001 (BasketService)
**Rules:** BIZ-RULE-004 (default qty 1), DISC-007 (auto-merge on duplicate), BIZ-RULE-016 (essential GUID cookie)

```mermaid
flowchart TB
    GUEST(["Guest Shopper\nBIZ-ACT-001\nGUID cookie"])
    USER(["Registered Shopper\nBIZ-ACT-002\nIdentity cookie"])

    subgraph WEB["Web MVC — APP-IF-001"]
        ADD_ACTION["POST /basket/add\n(CatalogItemId + quantity)"]
        BASKET_SVC["BasketService\nAPP-SVC-001\nAddItemToBasket()"]
    end

    subgraph CATALOG_READ["Catalog Read (price lock)"]
        CI_READ["Read CatalogItem.Price\nfor UnitPrice lock"]
    end

    BASKET_DB[("Baskets + BasketItems\nDATA-REPO-001")]
    CATDB[("Catalog table\nDATA-REPO-001")]

    GUEST -->|"Add to basket (anonymous GUID BuyerId)"| ADD_ACTION
    USER -->|"Add to basket (email/username BuyerId)"| ADD_ACTION
    ADD_ACTION --> BASKET_SVC

    BASKET_SVC -->|"GetOrCreate basket by BuyerId"| BASKET_DB
    BASKET_DB -->|"existing basket or new basket"| BASKET_SVC

    BASKET_SVC --> CI_READ
    CI_READ -->|"read CatalogItem.Price"| CATDB
    CATDB -->|"current Price"| CI_READ
    CI_READ -->|"UnitPrice LOCKED at this value"| BASKET_SVC

    BASKET_SVC -->|"item already in basket?"| BASKET_SVC
    BASKET_SVC -->|"NO: add new BasketItem (default Qty=1 if not specified)"| BASKET_DB
    BASKET_SVC -->|"YES: INCREMENT Quantity only\nDO NOT update UnitPrice (DISC-007)"| BASKET_DB

    BASKET_DB -->|"updated basket"| WEB
    WEB -->|"redirect to basket view"| GUEST
    WEB -->|"redirect to basket view"| USER

    classDef store fill:#dde,stroke:#449
    class BASKET_DB,CATDB store
```

**Price lock (BIZ-RULE-010):** BasketItem.UnitPrice is frozen when the item is first added. If the same item is already in the basket, its UnitPrice does NOT update — only Quantity increments. This means the basket may show a different price than the current catalog price if catalog prices change between add and checkout.

**Anonymous basket (BIZ-RULE-016):** Guest shoppers have a 10-year essential GUID cookie (`BuyerId = GUID string`). This cookie is marked as "essential" and is NOT subject to consent banners.

**BuyerId ambiguity (OQ-001 / ASMP-001):** Unit test evidence (`TransferBasket.cs` uses `testuser@microsoft.com`) suggests BuyerId stores the user's email address, not their AspNetUsers.Id GUID. If confirmed, PII-05 and PII-07 must be elevated to HIGH sensitivity.

---

## 5. Flow 3 — Anonymous-to-User Basket Transfer (BIZ-PROC-004)

**Capability:** BIZ-CAP-012 (Basket Transfer)
**Service:** APP-SVC-001 (BasketService.TransferBasketAsync)
**CRITICAL:** This flow triggers ONLY on Web login (Login.cshtml.cs:83-114) — NOT on API login (AuthenticateEndpoint)

```mermaid
flowchart TB
    GUEST(["Guest Shopper with\nanonymous basket\nBIZ-ACT-001"])
    REGISTERED(["Registered Shopper\nBIZ-ACT-002"])

    subgraph WEB_LOGIN["Web MVC Login — POST /account/login"]
        LOGIN_PAGE["Login.cshtml.cs\nPasswordSignInAsync()"]
        GUID_CHECK{"Is basket cookie\na valid GUID?\n(BIZ-RULE-017)"}
        TRANSFER["BasketService\n.TransferBasketAsync(\n  anonymousId,\n  username)\nAPP-SVC-001"]
    end

    BASKET_DB[("Baskets + BasketItems\nDATA-REPO-001")]
    IDDB[("IdentityDatabase\nDATA-REPO-002")]

    GUEST -->|"POST /account/login\n(username + password + basket cookie)"| LOGIN_PAGE
    LOGIN_PAGE --> GUID_CHECK
    GUID_CHECK -->|"INVALID GUID: skip transfer"| LOGIN_PAGE
    GUID_CHECK -->|"valid GUID"| TRANSFER

    TRANSFER -->|"load anonymous basket (BuyerId=GUID)"| BASKET_DB
    TRANSFER -->|"load or create user basket (BuyerId=username)"| BASKET_DB

    BASKET_DB -->|"anon basket items"| TRANSFER
    BASKET_DB -->|"user basket"| TRANSFER

    TRANSFER -->|"merge: for each anon item\n  if already in user basket → INCREMENT qty\n  if not → add new item\n  UnitPrice NOT updated (original price preserved)"| BASKET_DB
    TRANSFER -->|"DELETE anonymous basket + all BasketItems"| BASKET_DB

    LOGIN_PAGE <-->|"authenticate user"| IDDB
    LOGIN_PAGE -->|"set Identity cookie\ndelete basket cookie"| REGISTERED

    note_api["API LOGIN DOES NOT TRIGGER TRANSFER\nPOST /api/authenticate (APP-API-001)\ndoes NOT call TransferBasketAsync\nBlazorAdmin users never get basket merged\n(BIZ-CAP-012 — Web path only)"]

    classDef store fill:#dde,stroke:#449
    classDef warn fill:#ffe,stroke:#a80
    class BASKET_DB,IDDB store
    class note_api warn
```

---

## 6. Flow 4 — Checkout / Place an Order (BIZ-PROC-001)

**Capabilities:** BIZ-CAP-017 (Order Creation), BIZ-CAP-018 (Order Total)
**Services:** APP-SVC-004 (OrderService.CreateOrderAsync), APP-SVC-001 (BasketService.DeleteBasketAsync)
**Rules:** BIZ-RULE-001 (snapshot), BIZ-RULE-003 (delete basket), BIZ-RULE-006 (auth required), BIZ-RULE-018 (checkout requires auth)
**PII flows:** BuyerId (PII-05), ShipToAddress_* (PII-06)

```mermaid
flowchart TB
    USER(["Registered Shopper\nBIZ-ACT-002\n[Authorize] required (BIZ-RULE-018)"])

    subgraph WEB_CHECKOUT["Web MVC Checkout — POST /basket/checkout (Authenticated)"]
        CHECKOUT_PAGE["Checkout.cshtml.cs"]
        UPDATE_QTY["BasketService.SetQuantities()\nUpdate quantities from form (BIZ-RULE-026)"]
        ORDER_SVC["OrderService\n.CreateOrderAsync(\n  buyerId,\n  shipToAddress,\n  basketItems)\nAPP-SVC-004"]
        DELETE_BASKET["BasketService\n.DeleteBasketAsync()\nAPP-SVC-001"]
        EMAIL_STUB["IEmailSender\n.SendEmailAsync()\nAPP-SVC-012\n(STUB — returns immediately)"]
    end

    subgraph ORDER_CREATION["Order Assembly (snapshot pattern)"]
        SNAPSHOT["For each BasketItem:\n1. Read CatalogItem.Name + PictureUri\n2. Create CatalogItemOrdered snapshot\n   (ItemOrdered_ProductName,\n    ItemOrdered_PictureUri,\n    ItemOrdered_CatalogItemId)\n3. UnitPrice copied from BasketItem.UnitPrice\n4. Freeze — immune to future catalog changes\n(BIZ-RULE-001)"]
        GAP["CURRENT GAP (BIZ-RULE-015):\nShipping address HARDCODED:\n123 Main St., Kent, OH 44240\nAO-01: collect from user input"]
    end

    BASKET_DB[("Baskets + BasketItems\nDATA-REPO-001")]
    CATDB[("Catalog table\nDATA-REPO-001\n(read for snapshot)")]
    ORDER_DB[("Orders + OrderItems\nDATA-REPO-001\nPII: BuyerId + ShipToAddress_*")]

    USER -->|"Submit checkout form (authenticated)"| CHECKOUT_PAGE
    CHECKOUT_PAGE -->|"1. Guard: basket not empty (BIZ-RULE-019)"| CHECKOUT_PAGE
    CHECKOUT_PAGE --> UPDATE_QTY
    UPDATE_QTY -->|"update BasketItem.Quantity from form"| BASKET_DB
    BASKET_DB --> ORDER_SVC
    ORDER_SVC --> SNAPSHOT
    SNAPSHOT -->|"read Name + PictureUri"| CATDB
    CATDB -->|"product details for snapshot"| SNAPSHOT
    GAP -->|"hardcoded Address()"| ORDER_SVC

    ORDER_SVC -->|"INSERT Order + OrderItems\nBuyerId (PII-05)\nShipToAddress_* (PII-06)\nCatalogItemOrdered snapshots"| ORDER_DB

    ORDER_SVC --> DELETE_BASKET
    DELETE_BASKET -->|"DELETE Basket + BasketItems permanently"| BASKET_DB

    ORDER_SVC --> EMAIL_STUB
    EMAIL_STUB -.->|"returns Task.CompletedTask immediately\n(BIZ-RULE-008 — non-functional)"| ORDER_SVC

    ORDER_DB -->|"order ID"| CHECKOUT_PAGE
    CHECKOUT_PAGE -->|"redirect to order confirmation"| USER

    classDef store fill:#dde,stroke:#449
    classDef gap fill:#fdd,stroke:#a44
    class BASKET_DB,CATDB,ORDER_DB store
    class GAP gap
```

**PII data at checkout:**
- `Order.BuyerId` (PII-05): user's identity reference — MEDIUM sensitivity (HIGH if email per OQ-001)
- `Order.ShipToAddress_*` (PII-06): full physical shipping address — HIGH sensitivity; right to erasure applies

**Non-functional email (BIZ-RULE-008 — CRITICAL):** `EmailSender.SendEmailAsync()` in `EmailSender.cs` returns `Task.CompletedTask` immediately. No email is ever sent. AO-02 must implement a real email delivery service before production.

**Basket deletion (BIZ-RULE-003):** Basket is permanently deleted after order creation. This action is irreversible. There is no order cancellation or basket restoration path (BIZ-RULE-012: orders immutable).

---

## 7. Flow 5 — Admin Catalog Management (BIZ-PROC-005)

**Capabilities:** BIZ-CAP-003 (Create), BIZ-CAP-004 (Update), BIZ-CAP-005 (Delete), BIZ-CAP-008 (Cached View)
**Services:** APP-SVC-009 (CachedCatalogItemServiceDecorator), APP-SVC-007 (IdentityTokenClaimService)
**Cache:** CACHE-002 (BlazorAdmin localStorage, 1-minute TTL, write-through)
**Auth:** BIZ-RULE-005 (ADMINISTRATORS role required; BIZ-RULE-007 JWT with roles as claims)

```mermaid
flowchart TB
    ADMIN(["Administrator\nBIZ-ACT-003\nJWT 7-day expiry"])

    subgraph AUTH_FLOW["Step 1: JWT Authentication"]
        AUTH_ENDPOINT["POST /api/authenticate\nAPP-API-001\nAuthenticateEndpoint"]
        TOKEN_SVC["IdentityTokenClaimService\nAPP-SVC-007\nIssue JWT with roles claims"]
        JWT_STORE["Browser localStorage\nJWT stored here\nXSS RISK (TD-03)"]
    end

    subgraph BLAZOR_ADMIN["BlazorAdmin SPA — APP-IF-003 (served by eshopwebmvc :5106)"]
        ADMIN_UI["Admin Catalog List\n/admin route"]
        CACHE_SVC["CachedCatalogItemServiceDecorator\nAPP-SVC-009\nBlaored.LocalStorage cache"]
        AUTH_STATE["CustomAuthStateProvider\nAPP-SVC-013\n60-second JWT expiry poll"]
    end

    subgraph PUBLIC_API["PublicApi — APP-IF-002 (eshoppublicapi :5200)"]
        LIST_EP["GET /api/catalog-items\nAPP-API-004\n⚠ await Task.Delay(1000) AO-04"]
        CREATE_EP["POST /api/catalog-items\nAPP-API-005\n[Authorize(ADMINISTRATORS)]"]
        UPDATE_EP["PUT /api/catalog-items\nAPP-API-007\n[Authorize(ADMINISTRATORS)]"]
        DELETE_EP["DELETE /api/catalog-items/{id}\nAPP-API-006\n[Authorize(ADMINISTRATORS)]"]
        BRANDS_EP["GET /api/catalog-brands\nAPP-API-002"]
        TYPES_EP["GET /api/catalog-types\nAPP-API-008"]
    end

    IDDB[("IdentityDatabase\nDATA-REPO-002")]
    CATDB[("CatalogDatabase\nDATA-REPO-001\nCatalog + CatalogBrands + CatalogTypes")]
    CACHE2[("BlazorAdmin localStorage\nCACHE-002\n1-minute TTL")]
    WEBMVC_CACHE[("Web MVC IMemoryCache\nCACHE-001\n30-second sliding TTL\nNOT invalidated by admin writes")]

    %% Auth flow
    ADMIN -->|"POST credentials"| AUTH_ENDPOINT
    AUTH_ENDPOINT <-->|"validate password"| IDDB
    AUTH_ENDPOINT --> TOKEN_SVC
    TOKEN_SVC -->|"JWT (7 days; Administrators role claim)"| AUTH_ENDPOINT
    AUTH_ENDPOINT -->|"JWT token"| JWT_STORE
    JWT_STORE --> BLAZOR_ADMIN

    %% Read flow
    ADMIN -->|"open /admin"| ADMIN_UI
    ADMIN_UI --> CACHE_SVC
    CACHE_SVC -->|"check localStorage TTL"| CACHE2
    CACHE2 -->|"HIT (< 1 minute): return cached list"| CACHE_SVC
    CACHE2 -->|"MISS or expired"| LIST_EP
    LIST_EP -->|"read Catalog table"| CATDB
    CATDB -->|"paginated CatalogItem list"| LIST_EP
    LIST_EP -->|"product list"| CACHE_SVC
    CACHE_SVC -->|"store in localStorage with timestamp"| CACHE2
    CACHE_SVC -->|"catalog list"| ADMIN_UI

    ADMIN_UI --> BRANDS_EP
    BRANDS_EP -->|"read CatalogBrands"| CATDB
    ADMIN_UI --> TYPES_EP
    TYPES_EP -->|"read CatalogTypes"| CATDB

    %% Write flow
    ADMIN -->|"Create product\n(JWT Bearer header)"| CREATE_EP
    CREATE_EP -->|"validate unique name (BIZ-RULE-020)\ndefault placeholder image (BIZ-RULE-023)"| CATDB
    CREATE_EP -->|"write-through: RefreshLocalStorageList()"| CACHE2

    ADMIN -->|"Update product"| UPDATE_EP
    UPDATE_EP -->|"write updated CatalogItem"| CATDB
    UPDATE_EP -->|"write-through: RefreshLocalStorageList()"| CACHE2

    ADMIN -->|"Delete product"| DELETE_EP
    DELETE_EP -->|"remove from Catalog"| CATDB
    DELETE_EP -->|"write-through: RefreshLocalStorageList()"| CACHE2

    CATDB -.->|"Web MVC cache NOT notified\nStorefront may show stale data\nfor up to 30s after write"| WEBMVC_CACHE

    classDef store fill:#dde,stroke:#449
    classDef warn fill:#ffe,stroke:#a80
    class CATDB,IDDB,CACHE2,WEBMVC_CACHE store
```

**Two independent caches — NOT cross-invalidated:**
- `CACHE-001` (Web MVC IMemoryCache, 30s): wraps storefront catalog reads; server-side, per-instance; admin writes do NOT invalidate this cache
- `CACHE-002` (BlazorAdmin localStorage, 1min): client-side per-browser; write-through for Create/Update/Delete; TTL-only for brands and types

**Cache staleness window:** An admin deletes a product at time T. Storefront shoppers may see that product for up to 30 seconds (CACHE-001 TTL) after deletion.

**XSS risk (TD-03):** JWT token is stored in browser localStorage. Any XSS attack on the BlazorAdmin page can exfiltrate the admin JWT token, which has a 7-day validity. AO-03 recommendation: migrate to httpOnly cookie for JWT storage.

**Architecture violation (ARCH-VIOL-001 through ARCH-VIOL-007):** Six PublicApi endpoints (CatalogBrandListEndpoint, CatalogItemGetByIdEndpoint, CreateCatalogItemEndpoint, DeleteCatalogItemEndpoint, UpdateCatalogItemEndpoint, CatalogTypeListEndpoint) inject EfRepository directly, bypassing domain service abstractions. This violates Clean Architecture. The forward engineering spec (FE-14) corrects this by routing through IRepository<T> interfaces.

---

## 8. PII Data Flow Map

Summary of all flows involving PII data, with sensitivity levels:

| PII ID | Field | Flow | Actor | Sensitivity | GDPR Note |
|---|---|---|---|---|---|
| PII-01 | AspNetUsers.Email | Registration, login, JWT claims | BIZ-ACT-002 | HIGH | Right to erasure applies |
| PII-02 | AspNetUsers.UserName | Login, basket transfer | BIZ-ACT-002 | MEDIUM | Likely = Email (ASMP-001) |
| PII-03 | AspNetUsers.PasswordHash | Login validation | BIZ-ACT-002 | HIGH | Never log; PBKDF2/SHA-256 |
| PII-04 | AspNetUsers.PhoneNumber | Account management | BIZ-ACT-002 | MEDIUM | Optional; erasure if populated |
| PII-05 | Orders.BuyerId | Checkout (Flow 4), order history | BIZ-ACT-002 | MEDIUM/HIGH | Cross-DB soft ref; post-deletion retention |
| PII-06 | Orders.ShipToAddress_* | Checkout (Flow 4) | BIZ-ACT-002 | HIGH | Full physical address; right to erasure |
| PII-07 | Baskets.BuyerId | Add to basket (Flow 2) | BIZ-ACT-001/002 | LOW/MEDIUM | Orphan risk on user deletion |
| PII-08 | AspNetUserTokens.Value | JWT token storage | BIZ-ACT-003 | HIGH | Auth token; right to erasure |

**PII in transit — checkout flow (BIZ-RULE-015 CRITICAL):** Current source code hardcodes shipping address "123 Main St., Kent, OH, United States, 44240" in `Checkout.cshtml.cs:57`. Real user PII (ShipToAddress_*) is never actually collected or stored in the current implementation. AO-01 must be implemented to collect real shipping addresses — at which point PII-06 flows become active and require full GDPR treatment.

---

## 9. Startup Flow (BIZ-PROC-007)

**Services:** APP-SVC-010 (CatalogContextSeed), APP-SVC-011 (AppIdentityDbContextSeed)
**Rules:** BIZ-RULE-036 (10 retry attempts), BIZ-RULE-037 (idempotency bug on role creation)

```mermaid
flowchart LR
    SYS(["Application Startup\nBIZ-ACT-006"])

    subgraph CATALOG_SEED["CatalogContextSeed — APP-SVC-010"]
        CAT_CHECK{"CatalogItems exist?"}
        CAT_SKIP["Skip seeding"]
        CAT_SEED["Seed 5 brands\n4 types\n12 products\n(BIZ-RULE-031)"]
        RETRY["Retry up to 10x\non DB failure\n(BIZ-RULE-036)"]
    end

    subgraph IDENTITY_SEED["AppIdentityDbContextSeed — APP-SVC-011"]
        ROLE_CREATE["CreateAsync(Administrators)\n⚠ NO existence check\n→ duplicate role error on restart\n(BIZ-RULE-037 / AO-09)"]
        USER_ADMIN["admin@microsoft.com\nRole: Administrators\nPassword: Pass@word1 HARDCODED\n(BIZ-RULE-013 CRITICAL)"]
        USER_DEMO["demouser@microsoft.com\nPassword: Pass@word1 HARDCODED\n(BIZ-RULE-029 CRITICAL)"]
    end

    CATDB[("CatalogDatabase\nDATA-REPO-001")]
    IDDB[("IdentityDatabase\nDATA-REPO-002")]

    SYS --> CATALOG_SEED
    SYS --> IDENTITY_SEED

    CATALOG_SEED --> RETRY
    RETRY --> CAT_CHECK
    CAT_CHECK -->|"YES"| CAT_SKIP
    CAT_CHECK -->|"NO"| CAT_SEED
    CAT_SEED -->|"INSERT brands, types, items"| CATDB

    IDENTITY_SEED --> ROLE_CREATE
    ROLE_CREATE -->|"INSERT role"| IDDB
    ROLE_CREATE --> USER_ADMIN
    ROLE_CREATE --> USER_DEMO
    USER_ADMIN -->|"INSERT user + role assignment"| IDDB
    USER_DEMO -->|"INSERT user"| IDDB

    classDef store fill:#dde,stroke:#449
    classDef critical fill:#fdd,stroke:#a44
    class CATDB,IDDB store
    class USER_ADMIN,USER_DEMO critical
```

**AO-09 fix for BIZ-RULE-037:** Change identity seeding to:
```csharp
if (!await roleManager.RoleExistsAsync(AuthorizationConstants.Roles.ADMINISTRATORS))
    await roleManager.CreateAsync(new IdentityRole(AuthorizationConstants.Roles.ADMINISTRATORS));
```

---

*Data Flow Diagram — 5 primary business flows from ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*All actor, service, and data store IDs traceable to EKG node IDs.*
*PII data flows highlighted with sensitivity levels PII-01 through PII-08.*
