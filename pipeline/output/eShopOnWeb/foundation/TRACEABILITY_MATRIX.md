# Traceability Matrix — eShopOnWeb
**Source:** Foundation Synthesis Agent (BA-only run)
**Date:** 2026-06-30
**Format:** Capability → Process → Entity → Service → API

---

## How to Read This Matrix

Each row traces one business capability end-to-end:
- **Capability (BIZ-CAP-###)** — The business function
- **Process (BIZ-PROC-###)** — The process that exercises it (if any)
- **Entity (DATA-ENT-###)** — The primary domain entity created/read/updated/deleted
- **Service (APP-SVC-###)** — The application service implementing the capability
- **API / UI Surface** — The external interface (REST endpoint or Razor Page)

---

## Basket Domain

| Capability | Process | Entity (CRUD) | Service | API / UI Surface |
|------------|---------|---------------|---------|-----------------|
| BIZ-CAP-001 Basket Item Addition | BIZ-PROC-003 (Stage 2) | DATA-ENT-004 (U), DATA-ENT-005 (C) | APP-SVC-001 BasketService | Razor Page: /Basket (POST add item) |
| BIZ-CAP-002 Basket Deletion | BIZ-PROC-001 (Step 8) | DATA-ENT-004 (D), DATA-ENT-005 (D) | APP-SVC-001 BasketService | Internal — called after order creation |
| BIZ-CAP-003 Anon Basket Transfer | BIZ-PROC-003 (Stage 3) | DATA-ENT-004 (R+D anon, U authed) | APP-SVC-001 BasketService | Triggered by Login POST (APP-SVC-011) |
| BIZ-CAP-004 Basket Item Qty Update | BIZ-PROC-001 (Step 3) | DATA-ENT-005 (U) | APP-SVC-001 BasketService | Razor Page: /Basket (POST update) |
| BIZ-CAP-005 Basket Item Count Query | BIZ-PROC-003 (Stage 2) | DATA-ENT-005 (R) | APP-SVC-002 BasketQueryService | Razor Page layout header (GET) |
| BIZ-CAP-006 Basket View w/ Products | BIZ-PROC-003 (Stage 2) | DATA-ENT-004 (R), DATA-ENT-001 (R) | APP-SVC-003 BasketViewModelService | Razor Page: /Basket (GET) |
| BIZ-CAP-007 Get or Create Basket | BIZ-PROC-003 (Stage 2) | DATA-ENT-004 (R or C) | APP-SVC-003 BasketViewModelService | Razor Page: /Basket (GET init) |

## Order Domain

| Capability | Process | Entity (CRUD) | Service | API / UI Surface |
|------------|---------|---------------|---------|-----------------|
| BIZ-CAP-008 Order Creation from Basket | BIZ-PROC-001 (Steps 5–7) | DATA-ENT-008 (C), DATA-ENT-009 (C), DATA-ENT-011 (C), DATA-ENT-004 (D) | APP-SVC-004 OrderService | Razor Page: /Checkout (POST) via APP-SVC-010 |
| BIZ-CAP-009 Order Total Calculation | BIZ-PROC-001 (Step 7) | DATA-ENT-009 (R) | APP-SVC-013 Order Domain Logic | Internal — computed on Order entity |
| BIZ-CAP-010 Order History Retrieval | BIZ-PROC-002 (Steps 1–2) | DATA-ENT-008 (R) | APP-SVC-005 GetMyOrdersHandler | Razor Page: /MyOrders (GET) |
| BIZ-CAP-011 Order Detail View | BIZ-PROC-002 (Steps 3–5) | DATA-ENT-008 (R), DATA-ENT-009 (R), DATA-ENT-011 (R) | APP-SVC-006 GetOrderDetailsHandler | Razor Page: /MyOrders/{id} (GET) |

## Catalog Domain — Public

| Capability | Process | Entity (CRUD) | Service | API / UI Surface |
|------------|---------|---------------|---------|-----------------|
| BIZ-CAP-012 Paged Catalogue Browse | BIZ-PROC-003 (Stage 1) | DATA-ENT-001 (R), DATA-ENT-002 (R), DATA-ENT-003 (R) | APP-SVC-007 CachedCatalogItemServiceDecorator → ICatalogItemRepository | APP-API-001 GET /api/catalog-items?page=&pageSize=&brand=&type= |
| BIZ-CAP-013 Single Product Retrieval | BIZ-PROC-003 (Stage 1) | DATA-ENT-001 (R) | DATA-REPO-003 ICatalogItemRepository | APP-API-002 GET /api/catalog-items/{id} |

## Catalog Domain — Admin

| Capability | Process | Entity (CRUD) | Service | API / UI Surface |
|------------|---------|---------------|---------|-----------------|
| BIZ-CAP-014 Admin Catalogue Product Creation | — | DATA-ENT-001 (C) | DATA-REPO-003 ICatalogItemRepository | APP-API-003 POST /api/catalog-items (JWT, Administrator) |
| *(BIZ-CAP-015..017 — Admin Update/Delete — inferred from BIZ-RULE-005)* | — | DATA-ENT-001 (U/D) | DATA-REPO-003 | APP-API-004 PUT, APP-API-005 DELETE |

---

## Business Rule — Service — API Traceability

| Rule | Enforced In | At Layer | API / Page Affected |
|------|-------------|----------|---------------------|
| BIZ-RULE-001 (product snapshot) | CatalogItemOrdered.cs (DATA-ENT-011) | Domain Entity | APP-API-003 / /Checkout POST |
| BIZ-RULE-002 (basket transfer at login) | BasketService.TransferBasketAsync | Application Service | /Account/Login POST |
| BIZ-RULE-003 (non-empty basket required) | OrderService.CreateOrderAsync, Checkout.cshtml.cs | App Service + Page Model | /Checkout POST |
| BIZ-RULE-004 (default qty 1) | BasketService.AddItemToBasket, Basket.AddItem | App Service + Domain Entity | /Basket POST |
| BIZ-RULE-005 (admin-only catalog mutations) | [Authorize(Roles="Administrators")] | API Endpoint Authorization | APP-API-003, APP-API-004, APP-API-005 |
| BIZ-RULE-006 (checkout auth required) | [Authorize] on Checkout.cshtml.cs | Razor Page Authorization | /Checkout (all methods) |
| BIZ-RULE-007 (JWT admin auth) | IdentityTokenClaimService | App Service | Admin API (/api/*) |
| BIZ-RULE-008 (email no-op) | EmailSender.cs | Infrastructure Service | All email-triggering flows |
| BIZ-RULE-009 (1-sec delay) | CatalogItemListPagedEndpoint.cs:42 | API Endpoint | APP-API-001 |
| BIZ-RULE-010 (1-min cache) | CachedCatalogItemServiceDecorator.cs | Application Service Decorator | BlazorAdmin panel |
| BIZ-RULE-011 (BuyerId==IdentityGuid) | OrderService.CreateOrderAsync | Application Service | /Checkout POST |

---

## Actor — Capability — API Surface Traceability

| Actor | Capabilities | API / Page Surface | Auth Required |
|-------|--------------|--------------------|---------------|
| BIZ-ACT-001 Guest Shopper | BIZ-CAP-001, 005, 006, 007, 012, 013 | /Basket GET, /Catalog GET, APP-API-001, APP-API-002 | None |
| BIZ-ACT-002 Registered Shopper | BIZ-CAP-001..011 | /Basket GET+POST, /Checkout GET+POST, /MyOrders GET, APP-API-001, APP-API-002 | Cookie session |
| BIZ-ACT-003 System | BIZ-CAP-002, 003, 008 | Internal service calls | N/A |
| BIZ-ACT-004 Administrator | BIZ-CAP-014 + (inferred update/delete) | APP-API-003, APP-API-004, APP-API-005 | JWT Bearer (role: Administrators) |

---

## Entity — Aggregate — Repository — Service Traceability

| Entity | Aggregate | Repository | Primary Services Using It |
|--------|-----------|------------|--------------------------|
| DATA-ENT-001 CatalogItem | DATA-AGG-004 | DATA-REPO-003 | APP-SVC-003 (read for basket view), APP-SVC-007 (cached list), APP-API-001..005 |
| DATA-ENT-002 CatalogBrand | DATA-AGG-004 | DATA-REPO-003 | APP-API-001 (filter by brand) |
| DATA-ENT-003 CatalogType | DATA-AGG-004 | DATA-REPO-003 | APP-API-001 (filter by type) |
| DATA-ENT-004 Basket | DATA-AGG-001 | DATA-REPO-001 | APP-SVC-001, APP-SVC-002, APP-SVC-003, APP-SVC-004, APP-SVC-010 |
| DATA-ENT-005 BasketItem | DATA-AGG-001 | DATA-REPO-001 | APP-SVC-001, APP-SVC-002 |
| DATA-ENT-006 Buyer | DATA-AGG-003 | DATA-REPO-004 | APP-SVC-004 (order creation links buyer) |
| DATA-ENT-007 PaymentMethod | DATA-AGG-003 | DATA-REPO-004 | *(not exercised in visible BA scope)* |
| DATA-ENT-008 Order | DATA-AGG-002 | DATA-REPO-002 | APP-SVC-004, APP-SVC-005, APP-SVC-006 |
| DATA-ENT-009 OrderItem | DATA-AGG-002 | DATA-REPO-002 | APP-SVC-004 (creates), APP-SVC-006 (reads for detail) |
| DATA-ENT-010 Address | DATA-AGG-002 | DATA-REPO-002 | APP-SVC-004 (embeds in Order) |
| DATA-ENT-011 CatalogItemOrdered | DATA-AGG-002 | DATA-REPO-002 | APP-SVC-004 (creates snapshot), APP-SVC-006 (reads for detail) |
| DATA-ENT-012 ApplicationUser | — | Identity framework | APP-SVC-008 (claim generation), APP-SVC-011 (login) |

---

*Note: Rows marked (inferred) or with OQ/ASMP references require DA or AA layer evidence to confirm. Re-run synthesis after providing those layer outputs.*
