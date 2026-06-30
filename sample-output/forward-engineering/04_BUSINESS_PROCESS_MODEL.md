# Business Process Model

**System:** eShopOnWeb
**Source of truth:** ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline/sample-output/foundation/)
**Generated:** 2026-06-30
**Pipeline stage:** Forward Engineering — Document 04 of 20
**Confidence schema:** HIGH = direct code evidence confirmed; MEDIUM = inferred from structure; LOW = assumed from convention

> Every process, step, actor, rule, and value stream below traces to node IDs in ENTERPRISE_KNOWLEDGE_GRAPH.json. All 7 business processes (BIZ-PROC-001..007) are fully described. Process steps are derived from source code evidence (Login.cshtml.cs, OrderService.cs, Checkout.cshtml.cs, CatalogContextSeed.cs, etc.) and confirmed by the DA Agent 2 review. No process, actor, rule, or step is invented.

---

## 1. Process Inventory

| Process ID | Name | Domain | Primary Actor(s) | Steps (evidenced) | Confidence |
|------------|------|--------|-----------------|-------------------|------------|
| **BIZ-PROC-001** | Place an Order at Checkout | Order, Basket | BIZ-ACT-002 | 7 | HIGH |
| **BIZ-PROC-002** | View Order History and Order Detail | Order | BIZ-ACT-002 | 4 | HIGH |
| **BIZ-PROC-003** | Add Item to Basket (Anonymous Shopper) | Basket, Catalog | BIZ-ACT-001, BIZ-ACT-002 | 4 | HIGH |
| **BIZ-PROC-004** | Anonymous-to-User Basket Transfer at Login | Basket, Identity | BIZ-ACT-001 → BIZ-ACT-002 | 5 | HIGH |
| **BIZ-PROC-005** | Admin Creates / Manages a Catalogue Product | Catalog, Identity | BIZ-ACT-003 | 5 | HIGH |
| **BIZ-PROC-006** | New User Registration | Identity | BIZ-ACT-001 | 4 | HIGH |
| **BIZ-PROC-007** | Database Seeding on Application Startup | Infrastructure | BIZ-ACT-006 | 4 | HIGH |

---

## 2. Value Streams

Three primary value streams organise the 7 processes into end-to-end customer journeys. Each value stream spans multiple domains and processes.

### VS-001 — Shopper Purchase Journey

**Actors:** BIZ-ACT-001 (Guest), BIZ-ACT-002 (Registered Shopper)  
**Outcome:** Confirmed, correctly-priced order with immutable product snapshots  
**Critical gaps:**
- Hardcoded shipping address (BIZ-RULE-015 — AO-01 blocker)
- No payment processing (BIZ-CAP-030, BIZ-CAP-031 dormant — AO-05 blocker)
- No order fulfilment lifecycle (BIZ-RULE-012 — orders immutable — AO-06)
- Email confirmation non-functional (BIZ-RULE-008 — AO-02 blocker)

```
Stage 1: Browse Catalogue
  Actor: BIZ-ACT-001 / BIZ-ACT-002
  Process: BIZ-PROC-003 (partial)
  Capability: BIZ-CAP-001
  Known defect: 1-second artificial delay on every browse (BIZ-RULE-009)

Stage 2: View Product / Select Item
  Actor: BIZ-ACT-001 / BIZ-ACT-002
  Capability: BIZ-CAP-002

Stage 3: Add to Basket
  Actor: BIZ-ACT-001 (anonymous basket) or BIZ-ACT-002 (user basket)
  Process: BIZ-PROC-003
  Capability: BIZ-CAP-010, BIZ-CAP-016
  Key: Price locked at add-time; auto-merge on duplicate item

Stage 4: Login / Basket Transfer (if anonymous)
  Actor: BIZ-ACT-001 → BIZ-ACT-002
  Process: BIZ-PROC-004
  Capability: BIZ-CAP-012, BIZ-CAP-021
  Key: Web login only — API login does NOT trigger transfer (BIZ-RULE-002)

Stage 5: Checkout
  Actor: BIZ-ACT-002 (authenticated required)
  Process: BIZ-PROC-001
  Capability: BIZ-CAP-017, BIZ-CAP-018
  CRITICAL GAP: Hardcoded shipping address (BIZ-RULE-015)
  CRITICAL GAP: No payment processing

Stage 6: Order Confirmation
  Actor: BIZ-ACT-002
  Process: BIZ-PROC-001 (post-order)
  Capability: BIZ-CAP-019, BIZ-CAP-020
  Key: Immutable order snapshot (BIZ-RULE-001)

Stage 7: Email Notification
  Actor: BIZ-ACT-002 (intended recipient)
  Capability: BIZ-CAP-027
  CRITICAL GAP: EmailSender.cs is a non-functional stub (BIZ-RULE-008)
```

**Process flow for VS-001:**
```
[BIZ-ACT-001/002] --> Browse Catalogue (BIZ-PROC-003)
                   --> [Optional login: BIZ-PROC-006]
                   --> [If anonymous + login: BIZ-PROC-004 transfer]
                   --> Checkout (BIZ-PROC-001)
                   --> Order confirmation
                   --> [Email attempt: BIZ-CAP-027 STUB -- no delivery]
```

---

### VS-002 — Catalogue Lifecycle (Admin)

**Actors:** BIZ-ACT-003 (Product Administrator)  
**Outcome:** Product catalogue kept current with admin-controlled additions, updates, deletions  
**Critical gaps:**
- 1-second artificial delay on every catalogue load (BIZ-RULE-009 — AO-04 blocker)
- Web MVC storefront shows stale data for up to 30 seconds after any admin write (CACHE-001 not invalidated on writes)

```
Stage 1: Admin Authentication (JWT)
  Actor: BIZ-ACT-003
  Process: BIZ-PROC-006 (sub-process)
  Capability: BIZ-CAP-022, BIZ-CAP-023
  CRITICAL GAP: JWT signing key hardcoded (BIZ-RULE-032)

Stage 2: View Catalogue (BlazorAdmin)
  Actor: BIZ-ACT-003
  Process: BIZ-PROC-005
  Capability: BIZ-CAP-008
  Cache: localStorage 1-min TTL (BIZ-RULE-010)
  Known defect: 1-second delay on cache miss (BIZ-RULE-009)

Stage 3: Create / Update / Delete Product
  Actor: BIZ-ACT-003
  Process: BIZ-PROC-005
  Capability: BIZ-CAP-003, BIZ-CAP-004, BIZ-CAP-005
  Validation: BIZ-RULE-020, 021, 022, 023

Stage 4: Admin Cache Refresh
  Capability: BIZ-CAP-008
  Mechanism: Write-through invalidation for items; TTL-only for brands/types (BIZ-RULE-010)

Stage 5: Storefront Update
  Capability: BIZ-CAP-001
  KNOWN GAP: Web MVC IMemoryCache (30s sliding TTL) not invalidated by admin writes
  -- storefront may show stale catalogue for up to 30 seconds
```

---

### VS-003 — New User Onboarding

**Actors:** BIZ-ACT-001 (Guest) transitioning to BIZ-ACT-002 (Registered Shopper)  
**Outcome:** Active, authenticated user account  
**Critical gaps:**
- Email confirmation silently discarded — account activated immediately (BIZ-RULE-027 — AO-02, AO-08 blockers)

```
Stage 1: Register Account
  Actor: BIZ-ACT-001
  Process: BIZ-PROC-006
  Capability: BIZ-CAP-024
  CRITICAL GAP: No email confirmation required (BIZ-RULE-027)

Stage 2: Account Activation (Immediate)
  Capability: BIZ-CAP-024
  Current behaviour: Account active immediately after registration

Stage 3: First Login
  Actor: BIZ-ACT-002 (newly registered)
  Process: BIZ-PROC-006
  Capability: BIZ-CAP-021

Stage 4: Basket Transfer (if had anonymous basket)
  Actor: BIZ-ACT-002
  Process: BIZ-PROC-004
  Capability: BIZ-CAP-012
```

---

## 3. Process Specifications

### BIZ-PROC-001 — Place an Order at Checkout

**Domain:** Order, Basket  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Confidence:** HIGH  
**Evidence:** Checkout.cshtml.cs; OrderService.CreateOrderAsync; BasketService; CatalogItemOrdered.cs  
**Cross-domain handoff:** Basket consumed and deleted; Order created with CatalogItemOrdered snapshots

**Trigger:** Authenticated shopper navigates to the Checkout page.

**Entry point:** POST /basket/checkout (Web MVC — authenticated)

**Preconditions:**
- Shopper is authenticated (BIZ-RULE-018 [Authorize] on Checkout.cshtml.cs)
- Basket is non-empty (BIZ-RULE-019 enforced by GuardExtensions.EmptyBasketOnCheckout)

**Process Steps:**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Checkout.cshtml.cs reads current basket state via BasketViewModelService (BIZ-CAP-015) | System | — |
| **Step 2** | Shopper reviews basket quantities; Checkout form submission calls BasketService.SetQuantities() to apply quantity updates | BIZ-ACT-002 + System | BIZ-RULE-026 |
| **Step 3** | **[CRITICAL GAP — BIZ-RULE-015]** Shipping address is hardcoded to "123 Main St., Kent, OH, United States, 44240" — not collected from user. Address object constructed with hardcoded values in Checkout.cshtml.cs:57. | System | BIZ-RULE-015 (gap), BIZ-RULE-033 |
| **Step 4** | OrderService.CreateOrderAsync(buyerId, hardcodedAddress, basket.Items) is called — for each basket item, a CatalogItemOrdered value object is created capturing: CatalogItemId, ProductName (snapshot), PictureUri (snapshot). Order entity assembled with OrderDate = DateTime.UtcNow | System (APP-SVC-004) | BIZ-RULE-001, BIZ-RULE-011 |
| **Step 5** | **[BIZ-RULE-019]** GuardExtensions.EmptyBasketOnCheckout validates basket has items. If empty: throws exception; process aborts. IRepository<Order>.AddAsync() persists Order + all OrderItems to CatalogDatabase.Orders and CatalogDatabase.OrderItems. | System | BIZ-RULE-003, BIZ-RULE-014, BIZ-RULE-019 |
| **Step 6** | BasketService.DeleteBasketAsync(buyerId) permanently removes Basket and all BasketItems from CatalogDatabase. | System (APP-SVC-001) | BIZ-RULE-003 |
| **Step 7** | IEmailSender.SendEmailAsync() is called. **[CRITICAL GAP — BIZ-RULE-008]** EmailSender.cs returns Task.CompletedTask immediately — no email is delivered. | System (APP-SVC-012 stub) | BIZ-RULE-008 (gap) |

**Postconditions:**
- Order record exists in CatalogDatabase.Orders with immutable product snapshots
- Order.BuyerId = shopper's identity string (cross-DB soft reference — BIZ-RULE-011)
- Basket and all BasketItems permanently deleted (BIZ-RULE-003)
- No email confirmation sent (BIZ-RULE-008 gap)
- Shopper redirected to order confirmation page

**Data entities touched:**
- READ: DATA-ENT-004 (Basket), DATA-ENT-005 (BasketItems)
- WRITE: DATA-ENT-006 (Order), DATA-ENT-007 (OrderItems), DATA-ENT-011 (Address VO — inlined), DATA-ENT-012 (CatalogItemOrdered VO — inlined)
- DELETE: DATA-ENT-004 (Basket), DATA-ENT-005 (BasketItems)

**Exception Paths:**
- Empty basket at checkout: BIZ-RULE-019 guard throws; order not created; basket preserved
- Not authenticated: BIZ-RULE-018 redirect to login
- Database failure at Step 5: order not saved; basket state preserved (no orphaned partial order)

**Domain events (candidates — INFERRED):**
- EVT-06 CheckoutRejectedEmptyBasket (if Step 5 guard triggers)
- EVT-04 OrderPlaced (on successful order creation)
- EVT-05 OrderTotalCalculated

**Process pain points:**
- BIZ-RULE-015: Hardcoded shipping address makes this process unusable in production (AO-01)
- BIZ-RULE-008: No email confirmation provides poor post-checkout user experience (AO-02)
- BIZ-RULE-012: No order status lifecycle after order is placed (AO-06)

---

### BIZ-PROC-002 — View Order History and Order Detail

**Domain:** Order  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Confidence:** HIGH  
**Evidence:** OrderController.cs; GetMyOrdersHandler; GetOrderDetailsHandler; BIZ-RULE-030

**Trigger:** Authenticated shopper navigates to "My Orders" or clicks on a specific order.

**Entry points:**
- Order history: /Order/MyOrders (Web MVC — authenticated)
- Order detail: /Order/Detail/{orderId} (Web MVC — authenticated)

**Preconditions:**
- Shopper is authenticated
- For order detail: the requested order belongs to the authenticated shopper (BIZ-RULE-030)

**Process Steps:**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Shopper navigates to My Orders page. System extracts BuyerId from the authenticated user's identity claims. | BIZ-ACT-002 | — |
| **Step 2** | GetMyOrdersHandler (MediatR) queries CatalogDatabase.Orders WHERE BuyerId = current user's identity string. **[BIZ-RULE-030]** Other shoppers' orders are never included. | System (APP-SVC-005) | BIZ-RULE-030 |
| **Step 3** | System returns list of Order records (DATA-ENT-006) with OrderDate and Order.Total() calculated. Shopper sees their order history. | System | BIZ-RULE-011 |
| **Step 4** | Shopper selects an order. GetOrderDetailsHandler (MediatR) queries by Order.Id AND BuyerId. If Order.BuyerId ≠ current user: returns not-found (never exposes another user's order). System returns full order with all OrderItems and embedded CatalogItemOrdered snapshots (product name, picture URI as recorded at purchase time). | System (APP-SVC-006) | BIZ-RULE-001, BIZ-RULE-030 |

**Postconditions:**
- Shopper sees their own complete order history
- Product details in order detail reflect purchase-time snapshots (BIZ-RULE-001)

**Data entities touched:**
- READ: DATA-ENT-006 (Order), DATA-ENT-007 (OrderItems), DATA-ENT-012 (CatalogItemOrdered VO)

**Process pain points:**
- BIZ-RULE-012: No order status field — shopper cannot see if order is being processed, shipped, or delivered (AO-06)

---

### BIZ-PROC-003 — Add Item to Basket (Anonymous Shopper)

**Domain:** Basket, Catalog  
**Primary Actor:** BIZ-ACT-001 (Anonymous) or BIZ-ACT-002 (Authenticated)  
**Confidence:** HIGH  
**Evidence:** BasketService.AddItemToBasket; Basket/Index.cshtml.cs; BIZ-RULE-004  
**Cross-domain handoff:** CatalogItem.Price locked into BasketItem.UnitPrice at add time

**Trigger:** Shopper clicks "Add to Basket" on the catalogue or product detail page.

**Entry point:** Web MVC basket add action (POST — no authentication required)

**Preconditions:**
- CatalogItem exists in CatalogDatabase (DATA-ENT-001)
- For anonymous: GUID cookie is present or will be created (BIZ-RULE-016)

**Process Steps:**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Shopper selects an item and optionally specifies quantity. **[BIZ-RULE-004]** If no quantity specified, defaults to 1. System identifies the BuyerId: GUID for anonymous (from 10-year cookie), username for authenticated. | BIZ-ACT-001 / BIZ-ACT-002 | BIZ-RULE-004, BIZ-RULE-016 |
| **Step 2** | **[Get or Create — BIZ-CAP-016]** System checks if a Basket record (DATA-ENT-004) exists for this BuyerId. If not, creates a new Basket with BuyerId = GUID (anonymous) or username (authenticated). | System (APP-SVC-003) | — |
| **Step 3** | System reads CatalogItem.Price at this moment from CatalogDatabase. **[CRITICAL RULE]** This price is locked into BasketItem.UnitPrice — it will NOT change if the catalogue price is later updated. Cross-domain: this is the Catalog → Basket price handoff. | System | — |
| **Step 4** | **[Auto-merge rule]** System checks existing BasketItems for matching CatalogItemId. If found: increment existing BasketItem.Quantity. If not found: create new BasketItem (DATA-ENT-005) with CatalogItemId, UnitPrice (locked), Quantity. Persist updated Basket aggregate (DATA-AGG-001). | System (APP-SVC-001) | — |

**Postconditions:**
- BasketItem exists in CatalogDatabase.BasketItems
- Price locked at add-time (UnitPrice does not auto-update)
- BasketItem count updated (BIZ-CAP-014)

**Data entities touched:**
- READ: DATA-ENT-001 (CatalogItem — for price), DATA-ENT-004 (Basket — check/create)
- WRITE: DATA-ENT-004 (Basket), DATA-ENT-005 (BasketItem)

**Domain events (candidates — INFERRED):**
- EVT-01 ItemAddedToBasket

**Process pain points:**
- Price locked at add-time means a price change between "add to basket" and "checkout" will not be reflected — the shopper sees the add-time price, not the current price

---

### BIZ-PROC-004 — Anonymous-to-User Basket Transfer at Login

**Domain:** Basket, Identity  
**Primary Actor:** BIZ-ACT-001 → BIZ-ACT-002 (Guest transitioning to Registered Shopper)  
**Confidence:** HIGH  
**Evidence:** Login.cshtml.cs:83-114; BasketService.TransferBasketAsync; BIZ-RULE-002  
**Cross-domain handoff:** Identity login event triggers basket transfer (Web path only)

**Trigger:** Anonymous shopper submits the Web MVC login form.

**Entry point:** POST /account/login (Web MVC ONLY — NOT /api/authenticate)

**Preconditions:**
- Shopper has a valid GUID basket cookie (BIZ-RULE-016)
- Shopper has valid credentials for an existing account

**Process Steps:**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Login.cshtml.cs reads the anonymous basket GUID from the basket cookie. | System | BIZ-RULE-016 |
| **Step 2** | **[BIZ-RULE-017]** System validates the cookie value is a valid GUID format using Guid.TryParse(). If not a valid GUID: transfer is skipped; login proceeds normally without any basket merge. | System | BIZ-RULE-017 |
| **Step 3** | System calls BasketService.TransferBasketAsync(anonymousGuid, authenticatedUsername): loads both the anonymous basket and the user's existing basket. For each item in the anonymous basket: if the same CatalogItemId exists in the user basket → increment quantity (original prices preserved; NOT refreshed from catalogue); if new item → add to user basket. System deletes the anonymous Basket record and all its BasketItems permanently. | System (APP-SVC-001) | BIZ-RULE-002 |
| **Step 4** | ASP.NET Core Identity SignInManager.PasswordSignInAsync() completes authentication; cookie issued. | System | BIZ-RULE-025 |
| **Step 5** | System deletes the anonymous basket GUID cookie from the browser. | System | — |

**Postconditions:**
- Anonymous basket permanently deleted (BIZ-RULE-002)
- User's basket contains merged items from both baskets
- UnitPrice values are NOT refreshed from catalogue — original add-time prices preserved
- User is authenticated with ASP.NET Core Identity cookie

**[KEY ARCHITECTURE NOTE]**
This process is ONLY triggered by the Web MVC login path (Login.cshtml.cs). The API authentication path (BIZ-PROC-006 / BIZ-CAP-022 / POST /api/authenticate) does NOT trigger basket transfer. BlazorAdmin users who authenticate via the API never experience anonymous basket transfer.

**Domain events (candidates — INFERRED):**
- EVT-03 AnonymousBasketTransferred

**Process pain points:**
- Shopping carts built on mobile/API clients cannot be transferred at API login — users may experience basket loss if they switch from API-authenticated to Web-authenticated contexts

---

### BIZ-PROC-005 — Admin Creates / Manages a Catalogue Product

**Domain:** Catalog, Identity  
**Primary Actor:** BIZ-ACT-003 (Product Administrator)  
**Confidence:** HIGH  
**Evidence:** CreateCatalogItemEndpoint.cs; CachedCatalogItemServiceDecorator.cs; BIZ-RULE-005, 020, 021, 022, 023

**Trigger:** Admin navigates to the BlazorAdmin catalogue management interface and initiates a create, update, or delete action.

**Entry point:** POST/PUT/DELETE /api/catalog-items (PublicApi — JWT required with Administrators role)

**Preconditions:**
- Admin has a valid JWT token (BIZ-CAP-022)
- JWT token contains the "Administrators" role claim (BIZ-RULE-005)

**Process Steps (Create path — most complex):**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Admin submits new product form in BlazorAdmin SPA: Name, Description, Price, BrandId, TypeId. BlazorAdmin calls CachedCatalogItemServiceDecorator.CreateAsync(). HTTP POST /api/catalog-items is sent with JWT Bearer token header. | BIZ-ACT-003 | — |
| **Step 2** | **[BIZ-RULE-005]** CreateCatalogItemEndpoint enforces [Authorize(Roles = "ADMINISTRATORS")] — returns 401/403 if JWT is missing, expired, or lacks the Administrators claim. System validates all guard clauses: BIZ-RULE-020 (unique name), BIZ-RULE-021 (price > 0), BIZ-RULE-022 (non-empty name/description). | System (APP-API-005) | BIZ-RULE-005, BIZ-RULE-020, BIZ-RULE-021, BIZ-RULE-022 |
| **Step 3** | **[BIZ-RULE-023]** System assigns a default placeholder image URI — admin cannot upload a custom image (image upload is permanently disabled in the current implementation). CatalogItem entity created in memory with all validated fields plus default image. | System | BIZ-RULE-023 |
| **Step 4** | EfRepository.AddAsync() persists the new CatalogItem to CatalogDatabase.Catalog table (DATA-ENT-001). ID assigned via HiLo sequence (catalog_hilo). | System (APP-SVC-008) | ARCH-VIOL-003 — direct endpoint → EfRepository dep |
| **Step 5** | **[BIZ-RULE-010]** CachedCatalogItemServiceDecorator.RefreshLocalStorageList() is called: clears the localStorage item cache and reloads the full list. **[STALENESS NOTE]** Web MVC IMemoryCache (CACHE-001, 30-second sliding TTL) is NOT invalidated — the public storefront may show the old catalogue for up to 30 seconds after any admin write. | System (APP-SVC-009) | BIZ-RULE-010 |

**Update path variation (PUT /api/catalog-items):**
- Same JWT validation (Step 2)
- Name/description/price guards re-validated (Steps 2-3, excluding uniqueness on update)
- CatalogItem record updated in-place; HiLo ID unchanged
- **[BIZ-RULE-001]** Existing OrderItems with snapshots of this product are NOT affected — historical order records remain correct
- Write-through cache refresh triggered (Step 5)

**Delete path variation (DELETE /api/catalog-items/{id}):**
- Same JWT validation
- CatalogItem deleted from CatalogDatabase.Catalog
- **[BIZ-RULE-001]** Existing OrderItems retain their CatalogItemOrdered snapshots — no corruption of historical orders
- **[ORPHAN RISK]** BasketItems with soft reference to this CatalogItemId become orphaned (no DB FK)
- Write-through cache refresh triggered

**Postconditions:**
- CatalogDatabase.Catalog reflects the admin's change
- BlazorAdmin localStorage cache is immediately refreshed
- Web MVC storefront may serve stale data for up to 30 seconds

**Domain events (candidates — INFERRED):**
- EVT-08 CatalogItemCreated
- EVT-09 CatalogItemDeleted
- EVT-10 CatalogCacheRefreshed

**Process pain points:**
- ARCH-VIOL-003..007: PublicApi endpoints call EfRepository directly — no domain service abstraction layer
- GAP-015: Cross-cache staleness between BlazorAdmin localStorage and Web MVC IMemoryCache
- BIZ-RULE-023: No image upload capability; all products show default placeholder

---

### BIZ-PROC-006 — New User Registration

**Domain:** Identity  
**Primary Actor:** BIZ-ACT-001 (Guest Shopper becoming Registered Shopper)  
**Confidence:** HIGH  
**Evidence:** Register.cshtml.cs; BIZ-RULE-027, BIZ-RULE-028  
**Gap:** Email confirmation attempt silently discarded (BIZ-RULE-008, BIZ-RULE-027)

**Trigger:** Guest shopper navigates to the registration page and submits the form.

**Entry point:** POST /account/register (Web MVC — no authentication required)

**Preconditions:**
- Shopper does not have an existing account with the same email address

**Process Steps:**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step 1** | Shopper completes the registration form: email address, password (6-100 characters), password confirmation. System validates all input fields. | BIZ-ACT-001 | BIZ-RULE-028 |
| **Step 2** | **[BIZ-RULE-028]** Input validation: email must be valid format; password must be 6-100 characters; password and confirmation must match. If any validation fails: form is re-displayed with error messages; no account created. | System | BIZ-RULE-028 |
| **Step 3** | System calls ASP.NET Core Identity UserManager.CreateAsync() to create a new ApplicationUser (DATA-ENT-010) in IdentityDatabase.AspNetUsers. PasswordHash stored as PBKDF2/SHA-256 (not reversible). | System | BIZ-RULE-025 |
| **Step 4** | **[CRITICAL GAP — BIZ-RULE-027]** Register.cshtml.cs:77-88 generates an email confirmation token via UserManager.GenerateEmailConfirmationTokenAsync() but the token is immediately discarded — no email confirmation is sent. Account is activated immediately without email verification. The gap exists because BIZ-RULE-008 (EmailSender stub) makes email delivery impossible. | System | BIZ-RULE-008 (gap), BIZ-RULE-027 (gap) |

**Postconditions:**
- New ApplicationUser created in IdentityDatabase.AspNetUsers
- Account is immediately active — no email verification required (BIZ-RULE-027 gap)
- Account lockout policy applies from creation (BIZ-RULE-025)
- Shopper signed in automatically and redirected

**Data entities touched:**
- WRITE: DATA-ENT-010 (ApplicationUser in IdentityDatabase)

**Process pain points:**
- BIZ-RULE-027: No email confirmation creates a compliance gap — accounts can be created with unverified email addresses (AO-02 + AO-08 blockers)
- BIZ-RULE-008: Email system must be activated (AO-02) before email confirmation can be enforced (AO-08)
- BIZ-RULE-028: Password minimum length of 6 is below NIST SP 800-63B minimum of 8

**Domain events (candidates — INFERRED):**
- (No confirmed EVT for registration in the graph; EmailConfirmationRequested would be implied by AO-08)

---

### BIZ-PROC-007 — Database Seeding on Application Startup

**Domain:** Infrastructure  
**Primary Actor:** BIZ-ACT-006 (Application Startup Process)  
**Confidence:** HIGH  
**Evidence:** CatalogContextSeed.cs; AppIdentityDbContextSeed.cs; BIZ-RULE-036, BIZ-RULE-037

**Trigger:** Application starts up (both CatalogContextSeed and AppIdentityDbContextSeed are called from Program.cs startup pipeline).

**Entry point:** Application startup sequence (no HTTP endpoint — internal)

**Preconditions:**
- CatalogDatabase connection string (CatalogConnection) is configured
- IdentityDatabase connection string (IdentityConnection) is configured

**Sub-process A — Catalogue Seeding (CatalogContextSeed):**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step A1** | CatalogContextSeed.SeedAsync() is called. **[BIZ-RULE-036]** System attempts database connection with retry logic — Polly-style retry up to 10 times with back-off on database failure before aborting startup. | BIZ-ACT-006 | BIZ-RULE-036 |
| **Step A2** | **[BIZ-RULE-031]** System checks if any data exists in CatalogDatabase.Catalog. If any product records exist: seeding is skipped entirely (idempotent operation). | System | BIZ-RULE-031 |
| **Step A3** | If database is empty: system inserts seed data — 5 CatalogBrands (DATA-ENT-002), 4 CatalogTypes (DATA-ENT-003), 12 CatalogItems (DATA-ENT-001). Entity IDs assigned via HiLo sequences. | System | BIZ-RULE-031 |
| **Step A4** | Seeding complete; CatalogContextSeed.SeedAsync() returns; startup continues. | System | — |

**Sub-process B — Identity Seeding (AppIdentityDbContextSeed):**

| Step | Description | Actor/System | Rules Applied |
|------|-------------|-------------|--------------|
| **Step B1** | AppIdentityDbContextSeed.SeedAsync() is called. | BIZ-ACT-006 | — |
| **Step B2** | **[BIZ-RULE-037 — BUG]** System calls RoleManager.CreateAsync("Administrators") WITHOUT checking if the role already exists. On a second startup: duplicate role creation attempt → logged error, but startup continues. | System | BIZ-RULE-037 |
| **Step B3** | System checks if demouser@microsoft.com and admin@microsoft.com accounts exist. Creates them if absent. **[BIZ-RULE-029, BIZ-RULE-013]** Passwords are hardcoded constants: `Pass@word1` sourced from AuthorizationConstants.cs:8. Both constants carry explicit TODO comments in source code warning they must not be used in production. | System | BIZ-RULE-013, BIZ-RULE-029 |
| **Step B4** | admin@microsoft.com is assigned to the Administrators role. Identity seeding complete; startup continues. | System | — |

**Postconditions:**
- CatalogDatabase: 5 brands, 4 types, 12 products (or pre-existing data if skipped)
- IdentityDatabase: demouser@microsoft.com, admin@microsoft.com with roles
- Idempotency: catalogue seeding is safe to re-run (BIZ-RULE-031); identity seeding has a role duplication bug (BIZ-RULE-037)

**Process pain points:**
- BIZ-RULE-029, BIZ-RULE-013: Hardcoded plaintext passwords in source code. Anyone with repository access can authenticate as admin (AO-03 blocker).
- BIZ-RULE-037: Identity seeding is not idempotent for role creation — duplicate role error on every restart after first (AO-09 — low effort fix).
- No retry logic in identity seeding (only catalogue seeding has BIZ-RULE-036 retry).

---

## 4. Process Interaction Map

```
STARTUP (BIZ-PROC-007)
    |
    +-- CatalogContextSeed --> DATA-REPO-001 (CatalogDatabase)
    +-- AppIdentityDbContextSeed --> DATA-REPO-002 (IdentityDatabase)

                SHOPPER JOURNEY
                ================
[BIZ-ACT-001/002] --> BIZ-PROC-003 (Add to Basket)
                           |
                           +-- reads CatalogItem.Price (Catalog -> Basket price lock)
                           +-- writes BasketItem (DATA-REPO-001)

[BIZ-ACT-001] --> BIZ-PROC-006 (Registration)
                           |
                           +-- creates ApplicationUser (DATA-REPO-002)
                           
[BIZ-ACT-001 -> BIZ-ACT-002] --> BIZ-PROC-004 (Basket Transfer)
                           |
                           TRIGGERED BY: BIZ-PROC-006 Web login only
                           +-- reads/merges Basket (DATA-REPO-001)
                           +-- [NOT triggered by API login]

[BIZ-ACT-002] --> BIZ-PROC-001 (Checkout)
                           |
                           +-- REQUIRES: authenticated shopper (BIZ-PROC-006)
                           +-- CONSUMES: Basket (DATA-REPO-001) -- deleted on completion
                           +-- CREATES: Order + OrderItems (DATA-REPO-001)
                           +-- SNAPSHOTS: CatalogItemOrdered from Catalog data

[BIZ-ACT-002] --> BIZ-PROC-002 (Order History/Detail)
                           |
                           +-- reads Orders filtered by BuyerId (BIZ-RULE-030)

                ADMIN JOURNEY
                ==============
[BIZ-ACT-003] --> BIZ-PROC-006 (API Authentication)
                           |
                           +-- POST /api/authenticate --> JWT issued (IdentityDatabase)

[BIZ-ACT-003] --> BIZ-PROC-005 (Catalogue Management)
                           |
                           REQUIRES: BIZ-PROC-006 JWT with Administrators role
                           +-- reads/writes CatalogItems (DATA-REPO-001)
                           +-- write-through cache invalidation (localStorage)
                           +-- [Web MVC IMemoryCache NOT invalidated -- 30s staleness]
```

---

## 5. Cross-Process Data Flows

### 5.1 Catalog → Basket (Price Lock)

**Flow:** BIZ-PROC-003 Step 3  
**Source entity:** DATA-ENT-001 (CatalogItem.Price)  
**Destination entity:** DATA-ENT-005 (BasketItem.UnitPrice)  
**Mechanism:** BasketService reads CatalogItem.Price at add-time and stores it in BasketItem.UnitPrice  
**Persistence:** CatalogDatabase.BasketItems  
**Immutability:** UnitPrice in BasketItem does NOT update if catalogue price changes later  
**Implication for checkout:** OrderItem.UnitPrice will reflect the add-time basket price, not the current catalogue price

### 5.2 Basket → Order (Checkout Handoff)

**Flow:** BIZ-PROC-001 Steps 4-6  
**Trigger:** BIZ-PROC-001 Step 4 — OrderService.CreateOrderAsync()  
**Source aggregate:** DATA-AGG-001 (BasketAggregate) — read then deleted  
**Destination aggregate:** DATA-AGG-002 (OrderAggregate) — created  
**Snapshot pattern (BIZ-RULE-001):** Each basket item generates a CatalogItemOrdered (DATA-ENT-012) with ProductName and PictureUri captured at checkout time  
**Immutability:** OrderAggregate is immutable after creation (BIZ-RULE-012)  
**Cross-DB reference:** Order.BuyerId references IdentityDatabase.AspNetUsers.Id by string value convention — no DB FK (BIZ-RULE-011)

### 5.3 Identity → Basket (Login Event)

**Flow:** BIZ-PROC-004  
**Trigger:** Web MVC login (POST /account/login) — NOT API login  
**Source:** Anonymous GUID from basket cookie (DATA-ENT-004.BuyerId = GUID)  
**Destination:** Authenticated user basket (DATA-ENT-004.BuyerId = username)  
**Key constraint:** Only the Web login path triggers this; API JWT login (BIZ-PROC-006) does not

### 5.4 Identity → Order (Buyer Reference)

**Flow:** BIZ-PROC-001 Step 4  
**Mechanism:** Order.BuyerId is set to the authenticated user's identity string at checkout  
**Cross-DB soft reference:** Order.BuyerId → IdentityDatabase.AspNetUsers.Id (application code only — no FK)  
**Risk:** Orphaned order-to-user references if user is deleted from IdentityDatabase; no cascade behaviour

---

## 6. Pain Points and Production Readiness Assessment

### 6.1 Critical Process Blockers

| Process | Pain Point | BIZ-RULE | Roadmap |
|---------|-----------|----------|---------|
| BIZ-PROC-001 | Hardcoded shipping address — cannot ship to actual buyer address | BIZ-RULE-015 | AO-01 |
| BIZ-PROC-001 | Email order confirmation non-functional — no post-checkout notification | BIZ-RULE-008 | AO-02 |
| BIZ-PROC-001 | No payment processing — BuyerAggregate dormant | BIZ-RULE-035 | AO-05 |
| BIZ-PROC-001 | No order status lifecycle — orders frozen in "placed" state forever | BIZ-RULE-012 | AO-06 |
| BIZ-PROC-003 | 1-second artificial delay on every browse request | BIZ-RULE-009 | AO-04 |
| BIZ-PROC-005 | Admin catalogue management API authentication uses hardcoded JWT key | BIZ-RULE-032 | AO-03 |
| BIZ-PROC-006 | No email confirmation on registration — unverified accounts immediately active | BIZ-RULE-027 | AO-02 + AO-08 |
| BIZ-PROC-007 | Seeded account passwords hardcoded in source — anyone with repo access can authenticate as admin | BIZ-RULE-029, BIZ-RULE-013 | AO-03 |

### 6.2 Architecture Process Blockers

| Process | Pain Point | Evidence |
|---------|-----------|----------|
| BIZ-PROC-005 | PublicApi endpoints call EfRepository directly — 6 ARCH-VIOLs bypass domain service abstraction | ARCH-VIOL-001..007 |
| BIZ-PROC-001, BIZ-PROC-003 | Shared CatalogContext persists Catalog, Basket, and Order in one DbContext | DATA-REPO-001; ARCH-VIOL-008 |
| BIZ-PROC-004 | API login does not trigger basket transfer — creates asymmetric behaviour between Web and API authentication paths | BIZ-RULE-002 |
| BIZ-PROC-005 | Cross-cache staleness: admin writes update localStorage but leave Web MVC IMemoryCache stale for up to 30s | CACHE-001; CACHE-002 |

---

*Business Process Model — generated from ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline Foundation Layer).*
*All 7 BIZ-PROC nodes (BIZ-PROC-001..007) are fully specified.*
*Three value streams documented: VS-001 Shopper Purchase Journey, VS-002 Catalogue Lifecycle, VS-003 New User Onboarding.*
*Every step traces to source file evidence and business rule node IDs.*
