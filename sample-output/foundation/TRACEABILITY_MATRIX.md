# Traceability Matrix — eShopOnWeb
**Foundation Layer — Capability-to-Stack Traceability**  
**Generated:** 2026-06-30  
**Pipeline Stage:** Foundation Synthesis (Layer 5 — Final)  
**Column Schema:** Capability -> Process -> Entity/Aggregate -> Service -> API -> Technology Stack  
**One row per capability (BIZ-CAP-###)**

---

## How to Read This Matrix

Each row traces a single business capability from business intent (left) through to technology stack (right):

- **Capability** — what the business does (BIZ-CAP-###)
- **Process** — which business process exercises this capability (BIZ-PROC-###)
- **Entity / Aggregate** — which domain entity or aggregate is operated on (DATA-ENT-### or DATA-AGG-###)
- **Service / Handler** — which application service implements the capability (APP-SVC-###)
- **API / Entry Point** — which REST endpoint or MVC action exposes it (APP-API-### or route)
- **Database** — which repository/database persists the data (DATA-REPO-###)
- **Technology Stack** — key technology components involved (TECH-CUR-###)
- **Confidence** — evidence quality for this row

---

## Catalog Domain Capabilities

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| Catalogue Discovery (Paged Browse) | BIZ-CAP-001 | VS-001 Stage 2 | DATA-ENT-001 (CatalogItem), DATA-ENT-002 (Brand), DATA-ENT-003 (Type) | APP-SVC-014 (CachedCatalogViewModelService) | APP-API-004 GET /api/catalog-items; Web MVC GET /catalog | DATA-REPO-001 (CatalogDatabase) | TECH-CUR-001 (.NET 8), TECH-CUR-003 (ASP.NET Core MVC), TECH-CUR-006 (EF Core), CACHE-001 (IMemoryCache 30s) | HIGH |
| Single Product Retrieval | BIZ-CAP-002 | VS-001 Stage 2 | DATA-ENT-001 (CatalogItem) | APP-SVC-008 (EfRepository) | APP-API-003 GET /api/catalog-items/{id} | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004 (ASP.NET Core Web API), TECH-CUR-006 | HIGH |
| Admin Product Creation | BIZ-CAP-003 | BIZ-PROC-005 | DATA-ENT-001 (CatalogItem) | APP-SVC-008 (EfRepository) | APP-API-005 POST /api/catalog-items | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-006, TECH-CUR-008 (JWT), TECH-SEC-002 | HIGH |
| Admin Product Update | BIZ-CAP-004 | BIZ-PROC-005 | DATA-ENT-001 (CatalogItem) | APP-SVC-008 (EfRepository) | APP-API-007 PUT /api/catalog-items | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-006, TECH-CUR-008, TECH-SEC-002 | HIGH |
| Admin Product Deletion | BIZ-CAP-005 | BIZ-PROC-005 | DATA-ENT-001 (CatalogItem) | APP-SVC-008 (EfRepository) | APP-API-006 DELETE /api/catalog-items/{id} | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-006, TECH-CUR-008, TECH-SEC-002 | HIGH |
| Brand List Retrieval | BIZ-CAP-006 | VS-001 Stage 2 | DATA-ENT-002 (CatalogBrand) | APP-SVC-008 (EfRepository) | APP-API-002 GET /api/catalog-brands | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-006 | HIGH |
| Type List Retrieval | BIZ-CAP-007 | VS-001 Stage 2 | DATA-ENT-003 (CatalogType) | APP-SVC-008 (EfRepository) | APP-API-008 GET /api/catalog-types | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-006 | HIGH |
| Admin Browser-Cached Catalogue View | BIZ-CAP-008 | BIZ-PROC-005 | DATA-ENT-001 (CatalogItem) | APP-SVC-009 (CachedCatalogItemServiceDecorator) | APP-API-004 (via cache or HTTP) | DATA-REPO-001 (on cache miss) | TECH-CUR-012 (Blazored.LocalStorage), TECH-CUR-005 (Blazor WASM), CACHE-002 (localStorage 1min) | HIGH |
| Database Catalogue Seeding | BIZ-CAP-009 | BIZ-PROC-007 | DATA-ENT-001, DATA-ENT-002, DATA-ENT-003 | APP-SVC-010 (CatalogContextSeed) | N/A (startup — no API) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-006 | HIGH |

---

## Basket Domain Capabilities

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| Basket Item Addition | BIZ-CAP-010 | BIZ-PROC-003 | DATA-AGG-001 (BasketAggregate), DATA-ENT-005 (BasketItem) | APP-SVC-001 (BasketService.AddItemToBasket) | Web MVC POST /basket/add | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-006, TECH-CUR-009 (Ardalis.Specification) | HIGH |
| Basket Deletion | BIZ-CAP-011 | BIZ-PROC-001 Step 5 | DATA-AGG-001 (BasketAggregate) | APP-SVC-001 (BasketService.DeleteBasketAsync) | Triggered internally by order creation | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-006 | HIGH |
| Anonymous-to-User Basket Transfer | BIZ-CAP-012 | BIZ-PROC-004 | DATA-AGG-001 (BasketAggregate x2 — anon + user) | APP-SVC-001 (BasketService.TransferBasketAsync) | Web MVC POST /account/login (side effect — NOT API login) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-007 (Identity), TECH-CUR-006 | HIGH |
| Basket Item Quantity Update | BIZ-CAP-013 | BIZ-PROC-001 Step 2 | DATA-ENT-005 (BasketItem) | APP-SVC-001 (BasketService.SetQuantities) | Web MVC POST /basket/checkout (form pre-step) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-006 | HIGH |
| Basket Item Count Query | BIZ-CAP-014 | VS-001 (navigation header) | DATA-AGG-001 (BasketAggregate) | APP-SVC-002 (BasketQueryService) | Web MVC view component | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-006 | HIGH |
| Basket View with Product Details | BIZ-CAP-015 | VS-001 Stage 3 | DATA-AGG-001 (BasketAggregate), DATA-ENT-001 (CatalogItem) | APP-SVC-003 (BasketViewModelService) | Web MVC GET /basket | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-006, TECH-CUR-011 (AutoMapper) | HIGH |
| Get or Create Basket | BIZ-CAP-016 | BIZ-PROC-003 Step 1 | DATA-AGG-001 (BasketAggregate) | APP-SVC-003 (BasketViewModelService) | Web MVC basket actions (internal) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-006 | HIGH |

---

## Order Domain Capabilities

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| Order Creation from Basket | BIZ-CAP-017 | BIZ-PROC-001 | DATA-AGG-002 (OrderAggregate), DATA-ENT-012 (CatalogItemOrdered snapshot) | APP-SVC-004 (OrderService.CreateOrderAsync) | Web MVC POST /basket/checkout (authenticated) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-006, TECH-CUR-009 | HIGH |
| Order Total Calculation | BIZ-CAP-018 | BIZ-PROC-001 | DATA-ENT-006 (Order), DATA-ENT-007 (OrderItem) | Order.Total() method (domain method) | Computed in domain — no separate API | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-006 | HIGH |
| Order History Retrieval | BIZ-CAP-019 | BIZ-PROC-002 | DATA-AGG-002 (OrderAggregate) | APP-SVC-005 (GetMyOrdersHandler) | Web MVC GET /order/my-orders (MediatR) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-010 (MediatR), TECH-CUR-006 | HIGH |
| Order Detail View | BIZ-CAP-020 | BIZ-PROC-002 | DATA-AGG-002 (OrderAggregate) | APP-SVC-006 (GetOrderDetailsHandler) | Web MVC GET /order/detail/{orderId} (MediatR) | DATA-REPO-001 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-010, TECH-CUR-006 | HIGH |

---

## Identity Domain Capabilities

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| User Authentication (Web — Cookie) | BIZ-CAP-021 | BIZ-PROC-004, BIZ-PROC-006 | DATA-ENT-010 (ApplicationUser) | ASP.NET Core Identity SignInManager | Web MVC POST /account/login | DATA-REPO-002 (IdentityDatabase) | TECH-CUR-001, TECH-CUR-003, TECH-CUR-007 (Identity), TECH-SEC-001 (Cookie) | HIGH |
| User Authentication (API — JWT) | BIZ-CAP-022 | VS-002 Stage 1 | DATA-ENT-010 (ApplicationUser) | APP-SVC-007 (IdentityTokenClaimService) | APP-API-001 POST /api/authenticate | DATA-REPO-002 | TECH-CUR-001, TECH-CUR-004, TECH-CUR-007, TECH-CUR-008 (JWT Bearer), TECH-SEC-002 | HIGH |
| JWT Token Generation | BIZ-CAP-023 | VS-002 Stage 1 | DATA-ENT-010 (ApplicationUser + Roles) | APP-SVC-007 (IdentityTokenClaimService) | APP-API-001 (internal — called by AuthenticateEndpoint) | DATA-REPO-002 | TECH-CUR-008, TECH-SEC-002 | HIGH |
| New User Registration | BIZ-CAP-024 | VS-003 | DATA-ENT-010 (ApplicationUser) | Register.cshtml.cs | Web MVC POST /account/register | DATA-REPO-002 | TECH-CUR-001, TECH-CUR-003, TECH-CUR-007, TECH-SEC-001 | HIGH |
| BlazorAdmin Auth State (60s poll) | BIZ-CAP-025 | VS-002 ongoing | DATA-ENT-010 (ApplicationUser JWT claims) | APP-SVC-013 (CustomAuthStateProvider) | Internal Blazor — polls JWT expiry every 60s | N/A (client-side JWT check) | TECH-CUR-005 (Blazor WASM), TECH-CUR-008, TECH-CUR-012 (localStorage) | HIGH |
| Identity and Role Seeding | BIZ-CAP-026 | BIZ-PROC-007 | DATA-ENT-010, ASP.NET Identity Roles | APP-SVC-011 (AppIdentityDbContextSeed) | N/A (startup — no API) | DATA-REPO-002 | TECH-CUR-001, TECH-CUR-007 | HIGH |

---

## Infrastructure Domain Capabilities

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| Email Notification (STUB — non-functional) | BIZ-CAP-027 | BIZ-PROC-001 Step 6, BIZ-PROC-006 | N/A (no entity persisted) | APP-SVC-012 (EmailSender — returns immediately) | N/A (no API — internal fire-and-forget) | N/A | TECH-CUR-001 only — no SMTP client present | HIGH |
| Generic Data Repository (EF Core) | BIZ-CAP-028 | All data-access processes | All entities | APP-SVC-008 (EfRepository) | N/A (infrastructure concern — no direct API) | DATA-REPO-001, DATA-REPO-002 | TECH-CUR-006 (EF Core), TECH-CUR-009 (Ardalis.Specification) | HIGH |
| Database Seed and Migration on Startup | BIZ-CAP-029 | BIZ-PROC-007 | DATA-ENT-001,002,003 (Catalog seed), DATA-ENT-010 (Identity seed) | APP-SVC-010 (CatalogContextSeed) + APP-SVC-011 (AppIdentityDbContextSeed) | N/A (startup — no API) | DATA-REPO-001, DATA-REPO-002 | TECH-CUR-001, TECH-CUR-006, TECH-CUR-007 | HIGH |

---

## Dormant Domain Capabilities (Buyer)

| Capability | ID | Process | Entity / Aggregate | Service / Handler | API / Entry Point | Database | Technology Stack | Confidence |
|---|---|---|---|---|---|---|---|---|
| Buyer Account Structure (DORMANT) | BIZ-CAP-030 | NONE — no active process | DATA-AGG-003 (BuyerAggregate — DORMANT) | NONE — no service layer | NONE — no API | NONE — not persisted | NONE — dormant code only | HIGH |
| Payment Method Record (DORMANT) | BIZ-CAP-031 | NONE — no active process | DATA-ENT-009 (PaymentMethod — DORMANT) | NONE | NONE | NONE — not persisted; PCI comment references Stripe | NONE — dormant code only | HIGH |

---

## Value Stream to Capability Cross-Reference

### VS-001 — Shopper Purchase Journey (7 stages)

| Stage | Stage Name | Capabilities Involved |
|---|---|---|
| 1 | Guest Arrives | BIZ-CAP-016 (get/create basket), BIZ-ACT-001 (GUID cookie) |
| 2 | Browse Catalogue | BIZ-CAP-001, BIZ-CAP-002, BIZ-CAP-006, BIZ-CAP-007 |
| 3 | Add to Basket | BIZ-CAP-010, BIZ-CAP-013 |
| 4 | Login / Register | BIZ-CAP-021, BIZ-CAP-024, BIZ-CAP-012 (basket transfer) |
| 5 | Checkout | BIZ-CAP-017, BIZ-CAP-018 |
| 6 | Order Confirmation | BIZ-CAP-011 (basket deleted), BIZ-CAP-027 (email stub) |
| 7 | View Order History | BIZ-CAP-019, BIZ-CAP-020 |

**Gap:** No payment processing (BIZ-CAP-031 dormant), no shipping address collection (BR-15), email notification non-functional (BR-08)

### VS-002 — Catalogue Lifecycle / Admin (7 stages)

| Stage | Stage Name | Capabilities Involved |
|---|---|---|
| 1 | Admin Authenticates | BIZ-CAP-022, BIZ-CAP-023 |
| 2 | View Catalogue (Cached) | BIZ-CAP-008 (localStorage cache), BIZ-CAP-001 (via PublicApi) |
| 3 | Create Product | BIZ-CAP-003 |
| 4 | Update Product | BIZ-CAP-004 |
| 5 | Delete Product | BIZ-CAP-005 |
| 6 | View Brands/Types | BIZ-CAP-006, BIZ-CAP-007 |
| 7 | Seeding (startup) | BIZ-CAP-009 |

**Gap:** 1-second delay on every catalogue load (BR-09), Web MVC cache not invalidated on admin writes

### VS-003 — New User Onboarding (4 stages)

| Stage | Stage Name | Capabilities Involved |
|---|---|---|
| 1 | Register Account | BIZ-CAP-024 |
| 2 | (Email Confirmation) | BIZ-CAP-027 — NON-FUNCTIONAL; email silently discarded |
| 3 | Login | BIZ-CAP-021 |
| 4 | Basket Transfer | BIZ-CAP-012 (if anon basket existed) |

---

## Entity-to-Service Ownership Matrix

| Entity / Aggregate | Primary Owner Service | Secondary Services (reads only) | Persisted By | Domain |
|---|---|---|---|---|
| DATA-ENT-001 (CatalogItem) | APP-SVC-008 (EfRepository via PublicApi) | APP-SVC-009 (cached read), APP-SVC-014 (MVC cached read) | DATA-REPO-001 | Catalog |
| DATA-ENT-002 (CatalogBrand) | APP-SVC-008 | APP-SVC-014 | DATA-REPO-001 | Catalog |
| DATA-ENT-003 (CatalogType) | APP-SVC-008 | APP-SVC-014 | DATA-REPO-001 | Catalog |
| DATA-AGG-001 (BasketAggregate) | APP-SVC-001 (BasketService) | APP-SVC-002 (count query), APP-SVC-003 (view model) | DATA-REPO-001 | Basket |
| DATA-AGG-002 (OrderAggregate) | APP-SVC-004 (OrderService) | APP-SVC-005 (history), APP-SVC-006 (detail) | DATA-REPO-001 | Order |
| DATA-AGG-003 (BuyerAggregate) | NONE (dormant) | NONE | NONE (not persisted) | Buyer |
| DATA-ENT-010 (ApplicationUser) | ASP.NET Core Identity (framework) | APP-SVC-007 (JWT reads), APP-SVC-011 (seeding) | DATA-REPO-002 | Identity |

---

*Traceability Matrix — one row per capability, fully traceable from business intent to technology stack.*  
*Evidence for every row is in ENTERPRISE_KNOWLEDGE_GRAPH.json and ARCHITECTURE_INVENTORY.md.*
