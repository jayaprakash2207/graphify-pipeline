# Domain Model (Domain-Driven Design)

**System:** eShopOnWeb
**Source of truth:** ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline/sample-output/foundation/)
**Generated:** 2026-06-30
**Pipeline stage:** Forward Engineering — Document 05 of 20
**Confidence schema:** HIGH = direct code evidence confirmed; MEDIUM = inferred from structure; LOW = assumed from convention

> Every entity, aggregate, repository, relationship, and ubiquitous language term below traces to node IDs in ENTERPRISE_KNOWLEDGE_GRAPH.json. All 13 data entities (DATA-ENT-001..013), 4 DDD aggregates (DATA-AGG-001..004), and 2 repositories (DATA-REPO-001..002) are covered.
>
> **Status discipline:** DATA-ENT-008 (Buyer) and DATA-ENT-009 (PaymentMethod) are DORMANT — structurally defined in ApplicationCore but confirmed dead (no DbSet in CatalogContext; no service layer). DATA-AGG-003 (BuyerAggregate) is likewise DORMANT. BIZ-RULE-035 confirms this at HIGH confidence. Do not generate persistence for these without an explicit activation decision.
>
> **Snapshot pattern note:** DATA-ENT-011 (Address) and DATA-ENT-012 (CatalogItemOrdered) are value objects inlined into their parent tables (Orders and OrderItems respectively) — they are not separate database tables.

---

## 1. Domain Boundary Map

```
+===============================================================================+
|                           eShopOnWeb System                                   |
|                                                                               |
|  +=====================+   +=====================+   +=====================+  |
|  |   CATALOG DOMAIN    |   |   BASKET DOMAIN     |   |   ORDER DOMAIN      |  |
|  |   (Active)          |   |   (Active)          |   |   (Active)          |  |
|  |                     |   |                     |   |                     |  |
|  |  CatalogItem        |-->|  Basket             |-->|  Order              |  |
|  |  CatalogBrand       |   |  BasketItem         |   |  OrderItem          |  |
|  |  CatalogType        |   |                     |   |  Address (VO)       |  |
|  |                     |   |  Price locked       |   |  CatalogItemOrdered |  |
|  |  DATA-ENT-001       |   |  at add-time        |   |  (VO — snapshot)    |  |
|  |  DATA-ENT-002       |   |  DATA-ENT-004       |   |  DATA-ENT-006       |  |
|  |  DATA-ENT-003       |   |  DATA-ENT-005       |   |  DATA-ENT-007       |  |
|  |                     |   |                     |   |  DATA-ENT-011       |  |
|  |  DATA-AGG-004       |   |  DATA-AGG-001       |   |  DATA-ENT-012       |  |
|  +=====================+   +=====================+   |  DATA-AGG-002       |  |
|                                                      +=====================+  |
|  +=====================+   +=====================+                            |
|  |  IDENTITY DOMAIN    |   |  BUYER DOMAIN       |                            |
|  |  (Active)           |   |  (DORMANT)          |                            |
|  |                     |   |                     |                            |
|  |  ApplicationUser    |   |  BuyerAggregate     |<-- not in DbContext         |
|  |  (in IdentityDB)    |   |  Buyer              |<-- no service layer         |
|  |                     |   |  PaymentMethod      |<-- PCI comment in source   |
|  |  DATA-ENT-010       |   |  DATA-ENT-008       |                            |
|  |  DATA-REPO-002      |   |  DATA-ENT-009       |                            |
|  +=====================+   |  DATA-AGG-003       |                            |
|                            +=====================+                            |
|  +=========================================================================+  |
|  |                    INFRASTRUCTURE / SHARED KERNEL                       |  |
|  |  BaseEntity (DATA-ENT-013) * EfRepository * CatalogContextSeed         |  |
|  |  AppIdentityDbContextSeed * IMemoryCache (CACHE-001, 30s)              |  |
|  |  Blazored.LocalStorage (CACHE-002, 1min) * EmailSender (STUB)          |  |
|  +=========================================================================+  |
+===============================================================================+
```

---

## 2. DDD Aggregates

The Enterprise Knowledge Graph records exactly **four** aggregates (DATA-AGG-001..004). Aggregate roots are the consistency boundary; only the root is referenced from outside the aggregate.

### 2.1 Aggregate Inventory

| Aggregate | ID | Root Entity | Child Entities / Value Objects | Domain | Status | Confidence |
|-----------|----|-----------|-----------------------------|--------|--------|------------|
| **BasketAggregate** | DATA-AGG-001 | Basket (DATA-ENT-004) | BasketItem (DATA-ENT-005) | Basket | Active | HIGH |
| **OrderAggregate** | DATA-AGG-002 | Order (DATA-ENT-006) | OrderItem (DATA-ENT-007), Address VO (DATA-ENT-011), CatalogItemOrdered VO (DATA-ENT-012) | Order | Active — Immutable after creation | HIGH |
| **BuyerAggregate** | DATA-AGG-003 | Buyer (DATA-ENT-008) | PaymentMethod (DATA-ENT-009) | Buyer | **DORMANT — not in DbContext** | HIGH |
| **CatalogAggregate** | DATA-AGG-004 | CatalogItem (DATA-ENT-001) | — (CatalogBrand and CatalogType are independent reference entities) | Catalog | Active | HIGH |

### 2.2 Aggregate Detail — BasketAggregate (DATA-AGG-001)

**Root:** Basket (DATA-ENT-004)  
**Children:** BasketItem (DATA-ENT-005)  
**Persistence:** CatalogDatabase.Baskets + CatalogDatabase.BasketItems (DATA-REPO-001)  
**Backing service:** APP-SVC-001 (BasketService)

**Invariants enforced by aggregate:**
- Basket add without explicit quantity defaults to 1 (BIZ-RULE-004)
- Adding the same CatalogItemId a second time increments the existing BasketItem.Quantity — no duplicates (confirmed auto-merge — not an exception)
- UnitPrice on a BasketItem is locked at the moment the item is added; subsequent catalogue price changes do not propagate into the basket
- The GUID-based BuyerId identifies anonymous shoppers; the username string identifies authenticated shoppers

**Lifecycle:**
- **Created** when a shopper first adds an item (BIZ-CAP-016 Get or Create Basket)
- **Modified** by item additions, quantity updates, and anonymous transfer merge
- **Deleted** permanently after successful checkout (BIZ-RULE-003) or after anonymous basket is transferred to user basket (BIZ-RULE-002)

**Key relationships:**
- Basket 1..* BasketItem (owned collection — BasketItem has no meaning outside its Basket)
- BasketItem *..1 CatalogItem (soft reference by CatalogItemId — no DB FK confirmed; cross-domain read-only)
- Basket *..1 ApplicationUser (cross-DB soft reference by BuyerId string — no FK)

### 2.3 Aggregate Detail — OrderAggregate (DATA-AGG-002)

**Root:** Order (DATA-ENT-006)  
**Children:** OrderItem (DATA-ENT-007), Address VO (DATA-ENT-011, inlined), CatalogItemOrdered VO (DATA-ENT-012, inlined)  
**Persistence:** CatalogDatabase.Orders + CatalogDatabase.OrderItems (DATA-REPO-001)  
**Backing service:** APP-SVC-004 (OrderService)

**Invariants enforced by aggregate:**
- Order requires a non-empty basket to be created (BIZ-RULE-019)
- Order requires a BuyerId (BIZ-RULE-011) — set from authenticated shopper's identity string
- Product name, picture URI, and catalogue ID are snapshotted into CatalogItemOrdered at the moment of order creation — immune to future catalogue changes (BIZ-RULE-001)
- Orders are **immutable after creation** — no status field, no update or cancellation operations (BIZ-RULE-012)
- Order total = Σ(OrderItem.UnitPrice × OrderItem.Units) computed via Order.Total() method (BIZ-CAP-018)

**Lifecycle:**
- **Created** by OrderService.CreateOrderAsync (BIZ-PROC-001)
- **Immutable** forever after creation (BIZ-RULE-012 — no status transitions, no updates)
- Never deleted by application code (financial record — BIZ-RULE-030 data isolation by BuyerId)

**Value object schema:**
- **Address (VO)** — inlined into Orders table as ShipToAddress_* columns: Street nvarchar(180), City nvarchar(100), State nvarchar(60) nullable, Country nvarchar(90), ZipCode nvarchar(18). **Current gap: always hardcoded to "123 Main St., Kent, OH, 44240" (BIZ-RULE-015)**
- **CatalogItemOrdered (VO)** — inlined into OrderItems table as ItemOrdered_* columns: CatalogItemId int (snapshot reference), ProductName nvarchar(50) (frozen at purchase), PictureUri nvarchar(max) (frozen at purchase)

**Key relationships:**
- Order 1..* OrderItem (owned collection)
- OrderItem 1..1 CatalogItemOrdered (embedded snapshot VO — no live FK to Catalog)
- Order 1..1 Address (embedded VO — owned type, inlined columns)
- Order *..1 ApplicationUser (cross-DB soft reference by BuyerId — no FK; BIZ-RULE-011)

**PII fields:**
- Order.BuyerId — MEDIUM sensitivity (may be email per ASMP-001)
- All ShipToAddress_* columns — HIGH sensitivity (full physical address)

### 2.4 Aggregate Detail — BuyerAggregate (DATA-AGG-003) — DORMANT

**Root:** Buyer (DATA-ENT-008) — **NOT PERSISTED**  
**Children:** PaymentMethod (DATA-ENT-009) — **NOT PERSISTED**  
**Status:** DORMANT — confirmed dead. Buyer.cs and PaymentMethod.cs exist in ApplicationCore but:
- No DbSet registration in CatalogContext
- No active service layer creates or queries these entities
- No REST endpoint, no repository usage
- DA Agent 2 confirmed at HIGH confidence (BIZ-RULE-035; DISC-003 in normalization log)

**Activation path:** AO-05 — requires PCI-compliant payment processor (Stripe or Braintree) integration  
**PCI constraint:** BIZ-RULE-034 — PaymentMethod.CardId must store only a PCI-compliant token (e.g. Stripe charge token), never raw card number data. PaymentMethod.cs:7 contains an explicit PCI comment referencing Stripe.

**When activated, expected schema:**
- Buyer: IdentityGuid (string — links to ApplicationUser.Id by value convention, same soft-reference pattern as Order.BuyerId)
- PaymentMethod: Alias (string? nullable), CardId (string? nullable — PCI token only), Last4 (string? nullable — last 4 digits only)

### 2.5 Aggregate Detail — CatalogAggregate (DATA-AGG-004)

**Root:** CatalogItem (DATA-ENT-001)  
**Children:** None (CatalogBrand and CatalogType are independent reference entities, not children of CatalogAggregate)  
**Persistence:** CatalogDatabase.Catalog (DATA-REPO-001)  
**Backing service:** APP-SVC-008 (EfRepository via PublicApi endpoints + CachedCatalogViewModelService)

**Invariants enforced:**
- Product name must be unique (BIZ-RULE-020)
- Price must be greater than zero (BIZ-RULE-021)
- Name and description must not be empty at creation and update (BIZ-RULE-022)
- New products receive a default placeholder image; admin image upload is permanently disabled (BIZ-RULE-023)

**ID strategy:** HiLo sequence (catalog_hilo) — not auto-increment identity. This affects bulk insert behaviour and migration rollback strategies.

**Key relationships:**
- CatalogItem *..1 CatalogBrand (FK: CatalogBrandId — reference lookup only)
- CatalogItem *..1 CatalogType (FK: CatalogTypeId — reference lookup only)
- CatalogItem 1..* BasketItem (soft reverse reference by CatalogItemId — no DB FK on BasketItems side)
- CatalogItem 1..* CatalogItemOrdered (snapshot reference — no DB FK; ORDER reads from this at checkout time)

---

## 3. Entity Inventory — All 13 DATA-ENT Nodes

### 3.1 Catalog Domain Entities

#### DATA-ENT-001 — CatalogItem (Product)

**Business concept:** Product offered for sale  
**Domain:** Catalog  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** CatalogDatabase.Catalog table  
**ID strategy:** HiLo sequence (catalog_hilo)  
**Shared by domains:** Catalog (owner), Basket (reads price at add-time), Order (snapshot at checkout), PublicApi (CRUD), BlazorAdmin (admin reads/writes)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | HiLo sequence |
| Name | nvarchar(50) | NOT NULL | Unique (BIZ-RULE-020) |
| Description | nvarchar(max) | NULL | Non-empty at create/update (BIZ-RULE-022) |
| Price | decimal(18,2) | NOT NULL | Must be > 0 (BIZ-RULE-021) |
| PictureUri | nvarchar(max) | NULL | Default placeholder assigned (BIZ-RULE-023) |
| CatalogTypeId | int FK | NOT NULL | References CatalogTypes.Id |
| CatalogBrandId | int FK | NOT NULL | References CatalogBrands.Id |
| AvailableStock | int | NOT NULL | Inventory tracking field — no checkout validation rule exists in current implementation |
| RestockThreshold | int | NOT NULL | Minimum threshold before restock trigger |
| MaxStockThreshold | int | NOT NULL | Maximum stock ceiling |

**Evidence:** DA:erd.md; DA:schema-catalogue.json; BA:05_data_model.md; CreateCatalogItemEndpoint.cs; UpdateCatalogItemEndpoint.cs  
**Guard clause pattern:** Guard.Against.NegativeOrZero (Price), Guard.Against.NullOrEmpty (Name, Description)

---

#### DATA-ENT-002 — CatalogBrand (Brand)

**Business concept:** Manufacturer or label grouping products  
**Domain:** Catalog  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** CatalogDatabase.CatalogBrands table  
**ID strategy:** HiLo sequence (catalog_brand_hilo)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | HiLo sequence |
| Brand | nvarchar(100) | NOT NULL | DA Agent 2 corrected from nvarchar(max) (DISC-002) |

**Seed data:** 5 brands seeded on startup (BIZ-RULE-031)  
**Example values:** Azure, .NET, Visual Studio, SQL Server, Other

---

#### DATA-ENT-003 — CatalogType (Category / Product Type)

**Business concept:** Product category or type grouping  
**Domain:** Catalog  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** CatalogDatabase.CatalogTypes table  
**ID strategy:** HiLo sequence (catalog_type_hilo)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | HiLo sequence |
| Type | nvarchar(100) | NOT NULL | DA Agent 2 corrected from nvarchar(max) (DISC-002) |

**Seed data:** 4 types seeded on startup (BIZ-RULE-031)  
**Example values:** Mug, T-Shirt, Sheet, USB Memory Stick

---

### 3.2 Basket Domain Entities

#### DATA-ENT-004 — Basket (Shopping Basket)

**Business concept:** Temporary collection of products a customer intends to purchase  
**Domain:** Basket  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** CatalogDatabase.Baskets table  
**Aggregate:** Root of DATA-AGG-001 (BasketAggregate)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | IDENTITY (not HiLo) |
| BuyerId | nvarchar(256) | NOT NULL | GUID string for anonymous; username string for authenticated (ASMP-001: likely email address) |

**PII note:** BuyerId is an identity reference. If BuyerId stores email (ASMP-001), sensitivity is HIGH.  
**Lifecycle:** Created on first basket add; deleted on checkout completion or anonymous basket transfer (BIZ-RULE-002, BIZ-RULE-003).

---

#### DATA-ENT-005 — BasketItem (Basket Line Item)

**Business concept:** A single line in a basket referencing a product with a locked price  
**Domain:** Basket  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** CatalogDatabase.BasketItems table  
**Aggregate:** Child entity within DATA-AGG-001 (BasketAggregate)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | IDENTITY |
| BasketId | int FK | NOT NULL | References Baskets.Id |
| CatalogItemId | int | NOT NULL | Soft reference to Catalog.Id — no DB FK confirmed |
| UnitPrice | decimal | NOT NULL | **Locked at basket-add time; does NOT update if catalogue price changes** |
| Quantity | int | NOT NULL | ≥ 0; zero-quantity lines are removed |

**Key design decision:** CatalogItemId is a soft cross-domain reference with no DB FK. If a CatalogItem is deleted, orphaned BasketItems accumulate. This is a known risk with no current cleanup mechanism.

---

### 3.3 Order Domain Entities

#### DATA-ENT-006 — Order (Confirmed Purchase)

**Business concept:** A confirmed purchase record capturing date, buyer, shipping address, and line items  
**Domain:** Order  
**Status:** Active — persisted — **immutable after creation**  
**Confidence:** HIGH  
**Database:** CatalogDatabase.Orders table  
**Aggregate:** Root of DATA-AGG-002 (OrderAggregate)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | IDENTITY |
| BuyerId | nvarchar(256) | NOT NULL | Cross-DB soft reference to AspNetUsers.Id; application code only — no FK (BIZ-RULE-011) |
| OrderDate | datetimeoffset | NOT NULL | Auto-set at creation (DateTime.UtcNow) |
| ShipToAddress_Street | nvarchar(180) | NOT NULL | Address VO column (BIZ-RULE-033). **Currently hardcoded: "123 Main St."** |
| ShipToAddress_City | nvarchar(100) | NOT NULL | Address VO column. **Currently hardcoded: "Kent"** |
| ShipToAddress_State | nvarchar(60) | NULL | Address VO column. **Currently hardcoded: "OH"** |
| ShipToAddress_Country | nvarchar(90) | NOT NULL | Address VO column. **Currently hardcoded: "United States"** |
| ShipToAddress_ZipCode | nvarchar(18) | NOT NULL | Address VO column. **Currently hardcoded: "44240"** |

**PII fields:** BuyerId (MEDIUM, potentially HIGH if email per ASMP-001); all ShipToAddress_* columns (HIGH — full physical address).  
**Immutability:** BIZ-RULE-012 — no status field; once created, orders cannot be updated, cancelled, or progressed.

---

#### DATA-ENT-007 — OrderItem (Order Line Item)

**Business concept:** A single purchased line item in an order with a purchase-time product snapshot  
**Domain:** Order  
**Status:** Active — persisted — **immutable after creation**  
**Confidence:** HIGH  
**Database:** CatalogDatabase.OrderItems table  
**Aggregate:** Child entity within DATA-AGG-002 (OrderAggregate)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| Id | int PK | NOT NULL | IDENTITY |
| OrderId | int FK | NOT NULL | References Orders.Id |
| ItemOrdered_CatalogItemId | int | NOT NULL | Snapshot reference — no live FK (intentional) |
| ItemOrdered_ProductName | nvarchar(50) | NOT NULL | **Purchase-time snapshot — frozen at checkout (BIZ-RULE-001)** |
| ItemOrdered_PictureUri | nvarchar(max) | NULL | **Purchase-time snapshot — frozen at checkout (BIZ-RULE-001)** |
| UnitPrice | decimal(18,2) | NOT NULL | Price locked at basket-add time (propagated from BasketItem.UnitPrice) |
| Units | int | NOT NULL | Quantity at checkout |

**Snapshot pattern:** ItemOrdered_ProductName and ItemOrdered_PictureUri are captured at order creation time and never updated. If the catalogue product is renamed, repriced, or deleted after the order, the order history is unaffected — the snapshot preserves the historical product state. This is a deliberate DDD design decision (BIZ-RULE-001).

---

#### DATA-ENT-008 — Buyer (Buyer Profile) — DORMANT

**Business concept:** Buyer profile linking identity to payment methods  
**Domain:** Buyer  
**Status:** **DORMANT — not persisted — structurally defined only**  
**Confidence:** HIGH (confirmed dead)  
**Database:** NONE — not registered in CatalogContext DbSet  
**Evidence:** DA:erd.md CONFIRMED DEAD; BIZ-RULE-035; DISC-003 in normalization log

**Expected schema (when activated via AO-05):**
- IdentityGuid: string (links to ApplicationUser.Id by value convention — no DB FK)

**Note:** Currently the buyer reference in orders and baskets is satisfied by ApplicationUser.Id (DATA-ENT-010) directly. The Buyer entity is structurally present in ApplicationCore but dormant.

---

#### DATA-ENT-009 — PaymentMethod (Payment Method Record) — DORMANT

**Business concept:** A PCI-compliant payment method associated with a Buyer  
**Domain:** Buyer  
**Status:** **DORMANT — not persisted — structurally defined only**  
**Confidence:** HIGH (confirmed dead)  
**Database:** NONE — no DbSet, no EF configuration, no service usage  
**Evidence:** BIZ-RULE-034; PaymentMethod.cs:7 contains explicit PCI comment referencing Stripe

**Expected schema (when activated via AO-05, PCI-compliant):**
- Alias: string? nullable (friendly display name)
- CardId: string? nullable (**PCI-compliant token ONLY** — never raw card number)
- Last4: string? nullable (last 4 digits of card for display)

**PCI constraint (BIZ-RULE-034):** Must never store: full card number (PAN), CVV/CVC, full expiry. Only store what the payment processor token provides.

---

### 3.4 Identity Domain Entities

#### DATA-ENT-010 — ApplicationUser (Identity / Shopper Account)

**Business concept:** Identity and authentication record for a shopper or staff member  
**Domain:** Identity  
**Status:** Active — persisted  
**Confidence:** HIGH  
**Database:** IdentityDatabase.AspNetUsers (DATA-REPO-002)  
**Backing framework:** ASP.NET Core Identity (EF Core provider)

| Column | Type | Notes |
|--------|------|-------|
| Id | nvarchar (GUID) PK | Standard ASP.NET Identity ID |
| UserName | nvarchar | Typically = Email for this system |
| Email | nvarchar | NOT NULL — PRIMARY identifier; HIGH PII |
| EmailConfirmed | bit | Currently always false (BIZ-RULE-027 gap) |
| PasswordHash | nvarchar | PBKDF2/SHA-256 hash — not reversible; HIGH PII |
| PhoneNumber | nvarchar | NULL — optional; MEDIUM PII |
| LockoutEnabled | bit | TRUE — lockout policy active (BIZ-RULE-025) |
| LockoutEnd | datetimeoffset | NULL unless locked |

**PII classification (from DA:pii-inventory.json):**
- Email: HIGH sensitivity (PII-01)
- UserName: MEDIUM sensitivity (PII-02)
- PasswordHash: HIGH sensitivity (PII-03) — stored as PBKDF2 hash
- PhoneNumber: MEDIUM sensitivity (PII-04)

**Seeded accounts (production risk):**
- demouser@microsoft.com — BIZ-RULE-029 (hardcoded password)
- admin@microsoft.com — BIZ-RULE-013 (hardcoded password; assigned Administrators role)

---

#### DATA-ENT-011 — Address (Shipping Address Value Object)

**Business concept:** The physical shipping destination for an order  
**Domain:** Order  
**Status:** Active — persisted (embedded/owned, not a separate table)  
**Confidence:** HIGH  
**Database:** Inlined into CatalogDatabase.Orders as ShipToAddress_* columns (owned entity pattern)  
**Note:** This is a value object — not an independent table. It is part of the OrderAggregate (DATA-AGG-002).

| Logical field | Column | Type | Constraints |
|---------------|--------|------|-------------|
| Street | ShipToAddress_Street | nvarchar(180) | NOT NULL |
| City | ShipToAddress_City | nvarchar(100) | NOT NULL |
| State | ShipToAddress_State | nvarchar(60) | NULL |
| Country | ShipToAddress_Country | nvarchar(90) | NOT NULL |
| ZipCode | ShipToAddress_ZipCode | nvarchar(18) | NOT NULL |

**PII classification:** HIGH — full physical shipping address (PII-06)  
**Critical gap (BIZ-RULE-015):** All current order records in the system have the same hardcoded address: Street="123 Main St.", City="Kent", State="OH", Country="United States", ZipCode="44240". This makes the system unsuitable for production use until AO-01 is implemented.

---

#### DATA-ENT-012 — CatalogItemOrdered (Purchase-Time Product Snapshot Value Object)

**Business concept:** An immutable snapshot of a product as it appeared at the time of purchase  
**Domain:** Order (conceptually), Catalog (physically owned in entity_to_service)  
**Status:** Active — persisted (embedded/owned, not a separate table)  
**Confidence:** HIGH  
**Database:** Inlined into CatalogDatabase.OrderItems as ItemOrdered_* columns (owned entity pattern)

| Logical field | Column | Type | Notes |
|---------------|--------|------|-------|
| CatalogItemId | ItemOrdered_CatalogItemId | int | Snapshot reference — no live FK |
| ProductName | ItemOrdered_ProductName | nvarchar(50) | **Frozen at order creation — BIZ-RULE-001** |
| PictureUri | ItemOrdered_PictureUri | nvarchar(max) | **Frozen at order creation — BIZ-RULE-001** |

**Design intent:** This value object implements the snapshot pattern — it captures the product state at the exact moment of purchase. Future catalogue updates (renames, reprices, deletions) do not corrupt historical order records. The snapshot is immune to CatalogItem.Name changes, CatalogItem.PictureUri changes, or even CatalogItem deletion.

---

#### DATA-ENT-013 — BaseEntity (Shared Kernel Base Class)

**Business concept:** Abstract base class providing the Id property for all domain entities  
**Domain:** SharedKernel / Infrastructure  
**Status:** Active — abstract base class (not a database table)  
**Confidence:** HIGH  
**Database:** NONE — abstract base class only

| Property | Type | Notes |
|----------|------|-------|
| Id | int | Inherited by all domain entities |

**Note:** All domain entities (DATA-ENT-001..010) inherit from BaseEntity. The Id field is the universal primary key field across the eShopOnWeb domain model. BaseEntity lives in ApplicationCore with zero outbound project references, making it the clean core of the Clean Architecture implementation.

---

## 4. Repositories

### 4.1 DATA-REPO-001 — CatalogDatabase

**Name:** CatalogDatabase (Microsoft.eShopOnWeb.CatalogDb)  
**Technology:** SQL Server (Azure SQL Edge in Docker — **EOL March 2025**; Azure SQL Database in production per ASMP-003)  
**Context class:** CatalogContext (EF Core DbContext)  
**Connection key:** CatalogConnection (appsettings.json)  
**Owner:** Infrastructure layer (APP-SVC-008 EfRepository)

**Tables hosted:**

| Table | Entity | Domain | ID Strategy |
|-------|--------|--------|------------|
| Catalog | DATA-ENT-001 (CatalogItem) | Catalog | HiLo sequence (catalog_hilo) |
| CatalogBrands | DATA-ENT-002 (CatalogBrand) | Catalog | HiLo sequence (catalog_brand_hilo) |
| CatalogTypes | DATA-ENT-003 (CatalogType) | Catalog | HiLo sequence (catalog_type_hilo) |
| Baskets | DATA-ENT-004 (Basket) | Basket | IDENTITY |
| BasketItems | DATA-ENT-005 (BasketItem) | Basket | IDENTITY |
| Orders | DATA-ENT-006 (Order) + DATA-ENT-011 (Address VO inlined) | Order | IDENTITY |
| OrderItems | DATA-ENT-007 (OrderItem) + DATA-ENT-012 (CatalogItemOrdered VO inlined) | Order | IDENTITY |

**Architecture concern:** CatalogContext is a single DbContext spanning 3 functional domains (Catalog, Basket, Order). This is a shared persistence boundary that must be split when extracting domains into independent services. DISC-002 in the normalization log confirms this as a high-impact migration concern.

**Docker infrastructure:** TECH-INF-003 — Azure SQL Edge container (`mcr.microsoft.com/azure-sql-edge`) at port 1433:1433. SA_PASSWORD is hardcoded in docker-compose.yml: `@someThingComplicated1234` (TECH-SEC-007 — CRITICAL vulnerability).

---

### 4.2 DATA-REPO-002 — IdentityDatabase

**Name:** IdentityDatabase (Microsoft.eShopOnWeb.Identity)  
**Technology:** SQL Server (same instance as CatalogDatabase)  
**Context class:** AppIdentityDbContext (EF Core DbContext — inherits IdentityDbContext)  
**Connection key:** IdentityConnection (appsettings.json)  
**Owner:** Infrastructure layer (ASP.NET Core Identity)

**Tables hosted (standard ASP.NET Core Identity schema):**

| Table | Purpose |
|-------|---------|
| AspNetUsers | ApplicationUser records (DATA-ENT-010) |
| AspNetRoles | Role records |
| AspNetUserRoles | User-role join table |
| AspNetUserClaims | User claim records |
| AspNetRoleClaims | Role claim records |
| AspNetUserLogins | External login provider links |
| AspNetUserTokens | Auth tokens (HIGH PII — PII-08) |

**Isolation advantage:** AppIdentityDbContext is already isolated from CatalogContext — this is the cleanest boundary in the system. Identity domain can be extracted as a separate service without shared-context splitting.

**PII concentration:** This database contains the most sensitive PII in the system:
- PII-01: AspNetUsers.Email (HIGH)
- PII-02: AspNetUsers.UserName (MEDIUM)
- PII-03: AspNetUsers.PasswordHash (HIGH)
- PII-04: AspNetUsers.PhoneNumber (MEDIUM)
- PII-08: AspNetUserTokens.Value (HIGH — auth token)

---

## 5. Cross-Domain Soft References (No FK Enforcement)

The following cross-domain references are enforced only by application code — no database foreign keys exist.

| From | To | Boundary | Enforcement | Risk |
|------|----|----------|-------------|------|
| CatalogDatabase.Baskets.BuyerId | IdentityDatabase.AspNetUsers.Id | Cross-DB | Application code only | Orphan baskets accumulate if user is deleted; GDPR erasure gap (OQ-002) |
| CatalogDatabase.Orders.BuyerId | IdentityDatabase.AspNetUsers.Id | Cross-DB | Application code only | No FK cascade; order history preserved after user deletion (may be intentional for financial records — OQ-003) |
| CatalogDatabase.BasketItems.CatalogItemId | CatalogDatabase.Catalog.Id | Same-DB | No confirmed DB FK | Orphan basket items if catalogue item is deleted |
| CatalogDatabase.OrderItems.ItemOrdered_CatalogItemId | CatalogDatabase.Catalog.Id | Same-DB | No DB FK (snapshot pattern — intentional) | Mitigated: ProductName and PictureUri captured at order time; order display survives catalogue item deletion (BIZ-RULE-001) |

---

## 6. Caching Architecture

The system has **two independent caching layers** with different technologies, TTLs, and invalidation strategies.

| Cache | ID | Technology | TTL | Location | Invalidation |
|-------|----|-----------|-----|----------|-------------|
| Web MVC Catalogue Browse | CACHE-001 | ASP.NET Core IMemoryCache (server-side in-process) | 30 seconds sliding | Web server process | TTL only — NOT invalidated on admin writes |
| BlazorAdmin Catalogue List | CACHE-002 | Blazored.LocalStorage (browser localStorage — client-side) | 1 minute (DateCreated.AddMinutes(1)) | User's browser | Write-through for items (RefreshLocalStorageList on Create/Edit/Delete); TTL-only for brands/types |

**Critical staleness gap:** When an admin creates, updates, or deletes a product via BIZ-PROC-005, CACHE-002 (BlazorAdmin localStorage) is immediately refreshed via write-through invalidation. However, CACHE-001 (Web MVC IMemoryCache) is NOT invalidated — the public storefront may continue to display the old product data for up to 30 seconds. This cross-cache staleness is a known gap (GAP-015).

**Scale limitation:** IMemoryCache (CACHE-001) is per-process (in-memory). Horizontal scaling of the Web MVC application will cause different instances to have different cache states, potentially serving inconsistent product data. Redis would address this (OQ-007).

---

## 7. Ubiquitous Language Glossary

All terms are derived from the Enterprise Knowledge Graph `business` section and source code evidence. Terms are grouped by bounded context.

### Catalog Domain

| Term | Definition | Evidence |
|------|-----------|---------|
| **Catalogue** | The complete collection of products offered for sale in the eShopOnWeb storefront | DATA-ENT-001 (CatalogItem) |
| **Product** / **Catalogue Item** | A single item available for purchase, identified by a unique Name, classified by Brand and Type, and priced at a positive decimal Price | DATA-ENT-001; BIZ-RULE-020, 021, 022 |
| **Brand** | A manufacturer or product label grouping one or more products (e.g. "Azure", ".NET", "Visual Studio") | DATA-ENT-002 |
| **Type** | A product category grouping (e.g. "Mug", "T-Shirt", "Sheet", "USB Memory Stick") | DATA-ENT-003 |
| **Picture URI** | The URI of the product's display image; always a default placeholder in the current system (admin upload disabled — BIZ-RULE-023) | DATA-ENT-001.PictureUri |
| **Catalogue Seeding** | The process of populating the catalogue with 5 brands, 4 types, and 12 products on first application startup, skipped if data already exists | BIZ-RULE-031; BIZ-PROC-007 |
| **HiLo Sequence** | The ID generation strategy for Catalogue entities (catalog_hilo, catalog_brand_hilo, catalog_type_hilo) — allocates blocks of IDs without per-row database round-trips | DATA-REPO-001 |

### Basket Domain

| Term | Definition | Evidence |
|------|-----------|---------|
| **Basket** | A temporary collection of products a shopper intends to purchase, identified by a BuyerId. Created automatically on first item add; deleted on checkout or basket transfer. | DATA-ENT-004; DATA-AGG-001 |
| **Basket Item** / **Basket Line** | A single line in a basket referencing a CatalogItem, with the price **locked at add-time** and a quantity. Duplicate items auto-merge by incrementing quantity. | DATA-ENT-005 |
| **BuyerId** | The identifier linking a Basket or Order to a shopper. For anonymous shoppers: a GUID string from the basket cookie. For authenticated shoppers: the username string (likely email address per ASMP-001). | DATA-ENT-004.BuyerId |
| **Anonymous Basket** | A basket owned by a guest shopper (BuyerId = GUID cookie value). Identified by a 10-year GUID cookie marked as essential (BIZ-RULE-016). | BIZ-CAP-012; BIZ-ACT-001 |
| **Basket Transfer** | The process of merging an anonymous basket into a registered user's basket at the moment of Web login. Items are merged (quantities incremented on duplicates); anonymous basket permanently deleted. **Triggered only by Web login, not API login.** | BIZ-RULE-002; BIZ-PROC-004 |
| **Price Lock** | The behaviour of locking BasketItem.UnitPrice at the moment the item is added to the basket. Subsequent catalogue price changes do not propagate into existing basket items. | DATA-ENT-005.UnitPrice |

### Order Domain

| Term | Definition | Evidence |
|------|-----------|---------|
| **Order** | A confirmed purchase record created at checkout, containing an order date, a BuyerId (soft reference to identity), a shipping address, and one or more order items. Orders are **immutable after creation**. | DATA-ENT-006; BIZ-RULE-012 |
| **Order Item** | A single purchased line in an order, containing the purchase-time product snapshot and the quantity. Immutable — cannot be changed after order creation. | DATA-ENT-007 |
| **Ordered Item Snapshot** / **CatalogItemOrdered** | An immutable value object embedded in each OrderItem capturing the CatalogItemId, ProductName, and PictureUri **at the moment of purchase**. Immune to future catalogue changes (catalogue product renames, price changes, or deletions do not affect this snapshot). | DATA-ENT-012; BIZ-RULE-001 |
| **Ship-To Address** | The physical destination address for an order. Currently hardcoded to "123 Main St., Kent, OH, 44240" (production gap — BIZ-RULE-015). | DATA-ENT-011 |
| **Order Total** | The sum of all OrderItem.UnitPrice × OrderItem.Units, computed by the Order.Total() method. | BIZ-CAP-018 |
| **Checkout** | The process of converting a non-empty authenticated basket into a confirmed Order. Requires authentication (BIZ-RULE-018), a non-empty basket (BIZ-RULE-019), and produces an immutable order and deletes the basket (BIZ-RULE-003). | BIZ-PROC-001 |

### Identity Domain

| Term | Definition | Evidence |
|------|-----------|---------|
| **Application User** | The identity and authentication record for a shopper or staff member. Stored in IdentityDatabase (separate from CatalogDatabase). Provides the authoritative source of identity for the entire system. | DATA-ENT-010; DATA-REPO-002 |
| **ADMINISTRATORS Role** | The only defined role in the system (confirmed role string: "Administrators"). Grants the ability to create, update, and delete catalogue products via the PublicApi. | BIZ-RULE-005; BlazorShared/Authorization/Constants.cs |
| **JWT Token** | A signed JSON Web Token issued by POST /api/authenticate. Carries the user name and all assigned role claims. Expires in 7 days (BIZ-RULE-024). **Current gap: signed with a hardcoded key (BIZ-RULE-032).** | BIZ-CAP-022, BIZ-CAP-023 |
| **Account Lockout** | The security mechanism that locks an account after repeated failed password attempts. Identity password minimum: 6 characters (below NIST minimum of 8). | BIZ-RULE-025 |
| **Demo Shopper** | The pre-seeded account demouser@microsoft.com with password `Pass@word1`. For local development only. | BIZ-ACT-004; BIZ-RULE-029 |
| **Seeded Administrator** | The pre-seeded account admin@microsoft.com with password `Pass@word1` and Administrators role. For local development only. | BIZ-ACT-005; BIZ-RULE-013 |

### Buyer Domain (Dormant Terms)

| Term | Definition | Evidence |
|------|-----------|---------|
| **Buyer** | (Aspirational) A customer aggregate distinct from the authentication identity, intended to hold payment methods. Currently dormant — not in DbContext, no service layer. | DATA-ENT-008; BIZ-RULE-035 |
| **Payment Method** | (Aspirational) A PCI-compliant payment record holding only a payment processor token, alias, and last 4 digits. Never raw card data. | DATA-ENT-009; BIZ-RULE-034 |

### Infrastructure Terms

| Term | Definition | Evidence |
|------|-----------|---------|
| **Guard Clause** | A method that validates a domain invariant at object construction time and throws an exception if the invariant is violated. Implemented via Ardalis.GuardClauses. All domain entities use this pattern (BIZ-RULE-014). | GuardExtensions.cs |
| **EfRepository** | The generic Repository implementation (IRepository<T> / IReadRepository<T>) backed by Entity Framework Core. Has a coupling score of 16 — the highest in the codebase. 6 API endpoints depend on it directly, bypassing domain service abstraction (ARCH-VIOL-001..007). | APP-SVC-008; ARCH-VIOL-009 |
| **BaseEntity** | The abstract base class providing the Id property inherited by all domain entities. Lives in ApplicationCore. | DATA-ENT-013 |

---

## 8. Architecture Violations Affecting the Domain Model

The following violations are relevant to forward-engineering of the domain model and must be addressed during modernisation.

| ID | Violation | Domain Impact |
|----|-----------|--------------|
| **ARCH-VIOL-001..007** | 6 PublicApi endpoints and 1 PageModel depend directly on EfRepository (APP-SVC-008), bypassing domain service abstraction | Catalogue, Basket, and Order domain services are not the true application boundary — EfRepository is accessed directly from the API layer |
| **ARCH-VIOL-008** | Module dependency cycle: Admin → ApplicationCore → Basket → Catalog → DataAccess → Identity → Order → Web | Prevents independent domain extraction; all 5 active domains are entangled |
| **ARCH-VIOL-009** | EfRepository coupling score = 16 (highest in codebase) | Over-centralised data access; single point of coupling for the entire persistence layer |
| **ARCH-VIOL-011** | ApplicationCore references BlazorShared (UI-shared library) | Domain layer should have zero outbound references; this reference violates Clean Architecture's dependency rule |

---

## 9. Domain Model — Relationship Summary

```
CATALOG DOMAIN
  CatalogItem (DATA-ENT-001) *..1 CatalogBrand (DATA-ENT-002) [FK: CatalogBrandId]
  CatalogItem (DATA-ENT-001) *..1 CatalogType (DATA-ENT-003) [FK: CatalogTypeId]

BASKET DOMAIN
  Basket (DATA-ENT-004) 1..* BasketItem (DATA-ENT-005) [FK: BasketId, owned]
  BasketItem (DATA-ENT-005) *..1 CatalogItem (DATA-ENT-001) [soft ref: CatalogItemId, no DB FK]
  Basket (DATA-ENT-004) *..1 ApplicationUser (DATA-ENT-010) [cross-DB soft ref: BuyerId, no FK]

ORDER DOMAIN
  Order (DATA-ENT-006) 1..* OrderItem (DATA-ENT-007) [FK: OrderId, owned]
  Order (DATA-ENT-006) 1..1 Address (DATA-ENT-011) [owned VO, inlined columns]
  OrderItem (DATA-ENT-007) 1..1 CatalogItemOrdered (DATA-ENT-012) [owned VO, inlined columns]
  CatalogItemOrdered (DATA-ENT-012) *..1 CatalogItem (DATA-ENT-001) [snapshot ref: CatalogItemId, no live FK]
  Order (DATA-ENT-006) *..1 ApplicationUser (DATA-ENT-010) [cross-DB soft ref: BuyerId, no FK]

IDENTITY DOMAIN
  ApplicationUser (DATA-ENT-010) is persisted in DATA-REPO-002 (IdentityDatabase)
  ApplicationUser 1..* Roles (AspNetRoles) [via AspNetUserRoles join table]

BUYER DOMAIN (DORMANT)
  Buyer (DATA-ENT-008) 1..* PaymentMethod (DATA-ENT-009) [aspirational — not persisted]
  Buyer (DATA-ENT-008) *..1 ApplicationUser (DATA-ENT-010) [soft ref: IdentityGuid — aspirational]
```

---

*Domain Model — generated from ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline Foundation Layer).*
*All 13 DATA-ENT nodes, 4 DATA-AGG nodes, and 2 DATA-REPO nodes are covered.*
*Ubiquitous language glossary: 32 terms across 5 bounded contexts.*
*DDD aggregate boundaries, value objects, and cross-domain soft references fully documented.*
