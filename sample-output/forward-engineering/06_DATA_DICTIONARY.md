# 06 — Data Dictionary
**eShopOnWeb — Forward Engineering Package**
**Generated:** 2026-06-30
**Pipeline Stage:** Foundation Synthesis Output (Layer 5 — Final)
**Single source of truth:** `ENTERPRISE_KNOWLEDGE_GRAPH.json` (Foundation layer)
**DA Agent 2 corrections applied:** DISC-002 (column lengths), DISC-010 (HiLo sequences), DISC-003 (Buyer/PaymentMethod DORMANT)

---

## Purpose and Scope

This data dictionary covers all 13 `DATA-ENT` nodes extracted from the eShopOnWeb Enterprise Knowledge Graph. Every field, type, constraint, PII flag, and ownership statement below is traced to a graph node ID. No fields or types have been invented.

**DA Agent 2 corrected field types are used throughout.** DA Agent 1 reported several columns as `nvarchar(max)` and IDs as `IDENTITY`; DA Agent 2 corrected these by reading `IEntityTypeConfiguration` source files directly (DISC-002, DISC-010).

**Status flags honoured:**
- `DATA-ENT-008` Buyer — DORMANT (not in CatalogContext; no service layer) [DISC-003, BIZ-RULE-035]
- `DATA-ENT-009` PaymentMethod — DORMANT (not in CatalogContext; PCI comment) [BIZ-RULE-034]
- `DATA-ENT-013` BaseEntity — abstract base class, no table

**PII items confirmed (8 total):** PII-01 through PII-08 from `data.pii_summary`

---

## How to Read This Dictionary

| Column | Meaning |
|---|---|
| Field Name | Exact .NET property name and database column name |
| SQL Server Type | DA Agent 2 confirmed SQL Server physical type (nvarchar lengths from EF config files) |
| Nullable | YES = allows NULL; NO = NOT NULL constraint |
| Constraints | PK, FK, UNIQUE, CHECK constraints, EF owned entity config |
| PII | PII item ID if field is PII-bearing; blank = no PII |
| Notes | Business rule references, key generation strategy, cross-domain notes |

---

## DATABASE 1: CatalogDatabase (DATA-REPO-001)
**EF Context:** `CatalogContext` | **Connection key:** `CatalogConnection`
**Tables:** Catalog, CatalogBrands, CatalogTypes, Baskets, BasketItems, Orders, OrderItems

---

### DATA-ENT-001 — CatalogItem
**Business Concept:** Product | **Domain:** Catalog | **DB Table:** `Catalog`
**Aggregate:** CatalogAggregate (DATA-AGG-004) — informal root
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; DA:schema-catalogue.json; EF CatalogItemConfiguration.cs
**Key generation:** HiLo sequence `catalog_hilo` (DISC-010 — corrected from IDENTITY)
**Shared by:** Catalog, Basket (price read at add-time), Order (snapshot at checkout), PublicApi, BlazorAdmin

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; HiLo sequence `catalog_hilo` | — | BIZ-RULE-014: guard clauses enforced at construction; DISC-010 |
| Name | nvarchar(50) | NO | NOT NULL | — | BIZ-RULE-020: must be unique; BIZ-RULE-022: must not be empty; DISC-002 |
| Description | nvarchar(max) | YES | | — | BIZ-RULE-022: must not be empty at creation |
| Price | decimal(18,2) | NO | CHECK Price > 0 | — | BIZ-RULE-021: Guard.Against.NegativeOrZero; selling price — distinct from BasketItem.UnitPrice |
| PictureUri | nvarchar(max) | YES | | — | BIZ-RULE-023: default placeholder on creation; admin upload permanently disabled |
| CatalogTypeId | INT | NO | FK → CatalogTypes.Id (RESTRICT) | — | DATA-ENT-003; required |
| CatalogBrandId | INT | NO | FK → CatalogBrands.Id (RESTRICT) | — | DATA-ENT-002; required |
| AvailableStock | INT | NO | | — | Stock management field |
| RestockThreshold | INT | NO | | — | Stock level triggering reorder |
| MaxStockThreshold | INT | NO | | — | Maximum stock level |
| OnReorder | BIT | NO | | — | Whether item is flagged for reorder |

**Index:** `IX_Catalog_CatalogBrandId`, `IX_Catalog_CatalogTypeId`

---

### DATA-ENT-002 — CatalogBrand
**Business Concept:** Brand | **Domain:** Catalog | **DB Table:** `CatalogBrands`
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; DA:review-summary CORRECTED-1; EF CatalogBrandConfiguration.cs
**Key generation:** HiLo sequence `catalog_brand_hilo` (DISC-010)
**Seed data:** 5 brands seeded on startup (BIZ-RULE-031)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; HiLo sequence `catalog_brand_hilo` | — | DISC-010 — confirmed HiLo, not IDENTITY |
| Brand | nvarchar(100) | NO | NOT NULL | — | DISC-002: nvarchar(100) confirmed — DA Agent 1 incorrectly reported nvarchar(max) |

---

### DATA-ENT-003 — CatalogType
**Business Concept:** Category (Product Type) | **Domain:** Catalog | **DB Table:** `CatalogTypes`
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; DA:review-summary CORRECTED-1; EF CatalogTypeConfiguration.cs
**Key generation:** HiLo sequence `catalog_type_hilo` (DISC-010)
**Seed data:** 4 types seeded on startup (BIZ-RULE-031)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; HiLo sequence `catalog_type_hilo` | — | DISC-010 — confirmed HiLo, not IDENTITY |
| Type | nvarchar(100) | NO | NOT NULL | — | DISC-002: nvarchar(100) confirmed — DA Agent 1 incorrectly reported nvarchar(max) |

---

### DATA-ENT-004 — Basket
**Business Concept:** Shopping Basket | **Domain:** Basket | **DB Table:** `Baskets`
**Aggregate:** BasketAggregate root (DATA-AGG-001)
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; BA:05_data_model.md
**Key generation:** IDENTITY (standard)
**Lifecycle:** Created on first add; deleted after order placed (BIZ-RULE-003) or on basket transfer (BIZ-RULE-002)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; IDENTITY | — | Standard auto-increment; cascade delete to BasketItems |
| BuyerId | nvarchar(256) | NO | NOT NULL; IX_Baskets_BuyerId | PII-07 | Cross-DB soft ref to AspNetUsers.Id; GUID for anonymous, email/username for authenticated; ASMP-001: likely email (unit test evidence) |

**Index:** `IX_Baskets_BuyerId`
**Cascade:** DELETE CASCADE to BasketItems (EF config)
**PII note (PII-07):** BuyerId sensitivity LOW but escalates to MEDIUM/HIGH if BuyerId = email (OQ-001)

---

### DATA-ENT-005 — BasketItem
**Business Concept:** Basket Line Item | **Domain:** Basket | **DB Table:** `BasketItems`
**Aggregate:** Member of BasketAggregate (DATA-AGG-001)
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; BA:05_data_model.md
**Key generation:** IDENTITY (standard)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; IDENTITY | — | |
| BasketId | INT | NO | FK → Baskets.Id (CASCADE DELETE) | — | Parent aggregate; intra-aggregate FK |
| CatalogItemId | INT | NO | NOT NULL | — | Soft reference — no DB FK confirmed; cross-context to DATA-ENT-001 |
| UnitPrice | decimal(18,2) | NO | NOT NULL | — | Price LOCKED at basket-add time — does NOT update when catalog price changes; BIZ-RULE-010 |
| Quantity | INT | NO | CHECK Quantity >= 0 | — | BIZ-RULE-004: defaults to 1 on add; DISC-007: auto-merge increments quantity on duplicate |

**Index:** `IX_BasketItems_BasketId`
**Business rule note:** When same CatalogItemId already in basket, AddItem() increments Quantity — does NOT throw DuplicateException (DISC-007, BIZ-RULE-004)

---

### DATA-ENT-006 — Order
**Business Concept:** Order (Confirmed Purchase) | **Domain:** Order | **DB Table:** `Orders`
**Aggregate:** OrderAggregate root (DATA-AGG-002)
**Status:** Active — Immutable after creation | **Confidence:** HIGH
**Evidence:** DA:erd.md; DA:data-dictionary.md; BA:05_data_model.md; BR-12
**Key generation:** IDENTITY (standard)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; IDENTITY | — | |
| BuyerId | nvarchar(256) | NO | NOT NULL; IX_Orders_BuyerId | PII-05 | Cross-DB soft ref to AspNetUsers.Id; MEDIUM sensitivity (escalates to HIGH if email — OQ-001) |
| OrderDate | datetimeoffset | NO | NOT NULL; auto-set at creation | — | Creation timestamp; immutable |
| ShipToAddress_Street | nvarchar(180) | NO | NOT NULL | PII-06 | Owned entity Address (DATA-ENT-011); BIZ-RULE-033 max 180 chars |
| ShipToAddress_City | nvarchar(100) | NO | NOT NULL | PII-06 | Owned entity Address; BIZ-RULE-033 max 100 chars |
| ShipToAddress_State | nvarchar(60) | YES | nullable | PII-06 | Owned entity Address; BIZ-RULE-033 max 60 chars; OPTIONAL |
| ShipToAddress_Country | nvarchar(90) | NO | NOT NULL | PII-06 | Owned entity Address; BIZ-RULE-033 max 90 chars |
| ShipToAddress_ZipCode | nvarchar(18) | NO | NOT NULL | PII-06 | Owned entity Address; BIZ-RULE-033 max 18 chars |

**Index:** `IX_Orders_BuyerId`
**PII note (PII-05):** BuyerId — MEDIUM sensitivity, escalates to HIGH if BuyerId stores email (OQ-001)
**PII note (PII-06):** ShipToAddress_* — HIGH sensitivity (full physical address); right to erasure applies (GDPR)
**Immutability:** BIZ-RULE-012 — no status field; orders cannot be updated, cancelled, or progressed after creation
**CRITICAL GAP (BIZ-RULE-015 / AO-01):** All current orders have hardcoded shipping address "123 Main St., Kent, OH, United States, 44240" — user input not collected. MUST be resolved before production deployment.

---

### DATA-ENT-007 — OrderItem
**Business Concept:** Order Line Item | **Domain:** Order | **DB Table:** `OrderItems`
**Aggregate:** Member of OrderAggregate (DATA-AGG-002)
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md; BA:05_data_model.md
**Key generation:** IDENTITY (standard)

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | INT | NO | PK; IDENTITY | — | |
| OrderId | INT | NO | FK → Orders.Id (CASCADE DELETE) | — | Parent aggregate; intra-aggregate FK |
| ItemOrdered_CatalogItemId | INT | NO | NOT NULL | — | Owned value object CatalogItemOrdered (DATA-ENT-012); snapshot only — intentionally NO DB FK to Catalog table |
| ItemOrdered_ProductName | nvarchar(50) | NO | NOT NULL | — | Purchase-time snapshot; immutable; BIZ-RULE-001 |
| ItemOrdered_PictureUri | nvarchar(max) | YES | | — | Purchase-time snapshot; immune to future catalogue changes |
| UnitPrice | decimal(18,2) | NO | NOT NULL; CHECK UnitPrice >= 0 | — | Price captured at order time — may differ from current CatalogItem.Price |
| Units | INT | NO | NOT NULL; CHECK Units >= 1 | — | Quantity ordered |

**Index:** `IX_OrderItems_OrderId`
**Snapshot pattern (BIZ-RULE-001):** ItemOrdered_* fields are frozen at checkout. No FK to Catalog intentional — order history survives catalog item deletion.

---

### DATA-ENT-008 — Buyer  *(DORMANT — not persisted)*
**Business Concept:** Buyer Profile | **Domain:** Buyer | **DB Table:** NONE
**Aggregate:** BuyerAggregate root (DATA-AGG-003) — DORMANT
**Status:** DORMANT | **Confidence:** HIGH
**Evidence:** DA:erd.md CONFIRMED DEAD — not registered in CatalogContext; BA:05_data_model.md; BIZ-RULE-035

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| IdentityGuid | nvarchar (string) | NO | Links to Order.BuyerId by string value convention — no DB FK | — | String value convention only; no persisted table |

**DORMANT status (DISC-003 / BIZ-RULE-035):** Buyer aggregate is structurally defined in source code but has NO DbSet registration in CatalogContext. No service layer creates or queries it. Do NOT add to DbContext without implementing full payment integration (AO-05).

---

### DATA-ENT-009 — PaymentMethod  *(DORMANT — not persisted)*
**Business Concept:** Payment Method Record | **Domain:** Buyer | **DB Table:** NONE
**Aggregate:** Member of BuyerAggregate (DATA-AGG-003) — DORMANT
**Status:** DORMANT | **Confidence:** HIGH
**Evidence:** DA:erd.md CONFIRMED DEAD; BIZ-RULE-034; PaymentMethod.cs:7 explicit PCI comment referencing Stripe

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Alias | nvarchar (string?) | YES | | — | Human-readable label for payment method |
| CardId | nvarchar (string?) | YES | | — | PCI-COMPLIANT TOKEN ONLY — never store raw card data (BIZ-RULE-034; explicit source code comment) |
| Last4 | nvarchar (string?) | YES | | — | Last 4 digits of card only (BIZ-RULE-034) |

**PCI NOTE (BIZ-RULE-034):** CardId field must ONLY ever store a PCI-compliant payment token (e.g. Stripe token). Raw card numbers, CVV, or full PANs must NEVER be stored. Existing source code has an explicit comment referencing Stripe. Payment processor decision required before activating (OQ-008).

---

### DATA-ENT-011 — Address  *(Owned Value Object — no separate table)*
**Business Concept:** Shipping Address | **Domain:** Order | **DB Table:** Orders (columns inlined as ShipToAddress_*)
**Aggregate:** Member of OrderAggregate (DATA-AGG-002) — value object
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md value object; BA:05_data_model.md owned entity; EF OrderConfiguration.cs

This is an EF Core Owned Entity. All columns are inlined into the Orders table with the `ShipToAddress_` prefix. There is no separate Address table.

| Field Name (VO property) | Inlined Column | SQL Server Type | Nullable | PII | Source Constraint |
|---|---|---|---|---|---|
| Street | ShipToAddress_Street | nvarchar(180) | NO | PII-06 | BIZ-RULE-033 |
| City | ShipToAddress_City | nvarchar(100) | NO | PII-06 | BIZ-RULE-033 |
| State | ShipToAddress_State | nvarchar(60) | YES | PII-06 | BIZ-RULE-033 — OPTIONAL |
| Country | ShipToAddress_Country | nvarchar(90) | NO | PII-06 | BIZ-RULE-033 |
| ZipCode | ShipToAddress_ZipCode | nvarchar(18) | NO | PII-06 | BIZ-RULE-033 |

**EF Core configuration:** `.OwnsOne(o => o.ShipToAddress, a => { a.WithOwner(); a.Property(a => a.Street).HasMaxLength(180).IsRequired(); ... })`

---

### DATA-ENT-012 — CatalogItemOrdered  *(Owned Value Object — no separate table)*
**Business Concept:** Purchase-Time Product Snapshot | **Domain:** Order | **DB Table:** OrderItems (columns inlined as ItemOrdered_*)
**Aggregate:** Member of OrderAggregate (DATA-AGG-002) — value object
**Status:** Active | **Confidence:** HIGH
**Evidence:** DA:erd.md value object; BA:05_data_model.md snapshot pattern; BIZ-RULE-001

This is an EF Core Owned Entity. All columns are inlined into the OrderItems table with the `ItemOrdered_` prefix. Immutable — frozen at checkout time.

| Field Name (VO property) | Inlined Column | SQL Server Type | Nullable | PII | Notes |
|---|---|---|---|---|---|
| CatalogItemId | ItemOrdered_CatalogItemId | INT | NO | — | Snapshot reference — intentionally NO FK constraint (BIZ-RULE-001) |
| ProductName | ItemOrdered_ProductName | nvarchar(50) | NO | — | Product name at time of purchase — immune to future catalog changes |
| PictureUri | ItemOrdered_PictureUri | nvarchar(max) | YES | — | Product image URI at time of purchase |

**Immutability (BIZ-RULE-001):** No setters after construction. Order history accurate even if catalog item is later renamed, updated, or deleted.
**No FK by design:** ItemOrdered_CatalogItemId has no FK constraint to the Catalog table — this is intentional snapshot denormalization, not an oversight.

---

### DATA-ENT-013 — BaseEntity  *(Abstract base class — no table)*
**Business Concept:** Shared Kernel Base | **Domain:** SharedKernel | **DB Table:** NONE (abstract)
**Status:** Active (structural only) | **Confidence:** HIGH
**Evidence:** BA:05_data_model.md — parent of all domain entities

| Field Name | SQL Server Type | Nullable | Constraints | Notes |
|---|---|---|---|---|
| Id | INT | NO | PK on derived entity | Provides integer surrogate key to all domain entities that inherit BaseEntity |

**No table:** BaseEntity is an abstract C# class. The `Id` property is realized as the primary key column on each concrete persisted entity that inherits it.

---

## DATABASE 2: IdentityDatabase (DATA-REPO-002)
**EF Context:** `AppIdentityDbContext` | **Connection key:** `IdentityConnection`
**Framework:** ASP.NET Core Identity (standard schema)
**Tables:** AspNetUsers, AspNetRoles, AspNetUserRoles, AspNetUserClaims, AspNetRoleClaims, AspNetUserLogins, AspNetUserTokens

---

### DATA-ENT-010 — ApplicationUser
**Business Concept:** Shopper / Buyer Identity | **Domain:** Identity | **DB Table:** `AspNetUsers`
**Status:** Active | **Confidence:** HIGH
**Evidence:** BA:05_data_model.md; DA:pii-inventory.json PII-01 through PII-04

| Field Name | SQL Server Type | Nullable | Constraints | PII | Notes |
|---|---|---|---|---|---|
| Id | nvarchar(450) | NO | PK (GUID string) | — | Standard ASP.NET Identity string key |
| UserName | nvarchar(256) | YES | UNIQUE (NormalizedUserName) | PII-02 | MEDIUM sensitivity; typically equals Email (ASMP-001) |
| NormalizedUserName | nvarchar(256) | YES | UNIQUE | PII-02 | Uppercase UserName for case-insensitive lookup |
| Email | nvarchar(256) | YES | | PII-01 | HIGH sensitivity; right to erasure applies (GDPR) |
| NormalizedEmail | nvarchar(256) | YES | UNIQUE index | PII-01 | Uppercase Email for case-insensitive lookup |
| EmailConfirmed | bit | NO | DEFAULT 0 | — | BIZ-RULE-027: NOT enforced — accounts activated immediately on registration (compliance gap) |
| PasswordHash | nvarchar(max) | YES | | PII-03 | PBKDF2/SHA-256 — not reversible; HIGH sensitivity; must never be logged |
| PhoneNumber | nvarchar(max) | YES | | PII-04 | MEDIUM sensitivity; optional |
| LockoutEnabled | bit | NO | DEFAULT 1 | — | BIZ-RULE-025: account lockout enabled |
| AccessFailedCount | int | NO | DEFAULT 0 | — | BIZ-RULE-025: failed login counter |
| LockoutEnd | datetimeoffset | YES | | — | Lockout expiry; null = not locked |
| SecurityStamp | nvarchar(max) | YES | | — | Security invalidation stamp |
| ConcurrencyStamp | nvarchar(max) | YES | | — | Optimistic concurrency token |
| TwoFactorEnabled | bit | NO | DEFAULT 0 | — | |
| PhoneNumberConfirmed | bit | NO | DEFAULT 0 | — | |

**Seeded accounts (BIZ-RULE-013 / BIZ-RULE-029 — CRITICAL):**
- `admin@microsoft.com` — Administrators role; password `Pass@word1` hardcoded in AuthorizationConstants.cs:8
- `demouser@microsoft.com` — standard user; same hardcoded password
- **MUST NOT use in production — explicit TODO comment in source code (BIZ-RULE-029 / AO-03)**

**PII summary for AspNetUsers:**
- PII-01 (Email) — HIGH sensitivity
- PII-02 (UserName) — MEDIUM sensitivity
- PII-03 (PasswordHash) — HIGH sensitivity
- PII-04 (PhoneNumber) — MEDIUM sensitivity
- PII-08 (AspNetUserTokens.Value) — HIGH sensitivity (auth token)

---

## PII Summary

| PII-ID | Table | Column(s) | Sensitivity | GDPR Concern | Evidence |
|---|---|---|---|---|---|
| PII-01 | AspNetUsers | Email | HIGH | Core PII; right to erasure applies | DA:pii-inventory.json |
| PII-02 | AspNetUsers | UserName | MEDIUM | Likely = email (ASMP-001); right to erasure | DA:pii-inventory.json |
| PII-03 | AspNetUsers | PasswordHash | HIGH | Not reversible but must not be logged or leaked | DA:pii-inventory.json |
| PII-04 | AspNetUsers | PhoneNumber | MEDIUM | Optional; right to erasure if populated | DA:pii-inventory.json |
| PII-05 | Orders | BuyerId | MEDIUM → HIGH | Escalates to HIGH if BuyerId = email (OQ-001); post-deletion retention risk | DA:pii-inventory.json |
| PII-06 | Orders | ShipToAddress_Street, _City, _State, _Country, _ZipCode | HIGH | Full physical address; right to erasure applies | DA:pii-inventory.json |
| PII-07 | Baskets | BuyerId | LOW → MEDIUM/HIGH | Orphan baskets on user deletion (OQ-001) | DA:pii-inventory.json |
| PII-08 | AspNetUserTokens | Value | HIGH | Auth token; right to erasure applies | DA:pii-inventory.json |

**Total confirmed PII items:** 8 (PII-01 through PII-08)

**Open question affecting PII classification (OQ-001):** Does BuyerId in Basket and Order store the user's email address or their AspNetUsers.Id GUID? Unit test `TransferBasket.cs` uses `testuser@microsoft.com` as BuyerId, suggesting it is the email. If confirmed, PII-05 and PII-07 must be elevated to HIGH sensitivity. This has significant GDPR erasure implications.

---

## Cross-Database Soft References (No FK Enforcement)

| From | To | Enforcement | Risk |
|---|---|---|---|
| CatalogDatabase.Baskets.BuyerId | IdentityDatabase.AspNetUsers.Id | Application code only | Orphan baskets accumulate if user deleted; GDPR erasure gap (OQ-002) |
| CatalogDatabase.Orders.BuyerId | IdentityDatabase.AspNetUsers.Id | Application code only | Order history preserved after user deletion — may be intentional for financial records (OQ-003) |
| CatalogDatabase.BasketItems.CatalogItemId | CatalogDatabase.Catalog.Id | No confirmed DB FK | Orphan basket items if catalog item deleted |
| CatalogDatabase.OrderItems.ItemOrdered_CatalogItemId | CatalogDatabase.Catalog.Id | No DB FK — snapshot pattern intentional | Mitigated — ProductName and PictureUri captured at order time |

---

## DA Agent 2 Corrections Applied (DISC-002, DISC-010)

The following corrections override DA Agent 1 output and are incorporated in this data dictionary:

| Correction | Field / Entity | Agent 1 (WRONG) | Agent 2 (CONFIRMED) | Source |
|---|---|---|---|---|
| DISC-001 | CatalogBrand.Brand | nvarchar(max) | nvarchar(100) | CatalogBrandConfiguration.cs |
| DISC-002 | CatalogType.Type | nvarchar(max) | nvarchar(100) | CatalogTypeConfiguration.cs |
| DISC-003 | CatalogItem.Name | nvarchar(max) | nvarchar(50) | CatalogItemConfiguration.cs |
| DISC-004 | OrderItem.ItemOrdered_ProductName | nvarchar(max) | nvarchar(50) | OrderItemConfiguration.cs |
| DISC-005 | CatalogItem.Id key strategy | IDENTITY | HiLo `catalog_hilo` | CatalogItemConfiguration.cs |
| DISC-006 | CatalogBrand.Id key strategy | IDENTITY | HiLo `catalog_brand_hilo` | CatalogBrandConfiguration.cs |
| DISC-007 | CatalogType.Id key strategy | IDENTITY | HiLo `catalog_type_hilo` | CatalogTypeConfiguration.cs |
| DISC-008 | Buyer/PaymentMethod status | "Active domain entities" | DORMANT — not in CatalogContext | DA:erd.md direct inspection |
| DISC-009 | BlazorAdmin cache technology | Server-side in-process | browser localStorage (Blazored.LocalStorage) | CachedCatalogItemServiceDecorator.cs |

---

*Data Dictionary — 13 entities from ENTERPRISE_KNOWLEDGE_GRAPH.json. Every field traced to DATA-ENT node IDs.*
*DA Agent 2 corrected types used throughout. PII items PII-01 through PII-08 confirmed and flagged.*
*Dormant entities (Buyer, PaymentMethod) documented but explicitly excluded from persistence spec.*
