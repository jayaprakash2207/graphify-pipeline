# 08 — Entity Relationship Diagram (ERD)
**eShopOnWeb — Forward Engineering Package**
**Generated:** 2026-06-30
**Pipeline Stage:** Foundation Synthesis Output (Layer 5 — Final)
**Single source of truth:** `ENTERPRISE_KNOWLEDGE_GRAPH.json`
**DA Agent 2 corrections applied:** DISC-002 (column lengths), DISC-003 (Buyer/PaymentMethod DORMANT), DISC-010 (HiLo sequences)

---

## 1. Scope and Conventions

This ERD covers all 13 `DATA-ENT` nodes from the eShopOnWeb Enterprise Knowledge Graph.

**Persisted entities (11):** CatalogItem, CatalogBrand, CatalogType, Basket, BasketItem, Order, OrderItem, ApplicationUser — plus owned value objects Address (inlined in Orders) and CatalogItemOrdered (inlined in OrderItems)

**DORMANT entities (2 — shown in separate sub-model):** Buyer (DATA-ENT-008), PaymentMethod (DATA-ENT-009) — confirmed not persisted (DISC-003 / BIZ-RULE-035)

**Abstract base (1 — excluded from diagram):** BaseEntity (DATA-ENT-013) — provides int Id to all entities; no table

**Aggregate boundaries:**
- `DATA-AGG-001` BasketAggregate: root = Basket; children = BasketItem
- `DATA-AGG-002` OrderAggregate: root = Order; children = OrderItem, Address (VO), CatalogItemOrdered (VO)
- `DATA-AGG-003` BuyerAggregate: DORMANT — root = Buyer; children = PaymentMethod
- `DATA-AGG-004` CatalogAggregate (informal): root = CatalogItem; references = CatalogBrand, CatalogType

**Relationship types in diagrams:**
- Solid lines (`--`) = enforced database FK
- Dotted lines (`..`) = soft reference (cross-DB, application-enforced only, NO DB FK)
- `||` = exactly one (mandatory)
- `o{` = zero-or-many
- `|{` = one-or-many

---

## 2. Primary ERD — All 13 Active Entities

### 2.1 Complete Mermaid ERD

```mermaid
erDiagram
    %% ===== CATALOG DOMAIN =====
    CatalogBrand ||--o{ CatalogItem : "groups (DATA-ENT-002 -> DATA-ENT-001)"
    CatalogType  ||--o{ CatalogItem : "classifies (DATA-ENT-003 -> DATA-ENT-001)"

    %% ===== BASKET DOMAIN =====
    Basket ||--|{ BasketItem : "contains (DATA-AGG-001)"
    BasketItem }o--|| CatalogItem : "references-price-lock (soft — no DB FK)"

    %% ===== ORDER DOMAIN =====
    Order ||--|{ OrderItem : "contains (DATA-AGG-002)"
    Order ||--|| Address : "ships-to (owned VO — inlined in Orders table)"
    OrderItem ||--|| CatalogItemOrdered : "snapshot (owned VO — inlined in OrderItems table)"

    %% ===== CROSS-DOMAIN SOFT REFS (no DB FK) =====
    ApplicationUser ||..o{ Basket : "owns via BuyerId (soft cross-DB ref)"
    ApplicationUser ||..o{ Order  : "placed by BuyerId (soft cross-DB ref)"

    %% ===== ENTITIES =====

    CatalogItem {
        int    Id              PK
        nvarchar50  Name
        nvarcharmax Description
        decimal1802 Price
        nvarcharmax PictureUri
        int    CatalogTypeId   FK
        int    CatalogBrandId  FK
        int    AvailableStock
        int    RestockThreshold
        int    MaxStockThreshold
        bit    OnReorder
    }

    CatalogBrand {
        int         Id    PK
        nvarchar100 Brand
    }

    CatalogType {
        int         Id   PK
        nvarchar100 Type
    }

    Basket {
        int          Id      PK
        nvarchar256  BuyerId "soft cross-DB ref to AspNetUsers.Id — PII-07"
    }

    BasketItem {
        int         Id            PK
        int         BasketId      FK
        int         CatalogItemId "soft ref — no DB FK"
        decimal1802 UnitPrice     "locked at add-time"
        int         Quantity
    }

    Order {
        int              Id                    PK
        nvarchar256      BuyerId               "soft cross-DB ref — PII-05"
        datetimeoffset   OrderDate
        nvarchar180      ShipToAddress_Street  "owned Address — PII-06"
        nvarchar100      ShipToAddress_City    "owned Address — PII-06"
        nvarchar60       ShipToAddress_State   "owned Address nullable"
        nvarchar90       ShipToAddress_Country "owned Address — PII-06"
        nvarchar18       ShipToAddress_ZipCode "owned Address — PII-06"
    }

    OrderItem {
        int         Id                          PK
        int         OrderId                     FK
        int         ItemOrdered_CatalogItemId   "snapshot — no FK"
        nvarchar50  ItemOrdered_ProductName     "purchase-time snapshot"
        nvarcharmax ItemOrdered_PictureUri      "purchase-time snapshot"
        decimal1802 UnitPrice
        int         Units
    }

    Address {
        nvarchar180 Street  "owned in Orders as ShipToAddress_Street"
        nvarchar100 City    "owned in Orders as ShipToAddress_City"
        nvarchar60  State   "nullable"
        nvarchar90  Country "owned in Orders as ShipToAddress_Country"
        nvarchar18  ZipCode "owned in Orders as ShipToAddress_ZipCode"
    }

    CatalogItemOrdered {
        int         CatalogItemId "snapshot of product ID at purchase"
        nvarchar50  ProductName   "snapshot of product name at purchase"
        nvarcharmax PictureUri    "snapshot of product image at purchase"
    }

    ApplicationUser {
        nvarchar450 Id            PK
        nvarchar256 UserName      "PII-02"
        nvarchar256 Email         "PII-01 HIGH"
        nvarcharmax PasswordHash  "PII-03 HIGH — PBKDF2/SHA-256"
        nvarcharmax PhoneNumber   "PII-04"
        bit         LockoutEnabled
        int         AccessFailedCount
    }
```

---

### 2.2 Cross-Database and Boundary Annotations

| Relationship | From → To | Enforcement | Risk / Note |
|---|---|---|---|
| Basket.BuyerId → AspNetUsers.Id | CatalogDB → IdentityDB | Application code only — NO DB FK | Orphan baskets if user deleted (PII-07); GDPR erasure gap (OQ-002) |
| Order.BuyerId → AspNetUsers.Id | CatalogDB → IdentityDB | Application code only — NO DB FK | Order history preserved post-deletion; may be intentional for financial records (OQ-003) |
| BasketItem.CatalogItemId → Catalog.Id | CatalogDB → CatalogDB | Application code only — NO DB FK | Orphan basket items if catalog item deleted |
| OrderItem.ItemOrdered_CatalogItemId → Catalog.Id | CatalogDB → CatalogDB | NO FK by design | Historical snapshot — intentional per BIZ-RULE-001 |
| Order.ShipToAddress_* | Owned type in Orders | EF owned entity — no separate table | Address columns inlined; PII-06 |
| OrderItem.ItemOrdered_* | Owned type in OrderItems | EF owned entity — no separate table | Snapshot columns inlined; BIZ-RULE-001 |

---

## 3. Aggregate Boundary Diagram

```mermaid
graph TB
    subgraph AGG001["DATA-AGG-001 BasketAggregate (Active)"]
        direction TB
        B["Basket\n(Aggregate Root)\nDATA-ENT-004"]
        BI["BasketItem\nDATA-ENT-005"]
        B --> BI
    end

    subgraph AGG002["DATA-AGG-002 OrderAggregate (Active — Immutable)"]
        direction TB
        O["Order\n(Aggregate Root)\nDATA-ENT-006"]
        OI["OrderItem\nDATA-ENT-007"]
        ADDR["Address\n(Value Object)\nDATA-ENT-011"]
        CIOS["CatalogItemOrdered\n(Value Object)\nDATA-ENT-012"]
        O --> OI
        O --> ADDR
        OI --> CIOS
    end

    subgraph AGG004["DATA-AGG-004 CatalogAggregate (Active)"]
        direction TB
        CI["CatalogItem\n(Aggregate Root)\nDATA-ENT-001"]
        CB["CatalogBrand\n(Reference)\nDATA-ENT-002"]
        CT["CatalogType\n(Reference)\nDATA-ENT-003"]
        CB --> CI
        CT --> CI
    end

    subgraph AGG003["DATA-AGG-003 BuyerAggregate (DORMANT — not persisted)"]
        direction TB
        BU["Buyer\nDATA-ENT-008\nNO DB TABLE"]
        PM["PaymentMethod\nDATA-ENT-009\nNO DB TABLE"]
        BU -.-> PM
    end

    subgraph IDENTITY["IdentityDatabase (AppIdentityDbContext)"]
        AU["ApplicationUser\nDATA-ENT-010\nAspNetUsers"]
    end

    AU -.->|"soft cross-DB BuyerId"| B
    AU -.->|"soft cross-DB BuyerId"| O
    BI -->|"soft cross-context CatalogItemId"| CI

    classDef dormant fill:#f5f5f5,stroke:#999,stroke-dasharray:5 5,color:#666
    class AGG003 dormant
    class BU,PM dormant
```

---

## 4. Data Flow Between Aggregates at Checkout

```mermaid
sequenceDiagram
    participant C as Customer<br/>(BIZ-ACT-002)
    participant BS as BasketAggregate<br/>DATA-AGG-001
    participant CI as CatalogItem<br/>DATA-ENT-001
    participant OS as OrderAggregate<br/>DATA-AGG-002

    Note over C,OS: BIZ-PROC-001 — Place an Order at Checkout

    C->>BS: Checkout request (BIZ-CAP-017)
    BS->>BS: Guard: basket not empty (BIZ-RULE-003, BIZ-RULE-019)
    loop For each BasketItem
        BS->>CI: Read product name + picture URI
        CI-->>OS: CatalogItemOrdered snapshot created<br/>(ItemOrdered_ProductName, ItemOrdered_PictureUri,<br/>ItemOrdered_CatalogItemId)
    end
    Note over OS: BIZ-RULE-001: snapshot immune to<br/>future catalog changes
    BS->>OS: UnitPrice transferred from BasketItem.UnitPrice
    OS->>OS: Order created with BuyerId + Address + OrderItems
    BS->>BS: Basket permanently deleted (BIZ-RULE-003)
    OS-->>C: Order confirmation
```

**Price lock chain:**
1. `CatalogItem.Price` → read when item added to basket
2. `BasketItem.UnitPrice` → locked at basket-add time (BIZ-RULE-010)
3. `OrderItem.UnitPrice` → copied from BasketItem.UnitPrice at checkout
4. Future `CatalogItem.Price` changes → have NO effect on existing basket items or orders

---

## 5. Dormant Sub-Model — BuyerAggregate

> **DORMANT / NOT PERSISTED (DISC-003 / BIZ-RULE-035)**
> Buyer (DATA-ENT-008) and PaymentMethod (DATA-ENT-009) have no DbSet registration in CatalogContext.
> No service layer creates or queries them. Documented here for future payment integration planning (AO-05).

```mermaid
erDiagram
    %% DORMANT ONLY — not in CatalogContext; no service layer
    %% Activate as part of AO-05 payment integration

    Buyer ||--o{ PaymentMethod : "may have (DATA-AGG-003 — DORMANT)"

    Buyer {
        string IdentityGuid "links to Order.BuyerId by string convention — no FK"
        string status       "DORMANT — no DB table; no service layer"
    }

    PaymentMethod {
        string Alias    "nullable — human-readable label"
        string CardId   "PCI TOKEN ONLY — never raw card data (BIZ-RULE-034)"
        string Last4    "last 4 digits only (BIZ-RULE-034)"
        string status   "DORMANT — no DB table"
    }
```

**PCI Note (BIZ-RULE-034):** When PaymentMethod is eventually activated (AO-05), `CardId` must store ONLY a PCI-compliant payment processor token (e.g. Stripe token). Raw card numbers, CVV, expiry dates, or full PANs must NEVER be stored. The existing source code contains an explicit comment referencing Stripe as the intended processor.

**Payment processor decision required (OQ-008):** Stripe vs Braintree vs other — unresolved. PaymentMethod.CardId token format depends on this choice.

---

## 6. Relationship Inventory

All relationships from the Enterprise Knowledge Graph:

| Relationship | From Entity | To Entity | Cardinality | FK / Mechanism | Status |
|---|---|---|---|---|---|
| Data-ENT-001 → CatalogBrand | CatalogItem | CatalogBrand | Many → One | CatalogItem.CatalogBrandId FK → CatalogBrands.Id | Active |
| Data-ENT-001 → CatalogType | CatalogItem | CatalogType | Many → One | CatalogItem.CatalogTypeId FK → CatalogTypes.Id | Active |
| Basket contains BasketItem | Basket | BasketItem | One → Many | BasketItem.BasketId FK → Baskets.Id (CASCADE) | Active |
| BasketItem references CatalogItem | BasketItem | CatalogItem | Many → One | Soft ref — NO DB FK | Active |
| Order contains OrderItem | Order | OrderItem | One → Many | OrderItem.OrderId FK → Orders.Id (CASCADE) | Active |
| OrderItem owns CatalogItemOrdered | OrderItem | CatalogItemOrdered | One → One | Owned type (ItemOrdered_*) — snapshot, NO FK | Active |
| Order ships to Address | Order | Address | One → One | Owned type (ShipToAddress_*) — inlined | Active |
| Basket owned by ApplicationUser | Basket | ApplicationUser | Many → One | Basket.BuyerId soft cross-DB — NO FK | Active |
| Order placed by ApplicationUser | Order | ApplicationUser | Many → One | Order.BuyerId soft cross-DB — NO FK | Active |
| Basket converts to Order | Basket | Order | One → One | Process-level at checkout; basket deleted after (BIZ-RULE-003) | Active |
| Buyer owns PaymentMethod | Buyer | PaymentMethod | One → Many | NO FK — DORMANT (DATA-AGG-003) | DORMANT |

---

## 7. Entity-to-Table Mapping

| Entity (DATA-ENT) | Table | Database | Key Type | Aggregate |
|---|---|---|---|---|
| DATA-ENT-001 CatalogItem | Catalog | CatalogDatabase | HiLo `catalog_hilo` | DATA-AGG-004 (root) |
| DATA-ENT-002 CatalogBrand | CatalogBrands | CatalogDatabase | HiLo `catalog_brand_hilo` | DATA-AGG-004 (reference) |
| DATA-ENT-003 CatalogType | CatalogTypes | CatalogDatabase | HiLo `catalog_type_hilo` | DATA-AGG-004 (reference) |
| DATA-ENT-004 Basket | Baskets | CatalogDatabase | IDENTITY | DATA-AGG-001 (root) |
| DATA-ENT-005 BasketItem | BasketItems | CatalogDatabase | IDENTITY | DATA-AGG-001 (member) |
| DATA-ENT-006 Order | Orders | CatalogDatabase | IDENTITY | DATA-AGG-002 (root) |
| DATA-ENT-007 OrderItem | OrderItems | CatalogDatabase | IDENTITY | DATA-AGG-002 (member) |
| DATA-ENT-008 Buyer | NONE — not persisted | — | — | DATA-AGG-003 (DORMANT) |
| DATA-ENT-009 PaymentMethod | NONE — not persisted | — | — | DATA-AGG-003 (DORMANT) |
| DATA-ENT-010 ApplicationUser | AspNetUsers | IdentityDatabase | GUID string | Identity (standalone) |
| DATA-ENT-011 Address | Orders (inlined ShipToAddress_*) | CatalogDatabase | Owned VO — no PK | DATA-AGG-002 (VO) |
| DATA-ENT-012 CatalogItemOrdered | OrderItems (inlined ItemOrdered_*) | CatalogDatabase | Owned VO — no PK | DATA-AGG-002 (VO) |
| DATA-ENT-013 BaseEntity | NONE — abstract | — | — | Shared kernel |

---

## 8. PII Overlay

Entities and columns containing PII data, from DA:pii-inventory.json:

```mermaid
erDiagram
    ApplicationUser {
        nvarchar256 Email         "PII-01 HIGH"
        nvarchar256 UserName      "PII-02 MEDIUM"
        nvarcharmax PasswordHash  "PII-03 HIGH"
        nvarcharmax PhoneNumber   "PII-04 MEDIUM"
    }

    Order {
        nvarchar256 BuyerId               "PII-05 MEDIUM/HIGH"
        nvarchar180 ShipToAddress_Street  "PII-06 HIGH"
        nvarchar100 ShipToAddress_City    "PII-06 HIGH"
        nvarchar60  ShipToAddress_State   "PII-06 HIGH"
        nvarchar90  ShipToAddress_Country "PII-06 HIGH"
        nvarchar18  ShipToAddress_ZipCode "PII-06 HIGH"
    }

    Basket {
        nvarchar256 BuyerId "PII-07 LOW/MEDIUM"
    }

    AspNetUserTokens {
        nvarcharmax Value "PII-08 HIGH — auth token"
    }
```

**GDPR considerations:**
- Right to erasure applies to all HIGH sensitivity PII fields
- Cross-DB soft references (BuyerId) mean user deletion does NOT cascade to orders or baskets
- Order records likely retained for financial/legal reasons even after user deletion (OQ-003)
- No GDPR erasure workflow found in codebase — significant compliance gap (OQ-002 / ASMP-002)

---

*ERD — all 13 entities from ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*DA Agent 2 confirmed field types and key strategies applied.*
*Dormant BuyerAggregate documented separately — not part of current schema.*
