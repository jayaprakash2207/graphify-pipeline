# Use Case Specification

**System:** eShopOnWeb
**Source of truth:** ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline/sample-output/foundation/)
**Generated:** 2026-06-30
**Pipeline stage:** Forward Engineering — Document 03 of 20
**Confidence schema:** HIGH = direct code evidence confirmed; MEDIUM = inferred from structure; LOW = assumed from convention

> Use cases are derived from the 31 capabilities (BIZ-CAP-001..031), 7 processes (BIZ-PROC-001..007), and 6 actors (BIZ-ACT-001..006). Every flow step traces to graph node IDs, business rules (BIZ-RULE-001..037), entities (DATA-ENT-###), and services (APP-SVC-###). No actor, flow, rule, or system behaviour outside the graph is invented.

---

## 1. Actors

| Actor ID | Name | Type | Role in Use Cases | Authentication |
|----------|------|------|-------------------|---------------|
| **BIZ-ACT-001** | Guest Shopper (Anonymous) | Human | Browses catalogue, adds to basket. Cannot check out. | GUID cookie (10-year, essential, BIZ-RULE-016) |
| **BIZ-ACT-002** | Registered Shopper | Human | All of BIZ-ACT-001 plus checkout, order history, registration. | ASP.NET Core Identity cookie (Web) or JWT (API) |
| **BIZ-ACT-003** | Product Administrator | Human | Back-office product catalogue management via BlazorAdmin SPA. | JWT token — Administrators role (BIZ-RULE-005, BIZ-RULE-007) |
| **BIZ-ACT-004** | Demo Shopper (demouser@microsoft.com) | Human (Seeded) | Same as BIZ-ACT-002; seeded account for demo purposes only. | BIZ-RULE-029 — hardcoded password; do not use in production |
| **BIZ-ACT-005** | Seeded Administrator (admin@microsoft.com) | Human (Seeded) | Same as BIZ-ACT-003; seeded admin account. | BIZ-RULE-013 — hardcoded password; do not use in production |
| **BIZ-ACT-006** | Application Startup (System) | System | Performs database seeding on startup (BIZ-RULE-036, BIZ-RULE-037). | Internal process — no authentication |

---

## 2. Business Rules Reference

| Rule ID | Summary | Domain | Severity |
|---------|---------|--------|---------|
| BIZ-RULE-001 | Order snapshots product name, picture, catalogue ID at purchase time | Order | High |
| BIZ-RULE-002 | Login merges anonymous basket into user basket; anonymous basket deleted | Basket | High |
| BIZ-RULE-003 | Order requires non-empty basket; basket deleted after order saved | Order | High |
| BIZ-RULE-004 | Basket add without quantity defaults to 1 | Basket | Low |
| BIZ-RULE-005 | Only ADMINISTRATORS role may create/update/delete catalogue products | Catalog | High |
| BIZ-RULE-006 | Anonymous shoppers may add to basket; only authenticated may checkout | Basket | High |
| BIZ-RULE-007 | JWT tokens carry user name and all roles as claims | Identity | High |
| BIZ-RULE-008 | Email notification entirely non-functional stub | Infrastructure | Critical |
| BIZ-RULE-009 | 1-second artificial delay on every catalogue browse | Catalog | Critical |
| BIZ-RULE-010 | Admin panel localStorage cache 1-min TTL; write immediately clears | Catalog | Medium |
| BIZ-RULE-011 | Order.BuyerId matches buyer by string convention — no DB FK | Order | Medium |
| BIZ-RULE-012 | Orders are immutable — no status field, cannot update/cancel | Order | Medium |
| BIZ-RULE-014 | Guard clauses enforce domain invariants at object creation | Application | High |
| BIZ-RULE-015 | All orders record hardcoded address (123 Main St., Kent, OH) | Order | Critical |
| BIZ-RULE-016 | Anonymous shopper GUID cookie is 10-year and essential | Basket | High |
| BIZ-RULE-017 | Basket transfer only if cookie value is valid GUID | Basket | Medium |
| BIZ-RULE-018 | Checkout requires authentication | Order | High |
| BIZ-RULE-019 | Basket must have at least one item for checkout | Order | High |
| BIZ-RULE-020 | Catalogue product names must be unique | Catalog | High |
| BIZ-RULE-021 | Catalogue product price must be > 0 | Catalog | High |
| BIZ-RULE-022 | Product name and description must not be empty | Catalog | High |
| BIZ-RULE-023 | New products get default placeholder image; admin upload disabled | Catalog | Medium |
| BIZ-RULE-024 | JWT tokens expire 7 days after issue | Identity | Medium |
| BIZ-RULE-025 | Account lockout on repeated failed password attempts | Identity | High |
| BIZ-RULE-026 | Checkout updates basket quantities before order is created | Basket | Medium |
| BIZ-RULE-027 | No email confirmation required — account activated immediately | Identity | Critical |
| BIZ-RULE-028 | Registration: email + 6-100 char password + matching confirmation | Identity | High |
| BIZ-RULE-029 | Seeded account passwords hardcoded — do not use in production | Identity | Critical |
| BIZ-RULE-030 | Shoppers can only view own orders — cross-account returns not-found | Order | High |
| BIZ-RULE-031 | Seed: 5 brands, 4 types, 12 products; skipped if data already exists | Catalog | Low |
| BIZ-RULE-032 | JWT signing key hardcoded in source — do not use in production | Identity | Critical |
| BIZ-RULE-033 | Shipping address DB max lengths enforced (postcode 18, street 180, etc.) | Order | Medium |
| BIZ-RULE-034 | Payment method must only store PCI-compliant token, alias, last 4 digits | Buyer | Critical |
| BIZ-RULE-035 | Buyer aggregate and PaymentMethod entirely dormant | Buyer | Medium |
| BIZ-RULE-036 | Catalogue seeding retries 10 times before aborting startup | Infrastructure | Medium |
| BIZ-RULE-037 | Identity seeding creates ADMINISTRATORS role without existence check | Infrastructure | Medium |

---

## 3. Use Case Index

| UC | Name | Actor(s) | Capability | Process |
|----|------|---------|-----------|---------|
| **UC-01** | Browse Product Catalogue | BIZ-ACT-001, BIZ-ACT-002 | BIZ-CAP-001, 006, 007 | BIZ-PROC-001 |
| **UC-02** | View Single Product | BIZ-ACT-001, BIZ-ACT-002 | BIZ-CAP-002 | BIZ-PROC-001 |
| **UC-03** | Add Item to Basket | BIZ-ACT-001, BIZ-ACT-002 | BIZ-CAP-010 | BIZ-PROC-003 |
| **UC-04** | Update Basket Item Quantity | BIZ-ACT-002 | BIZ-CAP-013 | BIZ-PROC-004 |
| **UC-05** | Transfer Anonymous Basket on Login | BIZ-ACT-001 → BIZ-ACT-002 | BIZ-CAP-012 | BIZ-PROC-004 |
| **UC-06** | Complete Checkout and Place Order | BIZ-ACT-002 | BIZ-CAP-017, 018 | BIZ-PROC-001, 002 |
| **UC-07** | View Order History | BIZ-ACT-002 | BIZ-CAP-019 | BIZ-PROC-002 |
| **UC-08** | View Order Detail | BIZ-ACT-002 | BIZ-CAP-020 | BIZ-PROC-002 |
| **UC-09** | Register New Account | BIZ-ACT-001 | BIZ-CAP-024 | BIZ-PROC-006 |
| **UC-10** | Login via Web (Cookie) | BIZ-ACT-002 | BIZ-CAP-021 | BIZ-PROC-006 |
| **UC-11** | Login via API (JWT) | BIZ-ACT-002, BIZ-ACT-003 | BIZ-CAP-022, 023 | BIZ-PROC-006 |
| **UC-12** | Admin: View Catalogue List | BIZ-ACT-003 | BIZ-CAP-008 | BIZ-PROC-005 |
| **UC-13** | Admin: Create Catalogue Product | BIZ-ACT-003 | BIZ-CAP-003 | BIZ-PROC-005 |
| **UC-14** | Admin: Update Catalogue Product | BIZ-ACT-003 | BIZ-CAP-004 | BIZ-PROC-005 |
| **UC-15** | Admin: Delete Catalogue Product | BIZ-ACT-003 | BIZ-CAP-005 | BIZ-PROC-005 |
| **UC-16** | System: Seed Catalogue on Startup | BIZ-ACT-006 | BIZ-CAP-009, 029 | BIZ-PROC-007 |
| **UC-17** | System: Seed Identity Data on Startup | BIZ-ACT-006 | BIZ-CAP-026, 029 | BIZ-PROC-007 |

---

## 4. Use Case Specifications

---

### UC-01 — Browse Product Catalogue

**ID:** UC-01  
**Name:** Browse Product Catalogue  
**Primary Actor:** BIZ-ACT-001 (Guest Shopper) or BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-001, BIZ-CAP-006, BIZ-CAP-007  
**Process:** BIZ-PROC-001  
**Backing API:** GET /api/catalog-items (APP-API-004), GET /api/catalog-brands (APP-API-002), GET /api/catalog-types (APP-API-008)

**Trigger:** Shopper navigates to the storefront homepage or catalogue page.

**Preconditions:**
- Catalogue database is seeded with at least one product (BIZ-RULE-031)
- No authentication required for browse
- Anonymous shopper has a 10-year GUID cookie assigned (BIZ-RULE-016)

**Main Flow:**
1. Shopper requests the catalogue page (no login required)
2. System assigns GUID cookie if not already present (BIZ-RULE-016)
3. System serves catalogue browse request to PublicApi → GET /api/catalog-items
4. **[KNOWN DEFECT BIZ-RULE-009]** PublicApi introduces mandatory 1-second artificial delay (`await Task.Delay(1000)`) before returning data
5. Web MVC checks ASP.NET Core IMemoryCache (CACHE-001, 30-second sliding TTL)
6. On cache hit: serve cached catalogue data; on cache miss: query CatalogDatabase.Catalog table
7. System returns paged list of CatalogItem records (DATA-ENT-001) with brand (DATA-ENT-002) and type (DATA-ENT-003) filters applied
8. Shopper views catalogue with product names, prices, images, and brand/type classification

**Postconditions:**
- Shopper sees paged product list (12 products in seed data)
- Catalogue data cached for up to 30 seconds in Web MVC server process

**Alternative Flows:**
- **AF-01: Filter by brand** — Shopper selects a brand from GET /api/catalog-brands list; system returns filtered CatalogItem records
- **AF-02: Filter by type** — Shopper selects a product type from GET /api/catalog-types list; system returns filtered results
- **AF-03: Pagination** — Shopper navigates to next page; system returns next page of CatalogItem records

**Exception Flows:**
- **EF-01: Database unavailable** — System returns error; catalogue seeding retry logic (BIZ-RULE-036) applies only at startup, not during browse
- **EF-02: No products in catalogue** — System returns empty list; no error

**Business Rules Applied:** BIZ-RULE-009 (defect), BIZ-RULE-016, BIZ-RULE-031

---

### UC-02 — View Single Product

**ID:** UC-02  
**Name:** View Single Product  
**Primary Actor:** BIZ-ACT-001 (Guest Shopper) or BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-002  
**Backing API:** GET /api/catalog-items/{catalogItemId} (APP-API-003)

**Trigger:** Shopper clicks on a specific product in the catalogue listing.

**Preconditions:**
- The requested CatalogItem exists in CatalogDatabase
- No authentication required

**Main Flow:**
1. Shopper selects a product; system submits GET /api/catalog-items/{catalogItemId}
2. PublicApi handler (CatalogItemGetByIdEndpoint) retrieves CatalogItem from CatalogDatabase via EfRepository
3. System returns product details: Name, Description, Price, PictureUri, CatalogTypeId, CatalogBrandId (DATA-ENT-001)
4. Shopper views full product details with "Add to Basket" option

**Exception Flows:**
- **EF-01: Product not found** — PublicApi returns 404 Not Found
- **EF-02: Catalogue item deleted since listing** — returns 404; shopper redirected to catalogue

**Business Rules Applied:** None specific to single product retrieval (ARCH-VIOL-002 — architectural note only)

---

### UC-03 — Add Item to Basket

**ID:** UC-03  
**Name:** Add Item to Basket  
**Primary Actor:** BIZ-ACT-001 (Guest Shopper) or BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-010, BIZ-CAP-016  
**Process:** BIZ-PROC-003  
**Backing Service:** APP-SVC-001 (BasketService)

**Trigger:** Shopper clicks "Add to Basket" on a product detail page.

**Preconditions:**
- Valid CatalogItem exists (DATA-ENT-001)
- For anonymous shopper: GUID cookie present (BIZ-RULE-016)
- For registered shopper: authenticated session

**Main Flow:**
1. Shopper selects a product and optionally specifies quantity
2. **[BIZ-RULE-004]** If no quantity specified, system defaults to quantity = 1
3. System identifies the shopper's basket by BuyerId (GUID for anonymous, username for authenticated)
4. **[Get or Create]** BIZ-CAP-016: if no basket exists for this BuyerId, system creates a new Basket record (DATA-ENT-004)
5. System reads CatalogItem.Price at this moment — price is **locked into BasketItem.UnitPrice** and will not update if the catalogue price changes later
6. **[BIZ-RULE auto-merge]** If the same CatalogItemId already exists as a BasketItem, system **increments quantity** on the existing line (not an exception — this is the confirmed behaviour)
7. If item is new to basket, system creates a new BasketItem record (DATA-ENT-005) with CatalogItemId, UnitPrice, Quantity
8. System persists the updated Basket aggregate (DATA-AGG-001) to CatalogDatabase.BasketItems

**Postconditions:**
- BasketItem exists in CatalogDatabase with price locked at add-time
- Basket item count updated (BIZ-CAP-014)

**Alternative Flows:**
- **AF-01: Duplicate item** — System auto-merges into existing line by incrementing quantity (confirmed — not an exception or error)

**Exception Flows:**
- **EF-01: CatalogItem not found** — System returns error; basket not modified
- **EF-02: Database failure** — Basket operation fails; no partial write

**Business Rules Applied:** BIZ-RULE-004, BIZ-RULE-016, BIZ-RULE-017

---

### UC-04 — Update Basket Item Quantity

**ID:** UC-04  
**Name:** Update Basket Item Quantity  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-013, BIZ-CAP-011  
**Process:** BIZ-PROC-004  
**Backing Service:** APP-SVC-001 (BasketService)

**Trigger:** Shopper updates item quantity on the basket page or at checkout.

**Preconditions:**
- Shopper has an authenticated session
- Basket contains at least one item

**Main Flow:**
1. Shopper submits updated quantity for one or more basket items
2. **[BIZ-RULE-026]** At checkout, the system updates basket item quantities before creating the order
3. For each BasketItem:
   - If new quantity > 0: system updates BasketItem.Quantity
   - If new quantity = 0: system removes the BasketItem record (line-item cleanup)
4. System persists updated Basket aggregate (DATA-AGG-001)

**Postconditions:**
- BasketItem quantities reflect shopper's updates
- Zero-quantity items are removed from basket

**Exception Flows:**
- **EF-01: Negative quantity submitted** — System rejects with validation error; basket unchanged (BIZ-RULE-014 guard clause)
- **EF-02: Basket item not found** — Update silently ignored or error returned

**Business Rules Applied:** BIZ-RULE-026

---

### UC-05 — Transfer Anonymous Basket on Login

**ID:** UC-05  
**Name:** Transfer Anonymous Basket on Login (Web Path)  
**Primary Actor:** BIZ-ACT-001 (Guest) transitioning to BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-012  
**Process:** BIZ-PROC-004  
**Backing Service:** APP-SVC-001 (BasketService.TransferBasketAsync)

**Trigger:** Anonymous shopper logs in via the Web MVC login page (POST /account/login). **Not triggered by API login.**

**Preconditions:**
- Shopper has a GUID cookie (BIZ-RULE-016) containing a basket with items
- Shopper provides valid credentials for an existing account

**Main Flow:**
1. Shopper submits login form on the Web MVC storefront
2. Login.cshtml.cs reads anonymous basket GUID from cookie
3. **[BIZ-RULE-017]** System validates the cookie value is a valid GUID format; if not valid, transfer is skipped
4. System calls BasketService.TransferBasketAsync(anonymousId, username)
5. System loads both the anonymous basket and the user's authenticated basket
6. For each item in the anonymous basket:
   - If the same CatalogItemId exists in the user's basket: increment quantity in the user's basket (original price preserved — NOT refreshed from catalogue)
   - If new item: add to user's basket
7. System deletes the anonymous basket and all its BasketItems permanently
8. ASP.NET Core Identity SignInManager completes the sign-in process
9. System deletes the anonymous basket cookie
10. Shopper is now authenticated with a merged basket

**Postconditions:**
- Anonymous basket is permanently deleted
- User's basket contains all items from both baskets
- UnitPrice values are NOT refreshed — prices from anonymous session are preserved

**[IMPORTANT ASYMMETRY — BIZ-ACT-003 note]**
- This entire flow occurs **only on Web MVC login**
- API login via POST /api/authenticate (BIZ-CAP-022) does NOT trigger basket transfer
- BlazorAdmin users authenticating via the API never have their anonymous basket merged

**Exception Flows:**
- **EF-01: Invalid GUID cookie** — Transfer skipped; login proceeds normally (BIZ-RULE-017)
- **EF-02: No anonymous basket found** — Transfer skipped; login proceeds normally
- **EF-03: Invalid credentials** — Login fails; basket transfer not attempted

**Business Rules Applied:** BIZ-RULE-002, BIZ-RULE-016, BIZ-RULE-017

---

### UC-06 — Complete Checkout and Place Order

**ID:** UC-06  
**Name:** Complete Checkout and Place Order  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-017, BIZ-CAP-018  
**Process:** BIZ-PROC-001, BIZ-PROC-002  
**Backing Service:** APP-SVC-004 (OrderService)

**Trigger:** Authenticated shopper proceeds to checkout from the basket page.

**Preconditions:**
- Shopper is authenticated (BIZ-RULE-018) — unauthenticated visitors are redirected to login
- Basket contains at least one item (BIZ-RULE-019)
- **[KNOWN GAP BIZ-RULE-015]** In the current system, a hardcoded shipping address is used — user is not prompted to enter one

**Main Flow:**
1. Shopper clicks "Checkout"; system enforces [Authorize] attribute (BIZ-RULE-018)
2. Checkout.cshtml.cs reads basket via BasketViewModelService (BIZ-CAP-015)
3. **[BIZ-RULE-026]** Shopper may update quantities in the checkout form; system calls BasketService.SetQuantities before proceeding
4. **[KNOWN GAP BIZ-RULE-015]** System constructs hardcoded shipping Address: "123 Main St., Kent, OH, United States, 44240" — this is a production-blocking gap
5. System calls OrderService.CreateOrderAsync(buyerId, hardcoded_address, basket.Items)
6. **[BIZ-RULE-019]** GuardExtensions.EmptyBasketOnCheckout validates basket is non-empty; if empty, throws exception and blocks order creation
7. For each basket item, system creates a CatalogItemOrdered snapshot (DATA-ENT-012):
   - ItemOrdered_CatalogItemId (reference to CatalogItem ID)
   - ItemOrdered_ProductName (captured now — BIZ-RULE-001)
   - ItemOrdered_PictureUri (captured now — BIZ-RULE-001)
   - UnitPrice (from BasketItem — already locked at add-time)
8. **[BIZ-RULE-011]** Order.BuyerId is set to the shopper's identity string; no database foreign key to IdentityDatabase
9. **[BIZ-RULE-001]** OrderItem records are persisted — immune to future catalogue changes
10. System saves Order and all OrderItems to CatalogDatabase.Orders and CatalogDatabase.OrderItems via EfRepository
11. **[BIZ-RULE-003]** System calls BasketService.DeleteBasketAsync — basket and all BasketItems are permanently deleted
12. System attempts to send order confirmation email via IEmailSender.SendEmailAsync
13. **[BIZ-RULE-008]** EmailSender.cs returns Task.CompletedTask immediately — no email delivered
14. System redirects shopper to order confirmation page

**Postconditions:**
- Order record persisted in CatalogDatabase with immutable product snapshots
- Basket and all BasketItems permanently deleted
- Order total = sum(OrderItem.UnitPrice × OrderItem.Units) per BIZ-CAP-018
- No email confirmation sent (BIZ-RULE-008 — production gap)

**Alternative Flows:**
- **AF-01: Shopper updates quantities at checkout** — BIZ-RULE-026 applies; quantities updated before order creation

**Exception Flows:**
- **EF-01: Empty basket** — BIZ-RULE-019 guard throws exception; shopper redirected with error message
- **EF-02: Not authenticated** — BIZ-RULE-018 redirects to login
- **EF-03: CatalogItem not found during snapshot** — Order creation fails; basket preserved

**Business Rules Applied:** BIZ-RULE-001, BIZ-RULE-003, BIZ-RULE-008 (defect), BIZ-RULE-011, BIZ-RULE-012, BIZ-RULE-014, BIZ-RULE-015 (gap), BIZ-RULE-018, BIZ-RULE-019, BIZ-RULE-026, BIZ-RULE-033

---

### UC-07 — View Order History

**ID:** UC-07  
**Name:** View Order History  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-019  
**Process:** BIZ-PROC-002  
**Backing Service:** APP-SVC-005 (GetMyOrdersHandler)

**Trigger:** Authenticated shopper navigates to "My Orders."

**Preconditions:**
- Shopper is authenticated

**Main Flow:**
1. Shopper accesses the My Orders page
2. System extracts BuyerId from the authenticated user's identity
3. **[BIZ-RULE-030]** System queries CatalogDatabase.Orders filtered by Order.BuyerId = current user's identity string
4. GetMyOrdersHandler retrieves all matching Order records (DATA-ENT-006) via MediatR
5. System returns list of orders with OrderDate and Order totals
6. Shopper views their own order history

**Postconditions:**
- Only the authenticated shopper's orders are displayed
- Other shoppers' orders are never exposed

**Exception Flows:**
- **EF-01: No orders found** — System returns empty list; no error
- **EF-02: Not authenticated** — Redirected to login

**Business Rules Applied:** BIZ-RULE-030

---

### UC-08 — View Order Detail

**ID:** UC-08  
**Name:** View Order Detail  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-020  
**Process:** BIZ-PROC-002  
**Backing Service:** APP-SVC-006 (GetOrderDetailsHandler)

**Trigger:** Authenticated shopper clicks on a specific order from their order history.

**Preconditions:**
- Shopper is authenticated
- Requested order belongs to the requesting shopper

**Main Flow:**
1. Shopper selects an order; system extracts Order.Id and current user's BuyerId
2. **[BIZ-RULE-030]** GetOrderDetailsHandler queries CatalogDatabase.Orders with Id AND BuyerId filter
3. System returns Order with all OrderItems, each containing the purchase-time CatalogItemOrdered snapshot:
   - ItemOrdered_ProductName (as recorded at purchase — BIZ-RULE-001)
   - ItemOrdered_PictureUri (as recorded at purchase — BIZ-RULE-001)
   - UnitPrice, Units
4. System calculates and displays Order.Total() = sum(UnitPrice × Units)
5. Shopper views complete order detail including shipping address, order date, and all line items

**Postconditions:**
- Product details shown are the purchase-time snapshot — unaffected by catalogue changes since purchase

**Exception Flows:**
- **EF-01: Order belongs to different shopper** — System returns not-found; no data exposed (BIZ-RULE-030)
- **EF-02: Order not found** — Returns not-found

**Business Rules Applied:** BIZ-RULE-001, BIZ-RULE-012, BIZ-RULE-030

---

### UC-09 — Register New Account

**ID:** UC-09  
**Name:** Register New Account  
**Primary Actor:** BIZ-ACT-001 (Guest Shopper)  
**Capabilities:** BIZ-CAP-024  
**Process:** BIZ-PROC-006  
**Backing Service:** Register.cshtml.cs

**Trigger:** Guest shopper navigates to the registration page and submits the registration form.

**Preconditions:**
- Shopper does not have an existing account with the same email

**Main Flow:**
1. Shopper submits the registration form with email, password, and password confirmation
2. **[BIZ-RULE-028]** System validates:
   - Email is a valid email format
   - Password is between 6 and 100 characters
   - Password and confirmation password match
3. System calls ASP.NET Core Identity UserManager.CreateAsync with new ApplicationUser (DATA-ENT-010)
4. **[BIZ-RULE-027 — CRITICAL GAP]** System does NOT require email confirmation — account is activated immediately upon creation. The email confirmation token is generated but discarded (Register.cshtml.cs:77-88).
5. **[BIZ-RULE-025]** Account lockout is enabled on the new account from creation
6. Shopper is signed in automatically and redirected to the homepage

**Postconditions:**
- New ApplicationUser record created in IdentityDatabase.AspNetUsers
- Account is immediately active — no email verification required (gap: BIZ-RULE-027)

**Exception Flows:**
- **EF-01: Email already registered** — ASP.NET Core Identity returns DuplicateEmail error; form shows error
- **EF-02: Password too short** (< 6 chars) — Validation error shown (note: NIST minimum is 8 — gap per NFR)
- **EF-03: Password mismatch** — Validation error shown; account not created

**Business Rules Applied:** BIZ-RULE-025, BIZ-RULE-027 (critical gap), BIZ-RULE-028

---

### UC-10 — Login via Web (Cookie Authentication)

**ID:** UC-10  
**Name:** Login via Web Storefront (Cookie)  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper)  
**Capabilities:** BIZ-CAP-021  
**Process:** BIZ-PROC-006  
**Backing Service:** ASP.NET Core Identity SignInManager

**Trigger:** Shopper navigates to the login page and submits credentials.

**Preconditions:**
- Account exists in IdentityDatabase
- Account is not locked out

**Main Flow:**
1. Shopper submits email and password via the Web MVC login form
2. **[BIZ-RULE-025]** System checks account lockout status; if locked, returns lockout error
3. System calls SignInManager.PasswordSignInAsync with lockoutOnFailure = true
4. On successful authentication: ASP.NET Core Identity issues an authentication cookie
5. **[BIZ-RULE-002]** System reads the anonymous basket GUID cookie and calls BasketService.TransferBasketAsync if the GUID is valid (BIZ-RULE-017)
6. Anonymous basket is merged into the user's basket and deleted (see UC-05 for full transfer flow)
7. Anonymous basket cookie is deleted
8. Shopper is redirected to the originally requested page or homepage

**Postconditions:**
- Shopper is authenticated with an ASP.NET Core Identity cookie
- Anonymous basket (if valid) has been transferred to the user's basket

**Exception Flows:**
- **EF-01: Invalid credentials** — SignInManager returns Failed; failed attempt count incremented (BIZ-RULE-025)
- **EF-02: Account locked out** — SignInManager returns LockedOut; lockout message shown
- **EF-03: Account not allowed** — SignInManager returns NotAllowed; appropriate message shown

**Business Rules Applied:** BIZ-RULE-002, BIZ-RULE-016, BIZ-RULE-017, BIZ-RULE-025

---

### UC-11 — Login via API (JWT Authentication)

**ID:** UC-11  
**Name:** Login via API / Obtain JWT Token  
**Primary Actor:** BIZ-ACT-002 (Registered Shopper) or BIZ-ACT-003 (Product Administrator)  
**Capabilities:** BIZ-CAP-022, BIZ-CAP-023  
**Process:** BIZ-PROC-006  
**Backing API:** POST /api/authenticate (APP-API-001)  
**Backing Service:** APP-SVC-007 (IdentityTokenClaimService)

**Trigger:** Client application (typically BlazorAdmin SPA) submits login credentials to the API.

**Preconditions:**
- Account exists in IdentityDatabase
- Account is not locked out

**Main Flow:**
1. Client submits HTTP POST /api/authenticate with username and password (JSON body)
2. **[BIZ-RULE-025]** AuthenticateEndpoint.cs:44 checks lockout with lockoutOnFailure = false
3. System calls UserManager.CheckPasswordAsync to validate credentials
4. On success: system retrieves all roles and claims for the user via IdentityTokenClaimService
5. **[BIZ-RULE-007]** System generates a JWT token embedding: user name, all assigned roles as claims
6. **[BIZ-RULE-024]** JWT token has a 7-day expiry (DateTime.UtcNow.AddDays(7))
7. **[BIZ-RULE-032 — CRITICAL GAP]** JWT is signed with a hardcoded key from AuthorizationConstants.cs:12. Anyone with repository access can forge valid tokens.
8. System returns the JWT token to the client in the response body
9. **[IMPORTANT — BIZ-RULE-002 does NOT apply]** API login does NOT trigger anonymous basket transfer

**Postconditions:**
- Client holds a 7-day JWT token
- Token is stored in browser localStorage by BlazorAdmin (XSS-accessible risk)
- No basket transfer occurs

**Exception Flows:**
- **EF-01: Invalid credentials** — AuthenticateEndpoint returns 401 Unauthorized; lockout check applied but lockoutOnFailure=false means no increment on API path
- **EF-02: Account locked** — Lockout status checked; appropriate error returned
- **EF-03: User not found** — Returns 401 Unauthorized

**Business Rules Applied:** BIZ-RULE-007, BIZ-RULE-024, BIZ-RULE-025, BIZ-RULE-032 (critical gap)

---

### UC-12 — Admin: View Catalogue List (BlazorAdmin)

**ID:** UC-12  
**Name:** Admin: View Catalogue List  
**Primary Actor:** BIZ-ACT-003 (Product Administrator)  
**Capabilities:** BIZ-CAP-008, BIZ-CAP-001, BIZ-CAP-006, BIZ-CAP-007  
**Process:** BIZ-PROC-005  
**Backing Service:** APP-SVC-009 (CachedCatalogItemServiceDecorator)

**Trigger:** Admin navigates to the BlazorAdmin catalogue management panel.

**Preconditions:**
- Admin is authenticated with a valid JWT token (BIZ-RULE-007)
- JWT token carries Administrators role claim (BIZ-RULE-005)

**Main Flow:**
1. Admin navigates to the catalogue list in BlazorAdmin SPA
2. **[BIZ-RULE-010]** CachedCatalogItemServiceDecorator checks Blazored.LocalStorage for cached catalogue list
3. **Cache HIT (< 1 minute old):** system returns cached data from localStorage
4. **Cache MISS or expired:** system sends HTTP GET /api/catalog-items to PublicApi
5. **[BIZ-RULE-009]** PublicApi introduces 1-second artificial delay
6. PublicApi returns catalogue items from CatalogDatabase
7. CachedCatalogItemServiceDecorator stores result in localStorage with DateCreated timestamp
8. Admin views catalogue list with product names, prices, brands, and types
9. Brand and type dropdowns populated from GET /api/catalog-brands and GET /api/catalog-types (no caching for these — TTL only)

**Postconditions:**
- Admin sees catalogue list (from cache or live data)
- Cache timestamp updated on cache miss

**Business Rules Applied:** BIZ-RULE-005, BIZ-RULE-007, BIZ-RULE-009 (defect), BIZ-RULE-010

---

### UC-13 — Admin: Create Catalogue Product

**ID:** UC-13  
**Name:** Admin: Create Catalogue Product  
**Primary Actor:** BIZ-ACT-003 (Product Administrator)  
**Capabilities:** BIZ-CAP-003  
**Process:** BIZ-PROC-005  
**Backing API:** POST /api/catalog-items (APP-API-005)  
**Backing Service:** APP-SVC-008 (EfRepository via CreateCatalogItemEndpoint)

**Trigger:** Admin fills in the product creation form in BlazorAdmin and submits.

**Preconditions:**
- Admin is authenticated with JWT token carrying Administrators role
- Product name is unique (BIZ-RULE-020)

**Main Flow:**
1. Admin fills in: product name, description, price, brand ID, type ID
2. BlazorAdmin sends HTTP POST /api/catalog-items with JWT Bearer token
3. **[BIZ-RULE-005]** PublicApi endpoint enforces [Authorize(Roles = "ADMINISTRATORS")]; returns 401/403 if missing
4. **[BIZ-RULE-020]** CreateCatalogItemEndpoint.cs:43-47 checks for duplicate product name; if name exists, returns error
5. **[BIZ-RULE-021]** Guard.Against.NegativeOrZero validates price > 0 (BIZ-RULE-014 guard pattern)
6. **[BIZ-RULE-022]** Guard.Against.NullOrEmpty validates name and description are non-empty
7. **[BIZ-RULE-023]** System assigns default placeholder image URI — admin cannot upload a custom image (image upload is permanently disabled)
8. System creates new CatalogItem record (DATA-ENT-001) in CatalogDatabase.Catalog table via EfRepository
9. System returns the created CatalogItem with the assigned ID (HiLo sequence — DATA-REPO-001)
10. **[BIZ-RULE-010]** CachedCatalogItemServiceDecorator.RefreshLocalStorageList() clears and reloads the item cache in localStorage (write-through invalidation)
11. **[CACHE STALENESS NOTE]** Web MVC IMemoryCache (CACHE-001, 30s TTL) is NOT invalidated — storefront may show the old catalogue for up to 30 seconds

**Postconditions:**
- New CatalogItem persisted in CatalogDatabase
- BlazorAdmin localStorage cache immediately reflects new product
- Web MVC storefront may show stale data for up to 30 seconds

**Exception Flows:**
- **EF-01: Duplicate product name** — Returns 409 Conflict or error; product not created (BIZ-RULE-020)
- **EF-02: Price ≤ 0** — Guard clause throws; returns validation error (BIZ-RULE-021)
- **EF-03: Empty name or description** — Guard clause throws; returns validation error (BIZ-RULE-022)
- **EF-04: Missing or invalid JWT** — Returns 401 Unauthorized (BIZ-RULE-005)
- **EF-05: Missing Administrators role** — Returns 403 Forbidden (BIZ-RULE-005)

**Business Rules Applied:** BIZ-RULE-005, BIZ-RULE-010, BIZ-RULE-014, BIZ-RULE-020, BIZ-RULE-021, BIZ-RULE-022, BIZ-RULE-023

---

### UC-14 — Admin: Update Catalogue Product

**ID:** UC-14  
**Name:** Admin: Update Catalogue Product  
**Primary Actor:** BIZ-ACT-003 (Product Administrator)  
**Capabilities:** BIZ-CAP-004  
**Backing API:** PUT /api/catalog-items (APP-API-007)

**Trigger:** Admin edits an existing product's details in BlazorAdmin and saves.

**Preconditions:**
- Admin is authenticated with JWT token carrying Administrators role
- CatalogItem to update exists in CatalogDatabase

**Main Flow:**
1. Admin edits product fields (name, description, price, brand, type) in BlazorAdmin
2. BlazorAdmin sends HTTP PUT /api/catalog-items with updated product data and JWT Bearer token
3. **[BIZ-RULE-005]** Endpoint enforces [Authorize(Roles = "ADMINISTRATORS")]
4. **[BIZ-RULE-022]** Guard validates name and description are non-empty
5. **[BIZ-RULE-021]** Guard validates price > 0
6. System updates the CatalogItem record (DATA-ENT-001) in CatalogDatabase via EfRepository
7. **[BIZ-RULE-010]** CachedCatalogItemServiceDecorator.RefreshLocalStorageList() refreshes localStorage cache (write-through)
8. **[BIZ-RULE-001]** Any existing Orders with OrderItems referencing this product retain their original purchase-time snapshot — update does NOT affect historical orders
9. **[CACHE STALENESS]** Web MVC IMemoryCache not invalidated — 30s stale window on storefront

**Postconditions:**
- CatalogItem record updated in CatalogDatabase
- BlazorAdmin cache immediately reflects change
- Existing order history unaffected (BIZ-RULE-001 snapshot protection)

**Exception Flows:** Same as UC-13 EF-02..EF-05.

**Business Rules Applied:** BIZ-RULE-001, BIZ-RULE-005, BIZ-RULE-010, BIZ-RULE-014, BIZ-RULE-021, BIZ-RULE-022

---

### UC-15 — Admin: Delete Catalogue Product

**ID:** UC-15  
**Name:** Admin: Delete Catalogue Product  
**Primary Actor:** BIZ-ACT-003 (Product Administrator)  
**Capabilities:** BIZ-CAP-005  
**Backing API:** DELETE /api/catalog-items/{catalogItemId} (APP-API-006)

**Trigger:** Admin selects a product in BlazorAdmin and confirms deletion.

**Preconditions:**
- Admin is authenticated with JWT token carrying Administrators role
- CatalogItem exists in CatalogDatabase

**Main Flow:**
1. Admin confirms deletion of a catalogue item
2. BlazorAdmin sends HTTP DELETE /api/catalog-items/{catalogItemId} with JWT Bearer token
3. **[BIZ-RULE-005]** Endpoint enforces [Authorize(Roles = "ADMINISTRATORS")]
4. System deletes the CatalogItem record (DATA-ENT-001) from CatalogDatabase.Catalog
5. **[BIZ-RULE-001]** Existing OrderItems referencing this product retain their snapshot (ItemOrdered_ProductName, ItemOrdered_PictureUri) — deletion does not corrupt historical order records
6. **[ORPHAN RISK]** BasketItems referencing this CatalogItemId via soft reference (no DB FK) become orphaned; no automatic cleanup triggered
7. **[BIZ-RULE-010]** Write-through cache invalidation: CachedCatalogItemServiceDecorator refreshes localStorage
8. **[CACHE STALENESS]** Web MVC IMemoryCache not invalidated — deleted product may appear for up to 30s on storefront

**Postconditions:**
- CatalogItem deleted from CatalogDatabase
- Existing order snapshots intact (BIZ-RULE-001)
- BlazorAdmin cache immediately updated
- Orphaned BasketItems may exist

**Exception Flows:**
- **EF-01: Product not found** — Returns 404 Not Found
- **EF-02: Missing Administrators role** — Returns 403 Forbidden (BIZ-RULE-005)

**Business Rules Applied:** BIZ-RULE-001, BIZ-RULE-005, BIZ-RULE-010

---

### UC-16 — System: Seed Catalogue on Startup

**ID:** UC-16  
**Name:** System Seed Catalogue Database on Startup  
**Primary Actor:** BIZ-ACT-006 (Application Startup Process)  
**Capabilities:** BIZ-CAP-009, BIZ-CAP-029  
**Process:** BIZ-PROC-007  
**Backing Service:** APP-SVC-010 (CatalogContextSeed)

**Trigger:** Application starts up (CatalogContextSeed.SeedAsync called from startup).

**Preconditions:**
- CatalogDatabase connection is available (DATA-REPO-001, CatalogConnection string)

**Main Flow:**
1. Application startup calls CatalogContextSeed.SeedAsync
2. **[BIZ-RULE-036]** System attempts database connection with retry logic — up to 10 retries on failure; aborts startup after 10 failed attempts
3. **[BIZ-RULE-031]** System checks if any catalogue data already exists; if data is present, seeding is skipped entirely
4. If database is empty: system inserts seed data:
   - 5 catalogue brands into CatalogDatabase.CatalogBrands (DATA-ENT-002)
   - 4 catalogue types into CatalogDatabase.CatalogTypes (DATA-ENT-003)
   - 12 catalogue products into CatalogDatabase.Catalog (DATA-ENT-001)
5. Entity IDs assigned via HiLo sequences (catalog_hilo, catalog_brand_hilo, catalog_type_hilo)
6. Seeding complete; application startup continues

**Postconditions:**
- CatalogDatabase contains 5 brands, 4 types, 12 products (or pre-existing data if skipped)

**Exception Flows:**
- **EF-01: Database unavailable for 10 attempts** — Application startup aborts (BIZ-RULE-036)

**Business Rules Applied:** BIZ-RULE-031, BIZ-RULE-036

---

### UC-17 — System: Seed Identity Data on Startup

**ID:** UC-17  
**Name:** System Seed Identity Database on Startup  
**Primary Actor:** BIZ-ACT-006 (Application Startup Process)  
**Capabilities:** BIZ-CAP-026, BIZ-CAP-029  
**Process:** BIZ-PROC-007  
**Backing Service:** APP-SVC-011 (AppIdentityDbContextSeed)

**Trigger:** Application starts up (AppIdentityDbContextSeed called from startup).

**Preconditions:**
- IdentityDatabase connection is available (DATA-REPO-002, IdentityConnection string)

**Main Flow:**
1. Application startup calls AppIdentityDbContextSeed.SeedAsync
2. **[BIZ-RULE-037 — BUG]** System attempts to create the "Administrators" role via RoleManager.CreateAsync WITHOUT first checking if the role already exists. On a restart, this produces a duplicate role creation attempt and an error in the logs.
3. System creates seeded user accounts if they do not exist:
   - demouser@microsoft.com (BIZ-ACT-004) with hardcoded password `Pass@word1`
   - admin@microsoft.com with Administrators role (BIZ-ACT-005) with hardcoded password `Pass@word1`
4. **[BIZ-RULE-029, BIZ-RULE-013]** Both accounts have hardcoded plaintext passwords with explicit TODO comments in AuthorizationConstants.cs:8 warning against production use

**Postconditions:**
- IdentityDatabase contains at least two seeded accounts and one role
- Role creation may log an error on restart (BIZ-RULE-037 idempotency bug)

**Exception Flows:**
- **EF-01: Duplicate role creation on restart** — Logs an error but startup continues (BIZ-RULE-037)

**Business Rules Applied:** BIZ-RULE-013, BIZ-RULE-029, BIZ-RULE-037

---

## 5. Capability Coverage Summary

| Capability | UC Coverage | UC ID(s) |
|-----------|------------|---------|
| BIZ-CAP-001 Paged Browse | Full | UC-01, UC-12 |
| BIZ-CAP-002 Single Product | Full | UC-02 |
| BIZ-CAP-003 Admin Create | Full | UC-13 |
| BIZ-CAP-004 Admin Update | Full | UC-14 |
| BIZ-CAP-005 Admin Delete | Full | UC-15 |
| BIZ-CAP-006 Brand List | Full | UC-01 |
| BIZ-CAP-007 Type List | Full | UC-01 |
| BIZ-CAP-008 Admin Browser Cache | Full | UC-12, UC-13, UC-14, UC-15 |
| BIZ-CAP-009 Catalogue Seeding | Full | UC-16 |
| BIZ-CAP-010 Item Addition | Full | UC-03 |
| BIZ-CAP-011 Basket Deletion | Covered in | UC-05, UC-06 |
| BIZ-CAP-012 Anon Transfer | Full | UC-05 |
| BIZ-CAP-013 Quantity Update | Full | UC-04 |
| BIZ-CAP-014 Item Count Query | Supporting | UC-03 |
| BIZ-CAP-015 Basket View | Supporting | UC-06 |
| BIZ-CAP-016 Get or Create Basket | Supporting | UC-03 |
| BIZ-CAP-017 Order Creation | Full | UC-06 |
| BIZ-CAP-018 Order Total Calculation | Full | UC-06, UC-08 |
| BIZ-CAP-019 Order History | Full | UC-07 |
| BIZ-CAP-020 Order Detail | Full | UC-08 |
| BIZ-CAP-021 Web Auth (Cookie) | Full | UC-10 |
| BIZ-CAP-022 API Auth (JWT) | Full | UC-11 |
| BIZ-CAP-023 JWT Token Generation | Full | UC-11 |
| BIZ-CAP-024 User Registration | Full | UC-09 |
| BIZ-CAP-025 BlazorAdmin Auth State | Supporting | UC-11, UC-12 |
| BIZ-CAP-026 Identity & Role Seeding | Full | UC-17 |
| BIZ-CAP-027 Email Notification (Stub) | Noted in | UC-06 (gap) |
| BIZ-CAP-028 Generic Repository | Underlying | All UC via EfRepository |
| BIZ-CAP-029 DB Seed on Startup | Full | UC-16, UC-17 |
| BIZ-CAP-030 Buyer Structure | DORMANT | — |
| BIZ-CAP-031 Payment Method | DORMANT | — |

---

*Use Case Specification — generated from ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*17 use cases covering all 31 capabilities (2 dormant capabilities noted but not specified).*
*Every flow step traces to a BIZ-RULE, APP-SVC, or DATA-ENT node ID.*
