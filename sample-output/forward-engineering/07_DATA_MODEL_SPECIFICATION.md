# 07 — Data Model Specification
**eShopOnWeb — Forward Engineering Package**
**Generated:** 2026-06-30
**Pipeline Stage:** Foundation Synthesis Output (Layer 5 — Final)
**Single source of truth:** `ENTERPRISE_KNOWLEDGE_GRAPH.json`
**Target database:** SQL Server (Azure SQL, LocalDB for dev)
**DA Agent 2 corrections applied:** DISC-002 (column lengths), DISC-010 (HiLo sequences)

---

## 0. Purpose and Scope

This document specifies the physical data model for SQL Server targeting eShopOnWeb's two databases:

1. **CatalogDatabase** — Products, baskets, and orders (`CatalogContext`)
2. **IdentityDatabase** — Users, roles, authentication (`AppIdentityDbContext`)

Coverage:
- Physical table definitions (all 7 CatalogDatabase tables)
- Column types, lengths, nullability, and constraints (DA Agent 2 confirmed)
- Primary keys, foreign keys, and indexes
- EF Core configuration (Fluent API, HiLo sequences, owned entities)
- Migration strategy and dependency order

**Dormant entities excluded:** Buyer (DATA-ENT-008) and PaymentMethod (DATA-ENT-009) are DORMANT (DISC-003 / BIZ-RULE-035) and are not included in any table spec or EF configuration.

---

## 1. Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Table | PascalCase (EF default from entity name) | `Catalog`, `CatalogBrands`, `Baskets` |
| Column | PascalCase (.NET property names) | `CatalogBrandId`, `UnitPrice` |
| PK | `Id` | `Id INT NOT NULL` |
| FK column | `<Target>Id` | `CatalogBrandId`, `OrderId` |
| Owned VO column | `<OwnerField>_<Property>` | `ShipToAddress_Street`, `ItemOrdered_ProductName` |
| Index | `IX_<Table>_<Column>` | `IX_Catalog_CatalogBrandId` |
| FK constraint | `FK_<Child>_<Parent>` | `FK_BasketItems_Baskets` |
| Sequence (HiLo) | `<EntityName>_hilo` | `catalog_hilo`, `catalog_brand_hilo` |
| EF Config class | `<Entity>Configuration` | `CatalogItemConfiguration` |

---

## 2. CatalogDatabase — Physical Table Specifications

### 2.1 `CatalogBrands` — DATA-ENT-002

**EF Entity:** `CatalogBrand` | **Key:** HiLo `catalog_brand_hilo` (DISC-010)

```sql
CREATE TABLE [CatalogBrands] (
    [Id]    INT           NOT NULL,
    [Brand] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_CatalogBrands] PRIMARY KEY ([Id])
);
```

| Column | SQL Server Type | Nullable | Default | Notes |
|---|---|---|---|---|
| Id | INT | NOT NULL | — | HiLo sequence `catalog_brand_hilo`; corrected from IDENTITY (DISC-010) |
| Brand | NVARCHAR(100) | NOT NULL | — | Corrected from nvarchar(max) — DA Agent 2 (DISC-002) |

**HiLo Sequence:**
```sql
CREATE SEQUENCE [catalog_brand_hilo]
    START WITH 1
    INCREMENT BY 10;
```

---

### 2.2 `CatalogTypes` — DATA-ENT-003

**EF Entity:** `CatalogType` | **Key:** HiLo `catalog_type_hilo` (DISC-010)

```sql
CREATE TABLE [CatalogTypes] (
    [Id]   INT           NOT NULL,
    [Type] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_CatalogTypes] PRIMARY KEY ([Id])
);
```

| Column | SQL Server Type | Nullable | Default | Notes |
|---|---|---|---|---|
| Id | INT | NOT NULL | — | HiLo sequence `catalog_type_hilo`; corrected from IDENTITY (DISC-010) |
| Type | NVARCHAR(100) | NOT NULL | — | Corrected from nvarchar(max) — DA Agent 2 (DISC-002) |

**HiLo Sequence:**
```sql
CREATE SEQUENCE [catalog_type_hilo]
    START WITH 1
    INCREMENT BY 10;
```

---

### 2.3 `Catalog` — DATA-ENT-001

**EF Entity:** `CatalogItem` | **Key:** HiLo `catalog_hilo` (DISC-010)
**Table name:** `Catalog` (EF config sets explicit table name via `.ToTable("Catalog")`)

```sql
CREATE TABLE [Catalog] (
    [Id]                INT              NOT NULL,
    [Name]              NVARCHAR(50)     NOT NULL,
    [Description]       NVARCHAR(MAX)    NOT NULL,
    [Price]             DECIMAL(18,2)    NOT NULL,
    [PictureUri]        NVARCHAR(MAX)    NULL,
    [CatalogTypeId]     INT              NOT NULL,
    [CatalogBrandId]    INT              NOT NULL,
    [AvailableStock]    INT              NOT NULL  DEFAULT 0,
    [RestockThreshold]  INT              NOT NULL  DEFAULT 0,
    [MaxStockThreshold] INT              NOT NULL  DEFAULT 0,
    [OnReorder]         BIT              NOT NULL  DEFAULT 0,
    CONSTRAINT [PK_Catalog]            PRIMARY KEY ([Id]),
    CONSTRAINT [FK_Catalog_CatalogBrands_CatalogBrandId]
        FOREIGN KEY ([CatalogBrandId]) REFERENCES [CatalogBrands]([Id]) ON DELETE NO ACTION,
    CONSTRAINT [FK_Catalog_CatalogTypes_CatalogTypeId]
        FOREIGN KEY ([CatalogTypeId])  REFERENCES [CatalogTypes]([Id])  ON DELETE NO ACTION
);

CREATE INDEX [IX_Catalog_CatalogBrandId] ON [Catalog] ([CatalogBrandId]);
CREATE INDEX [IX_Catalog_CatalogTypeId]  ON [Catalog] ([CatalogTypeId]);
```

| Column | SQL Server Type | Nullable | Constraint | Notes |
|---|---|---|---|---|
| Id | INT | NOT NULL | PK; HiLo `catalog_hilo` | DISC-010 |
| Name | NVARCHAR(50) | NOT NULL | | BIZ-RULE-020: unique enforced in app; BIZ-RULE-022: not empty; DISC-002 |
| Description | NVARCHAR(MAX) | NOT NULL | | BIZ-RULE-022: not empty at creation |
| Price | DECIMAL(18,2) | NOT NULL | | BIZ-RULE-021: Guard.Against.NegativeOrZero enforced at domain layer |
| PictureUri | NVARCHAR(MAX) | NULL | | BIZ-RULE-023: default placeholder assigned on create |
| CatalogTypeId | INT | NOT NULL | FK → CatalogTypes.Id RESTRICT | |
| CatalogBrandId | INT | NOT NULL | FK → CatalogBrands.Id RESTRICT | |
| AvailableStock | INT | NOT NULL | DEFAULT 0 | |
| RestockThreshold | INT | NOT NULL | DEFAULT 0 | |
| MaxStockThreshold | INT | NOT NULL | DEFAULT 0 | |
| OnReorder | BIT | NOT NULL | DEFAULT 0 | |

**HiLo Sequence:**
```sql
CREATE SEQUENCE [catalog_hilo]
    START WITH 1
    INCREMENT BY 10;
```

---

### 2.4 `Baskets` — DATA-ENT-004

**EF Entity:** `Basket` | **Key:** IDENTITY

```sql
CREATE TABLE [Baskets] (
    [Id]      INT           NOT NULL IDENTITY(1,1),
    [BuyerId] NVARCHAR(256) NOT NULL,
    CONSTRAINT [PK_Baskets] PRIMARY KEY ([Id])
);

CREATE INDEX [IX_Baskets_BuyerId] ON [Baskets] ([BuyerId]);
```

| Column | SQL Server Type | Nullable | Notes |
|---|---|---|---|
| Id | INT IDENTITY(1,1) | NOT NULL | Standard IDENTITY; cascade delete to BasketItems |
| BuyerId | NVARCHAR(256) | NOT NULL | Cross-DB soft ref to AspNetUsers.Id — NO FK constraint; PII-07 |

---

### 2.5 `BasketItems` — DATA-ENT-005

**EF Entity:** `BasketItem` | **Key:** IDENTITY

```sql
CREATE TABLE [BasketItems] (
    [Id]            INT           NOT NULL IDENTITY(1,1),
    [BasketId]      INT           NOT NULL,
    [CatalogItemId] INT           NOT NULL,
    [UnitPrice]     DECIMAL(18,2) NOT NULL,
    [Quantity]      INT           NOT NULL,
    CONSTRAINT [PK_BasketItems]      PRIMARY KEY ([Id]),
    CONSTRAINT [FK_BasketItems_Baskets_BasketId]
        FOREIGN KEY ([BasketId]) REFERENCES [Baskets]([Id]) ON DELETE CASCADE
);

CREATE INDEX [IX_BasketItems_BasketId] ON [BasketItems] ([BasketId]);
```

| Column | SQL Server Type | Nullable | Notes |
|---|---|---|---|
| Id | INT IDENTITY(1,1) | NOT NULL | |
| BasketId | INT | NOT NULL | FK → Baskets.Id CASCADE DELETE (intra-aggregate) |
| CatalogItemId | INT | NOT NULL | Soft ref to Catalog.Id — NO FK constraint (cross-context) |
| UnitPrice | DECIMAL(18,2) | NOT NULL | Price LOCKED at add-time — not updated when catalog changes (BIZ-RULE-010) |
| Quantity | INT | NOT NULL | BIZ-RULE-004: defaults to 1; auto-merge on duplicate (DISC-007) |

---

### 2.6 `Orders` — DATA-ENT-006 + DATA-ENT-011 (Address VO inlined)

**EF Entity:** `Order` | **Key:** IDENTITY
**Owned entity:** `Address` (DATA-ENT-011) inlined as `ShipToAddress_*` columns

```sql
CREATE TABLE [Orders] (
    [Id]                    INT              NOT NULL IDENTITY(1,1),
    [BuyerId]               NVARCHAR(256)    NOT NULL,
    [OrderDate]             DATETIMEOFFSET   NOT NULL,
    [ShipToAddress_Street]  NVARCHAR(180)    NOT NULL,
    [ShipToAddress_City]    NVARCHAR(100)    NOT NULL,
    [ShipToAddress_State]   NVARCHAR(60)     NULL,
    [ShipToAddress_Country] NVARCHAR(90)     NOT NULL,
    [ShipToAddress_ZipCode] NVARCHAR(18)     NOT NULL,
    CONSTRAINT [PK_Orders] PRIMARY KEY ([Id])
);

CREATE INDEX [IX_Orders_BuyerId] ON [Orders] ([BuyerId]);
```

| Column | SQL Server Type | Nullable | PII | Notes |
|---|---|---|---|---|
| Id | INT IDENTITY(1,1) | NOT NULL | — | |
| BuyerId | NVARCHAR(256) | NOT NULL | PII-05 | Cross-DB soft ref — NO FK; BIZ-RULE-011 |
| OrderDate | DATETIMEOFFSET | NOT NULL | — | Auto-set at creation |
| ShipToAddress_Street | NVARCHAR(180) | NOT NULL | PII-06 | BIZ-RULE-033 |
| ShipToAddress_City | NVARCHAR(100) | NOT NULL | PII-06 | BIZ-RULE-033 |
| ShipToAddress_State | NVARCHAR(60) | NULL | PII-06 | BIZ-RULE-033 — optional |
| ShipToAddress_Country | NVARCHAR(90) | NOT NULL | PII-06 | BIZ-RULE-033 |
| ShipToAddress_ZipCode | NVARCHAR(18) | NOT NULL | PII-06 | BIZ-RULE-033 |

**CRITICAL GAP (BIZ-RULE-015):** Current source code hardcodes "123 Main St., Kent, OH, United States, 44240" for all orders. AO-01 must be implemented before production deployment.

---

### 2.7 `OrderItems` — DATA-ENT-007 + DATA-ENT-012 (CatalogItemOrdered VO inlined)

**EF Entity:** `OrderItem` | **Key:** IDENTITY
**Owned entity:** `CatalogItemOrdered` (DATA-ENT-012) inlined as `ItemOrdered_*` columns

```sql
CREATE TABLE [OrderItems] (
    [Id]                        INT           NOT NULL IDENTITY(1,1),
    [OrderId]                   INT           NOT NULL,
    [ItemOrdered_CatalogItemId] INT           NOT NULL,
    [ItemOrdered_ProductName]   NVARCHAR(50)  NOT NULL,
    [ItemOrdered_PictureUri]    NVARCHAR(MAX) NULL,
    [UnitPrice]                 DECIMAL(18,2) NOT NULL,
    [Units]                     INT           NOT NULL,
    CONSTRAINT [PK_OrderItems] PRIMARY KEY ([Id]),
    CONSTRAINT [FK_OrderItems_Orders_OrderId]
        FOREIGN KEY ([OrderId]) REFERENCES [Orders]([Id]) ON DELETE CASCADE
);

CREATE INDEX [IX_OrderItems_OrderId] ON [OrderItems] ([OrderId]);
```

| Column | SQL Server Type | Nullable | Notes |
|---|---|---|---|
| Id | INT IDENTITY(1,1) | NOT NULL | |
| OrderId | INT | NOT NULL | FK → Orders.Id CASCADE DELETE (intra-aggregate) |
| ItemOrdered_CatalogItemId | INT | NOT NULL | Snapshot — intentionally NO FK to Catalog table (BIZ-RULE-001) |
| ItemOrdered_ProductName | NVARCHAR(50) | NOT NULL | Purchase-time snapshot; immutable; DISC-002 corrected from nvarchar(max) |
| ItemOrdered_PictureUri | NVARCHAR(MAX) | NULL | Purchase-time snapshot |
| UnitPrice | DECIMAL(18,2) | NOT NULL | Price at time of order |
| Units | INT | NOT NULL | CHECK Units >= 1 |

---

## 3. EF Core Configuration (Fluent API)

### 3.1 HiLo Sequences — `CatalogContext.OnModelCreating`

```csharp
// DISC-010: All three Catalog entities use HiLo sequences — NOT IDENTITY
// This is a critical correction from DA Agent 1 output.

modelBuilder.HasSequence("catalog_hilo")
    .StartsAt(1)
    .IncrementsBy(10);

modelBuilder.HasSequence("catalog_brand_hilo")
    .StartsAt(1)
    .IncrementsBy(10);

modelBuilder.HasSequence("catalog_type_hilo")
    .StartsAt(1)
    .IncrementsBy(10);
```

### 3.2 CatalogItemConfiguration

```csharp
public class CatalogItemConfiguration : IEntityTypeConfiguration<CatalogItem>
{
    public void Configure(EntityTypeBuilder<CatalogItem> builder)
    {
        builder.ToTable("Catalog");

        // HiLo PK — DISC-010
        builder.Property(ci => ci.Id)
            .UseHiLo("catalog_hilo");

        // DA Agent 2 corrected: nvarchar(50) not nvarchar(max) — DISC-002
        builder.Property(ci => ci.Name)
            .IsRequired()
            .HasMaxLength(50);

        builder.Property(ci => ci.Description)
            .IsRequired();

        builder.Property(ci => ci.Price)
            .IsRequired()
            .HasColumnType("decimal(18,2)");

        builder.Property(ci => ci.PictureUri)
            .IsRequired(false);

        // FKs — RESTRICT (no cascade delete on reference data)
        builder.HasOne(ci => ci.CatalogBrand)
            .WithMany()
            .HasForeignKey(ci => ci.CatalogBrandId)
            .OnDelete(DeleteBehavior.Restrict);

        builder.HasOne(ci => ci.CatalogType)
            .WithMany()
            .HasForeignKey(ci => ci.CatalogTypeId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
```

### 3.3 CatalogBrandConfiguration

```csharp
public class CatalogBrandConfiguration : IEntityTypeConfiguration<CatalogBrand>
{
    public void Configure(EntityTypeBuilder<CatalogBrand> builder)
    {
        builder.ToTable("CatalogBrands");

        // HiLo PK — DISC-010
        builder.Property(cb => cb.Id)
            .UseHiLo("catalog_brand_hilo");

        // DA Agent 2 corrected: nvarchar(100) not nvarchar(max) — DISC-002
        builder.Property(cb => cb.Brand)
            .IsRequired()
            .HasMaxLength(100);
    }
}
```

### 3.4 CatalogTypeConfiguration

```csharp
public class CatalogTypeConfiguration : IEntityTypeConfiguration<CatalogType>
{
    public void Configure(EntityTypeBuilder<CatalogType> builder)
    {
        builder.ToTable("CatalogTypes");

        // HiLo PK — DISC-010
        builder.Property(ct => ct.Id)
            .UseHiLo("catalog_type_hilo");

        // DA Agent 2 corrected: nvarchar(100) not nvarchar(max) — DISC-002
        builder.Property(ct => ct.Type)
            .IsRequired()
            .HasMaxLength(100);
    }
}
```

### 3.5 BasketConfiguration

```csharp
public class BasketConfiguration : IEntityTypeConfiguration<Basket>
{
    public void Configure(EntityTypeBuilder<Basket> builder)
    {
        builder.ToTable("Baskets");

        // Standard IDENTITY — not HiLo
        builder.Property(b => b.Id)
            .UseIdentityColumn();

        builder.Property(b => b.BuyerId)
            .IsRequired()
            .HasMaxLength(256);

        // Cascade delete to child BasketItems
        builder.HasMany(b => b.Items)
            .WithOne()
            .HasForeignKey(bi => bi.BasketId)
            .OnDelete(DeleteBehavior.Cascade);

        builder.HasIndex(b => b.BuyerId)
            .HasDatabaseName("IX_Baskets_BuyerId");
    }
}
```

### 3.6 OrderConfiguration — including Address owned entity

```csharp
public class OrderConfiguration : IEntityTypeConfiguration<Order>
{
    public void Configure(EntityTypeBuilder<Order> builder)
    {
        builder.ToTable("Orders");

        // Standard IDENTITY
        builder.Property(o => o.Id)
            .UseIdentityColumn();

        builder.Property(o => o.BuyerId)
            .IsRequired()
            .HasMaxLength(256);
        // NOTE: No FK constraint to IdentityDatabase — cross-DB soft reference
        // BIZ-RULE-011: BuyerId required; OQ-001: may store email (PII-05)

        builder.Property(o => o.OrderDate)
            .IsRequired();

        // Address owned entity — inlined into Orders table as ShipToAddress_* columns
        // DATA-ENT-011; BIZ-RULE-033 column lengths
        builder.OwnsOne(o => o.ShipToAddress, address =>
        {
            address.WithOwner();
            address.Property(a => a.Street)
                .HasColumnName("ShipToAddress_Street")
                .HasMaxLength(180)
                .IsRequired();
            address.Property(a => a.City)
                .HasColumnName("ShipToAddress_City")
                .HasMaxLength(100)
                .IsRequired();
            address.Property(a => a.State)
                .HasColumnName("ShipToAddress_State")
                .HasMaxLength(60)
                .IsRequired(false);  // nullable per BIZ-RULE-033
            address.Property(a => a.Country)
                .HasColumnName("ShipToAddress_Country")
                .HasMaxLength(90)
                .IsRequired();
            address.Property(a => a.ZipCode)
                .HasColumnName("ShipToAddress_ZipCode")
                .HasMaxLength(18)
                .IsRequired();
        });

        builder.HasIndex(o => o.BuyerId)
            .HasDatabaseName("IX_Orders_BuyerId");
    }
}
```

### 3.7 OrderItemConfiguration — including CatalogItemOrdered owned entity

```csharp
public class OrderItemConfiguration : IEntityTypeConfiguration<OrderItem>
{
    public void Configure(EntityTypeBuilder<OrderItem> builder)
    {
        builder.ToTable("OrderItems");

        builder.Property(oi => oi.Id)
            .UseIdentityColumn();

        builder.Property(oi => oi.UnitPrice)
            .IsRequired()
            .HasColumnType("decimal(18,2)");

        builder.Property(oi => oi.Units)
            .IsRequired();

        // CatalogItemOrdered owned value object — inlined as ItemOrdered_* columns
        // DATA-ENT-012; BIZ-RULE-001 snapshot principle
        builder.OwnsOne(oi => oi.ItemOrdered, itemOrdered =>
        {
            itemOrdered.WithOwner();
            itemOrdered.Property(io => io.CatalogItemId)
                .HasColumnName("ItemOrdered_CatalogItemId")
                .IsRequired();
            // NOTE: ItemOrdered_CatalogItemId intentionally has NO FK constraint
            // This is a snapshot — not a live reference to the Catalog table (BIZ-RULE-001)

            // DA Agent 2 corrected: nvarchar(50) not nvarchar(max) — DISC-002
            itemOrdered.Property(io => io.ProductName)
                .HasColumnName("ItemOrdered_ProductName")
                .HasMaxLength(50)
                .IsRequired();

            itemOrdered.Property(io => io.PictureUri)
                .HasColumnName("ItemOrdered_PictureUri")
                .IsRequired(false);
        });

        builder.HasIndex(oi => oi.OrderId)
            .HasDatabaseName("IX_OrderItems_OrderId");
    }
}
```

---

## 4. Complete CatalogContext Setup

```csharp
public class CatalogContext : DbContext
{
    public DbSet<CatalogItem> CatalogItems { get; set; }
    public DbSet<CatalogBrand> CatalogBrands { get; set; }
    public DbSet<CatalogType> CatalogTypes { get; set; }
    public DbSet<Basket> Baskets { get; set; }
    public DbSet<BasketItem> BasketItems { get; set; }
    public DbSet<Order> Orders { get; set; }
    public DbSet<OrderItem> OrderItems { get; set; }

    // NOTE: Buyer and PaymentMethod are intentionally NOT registered here.
    // DATA-ENT-008 and DATA-ENT-009 are DORMANT (DISC-003 / BIZ-RULE-035).
    // Add DbSets only when AO-05 (payment integration) is implemented.

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Apply all IEntityTypeConfiguration classes
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(CatalogContext).Assembly);

        // HiLo sequences for Catalog entities — DISC-010
        modelBuilder.HasSequence("catalog_hilo").StartsAt(1).IncrementsBy(10);
        modelBuilder.HasSequence("catalog_brand_hilo").StartsAt(1).IncrementsBy(10);
        modelBuilder.HasSequence("catalog_type_hilo").StartsAt(1).IncrementsBy(10);
    }
}
```

---

## 5. Migration Strategy

### 5.1 Topological Migration Order

Parent tables must be created before child tables that reference them.

```
Wave 1 — No FK dependencies:
  CatalogBrands (+ catalog_brand_hilo sequence)
  CatalogTypes  (+ catalog_type_hilo sequence)
  Baskets       (no FK to Identity — cross-DB soft ref)

Wave 2 — FK dependencies on Wave 1:
  Catalog       (catalog_hilo sequence; FK → CatalogBrands, FK → CatalogTypes)
  BasketItems   (FK → Baskets CASCADE)

Wave 3 — Root table:
  Orders        (no FK — BuyerId is cross-DB soft ref)

Wave 4 — FK dependencies on Wave 3:
  OrderItems    (FK → Orders CASCADE)
```

### 5.2 EF Core Migration Commands

```bash
# Add initial migration
dotnet ef migrations add InitialCreate \
    --context CatalogContext \
    --project src/Infrastructure \
    --startup-project src/Web

# Apply to database
dotnet ef database update \
    --context CatalogContext \
    --project src/Infrastructure \
    --startup-project src/Web
```

### 5.3 Migration Rollback Strategy

**Impact of HiLo sequences on rollback (DISC-010):**
- HiLo sequences allocate blocks of IDs in advance (increment by 10)
- After a failed migration, sequence values are NOT rolled back
- Gaps will exist in ID sequences after rollback — this is expected and acceptable
- Do NOT attempt to reset sequences manually after rollback; this can cause duplicate key violations

### 5.4 Seed Data Migration

Seed data is applied via `CatalogContextSeed` and `AppIdentityDbContextSeed` at application startup (APP-SVC-010, APP-SVC-011), NOT via EF migrations.

**Catalog seed (BIZ-RULE-031):** 5 brands, 4 types, 12 products — skipped if data already exists.
**Retry strategy (BIZ-RULE-036):** Seeding retries up to 10 times on database failure before aborting startup.
**Identity seed bug (BIZ-RULE-037 / AO-09):** Role creation does NOT check if role exists before creating — produces duplicate role error on restart. Fix: `if (!await roleManager.RoleExistsAsync(roleName)) await roleManager.CreateAsync(new IdentityRole(roleName));`

---

## 6. IdentityDatabase — Physical Schema (ASP.NET Core Identity)

The IdentityDatabase uses the standard ASP.NET Core Identity schema managed by `AppIdentityDbContext`. The full schema is generated by the Identity framework migration — key tables:

| Table | Purpose | Key Notes |
|---|---|---|
| AspNetUsers | User accounts | PII-01 through PII-04; seeded accounts have hardcoded passwords (BIZ-RULE-029 — CRITICAL) |
| AspNetRoles | Roles | Only confirmed role: `Administrators` (BIZ-RULE-005) |
| AspNetUserRoles | User-role assignments | Many-to-many join |
| AspNetUserClaims | User claims | JWT claims sourced from here (BIZ-RULE-007) |
| AspNetRoleClaims | Role claims | |
| AspNetUserLogins | External logins | |
| AspNetUserTokens | User tokens | PII-08: Value column HIGH sensitivity |

**Connection string key:** `IdentityConnection`
**EF Context class:** `AppIdentityDbContext`

---

## 7. Referential Integrity Summary

| FK | Child Table.Column | Parent Table | On Delete | Type |
|---|---|---|---|---|
| FK_Catalog_CatalogBrands | Catalog.CatalogBrandId | CatalogBrands.Id | NO ACTION (RESTRICT) | Hard — same DB |
| FK_Catalog_CatalogTypes | Catalog.CatalogTypeId | CatalogTypes.Id | NO ACTION (RESTRICT) | Hard — same DB |
| FK_BasketItems_Baskets | BasketItems.BasketId | Baskets.Id | CASCADE | Hard — intra-aggregate |
| FK_OrderItems_Orders | OrderItems.OrderId | Orders.Id | CASCADE | Hard — intra-aggregate |
| *(soft)* Baskets.BuyerId | — | AspNetUsers.Id | App-enforced ONLY | Cross-DB — NO FK |
| *(soft)* Orders.BuyerId | — | AspNetUsers.Id | App-enforced ONLY | Cross-DB — NO FK |
| *(soft)* BasketItems.CatalogItemId | — | Catalog.Id | App-enforced ONLY | Cross-context — NO FK |
| *(snapshot)* OrderItems.ItemOrdered_CatalogItemId | — | Catalog.Id | NO FK by design | Historical snapshot — intentional |

**Why no FK on CatalogItemId in BasketItems:** Cross-context soft reference. Catalog items could theoretically be deleted while basket items exist — orphan basket items are an accepted risk per DISC-002 (no cross-context FK found in source).

**Why no FK on ItemOrdered_CatalogItemId:** Intentional snapshot denormalization (BIZ-RULE-001). Order history must survive catalog item deletion, renaming, or price changes.

---

## 8. Production-Readiness Notes

| Item | Status | Reference |
|---|---|---|
| Hardcoded seeded passwords (Pass@word1) | CRITICAL — must externalise to config | BIZ-RULE-029, AO-03 |
| JWT signing key hardcoded in source | CRITICAL — must externalise to config/Key Vault | BIZ-RULE-032, AO-03 |
| SA password hardcoded in docker-compose.yml | CRITICAL — use Docker secrets or env var | TECH-SEC-007, TD-01 |
| Hardcoded shipping address in all orders | CRITICAL — collect from user at checkout | BIZ-RULE-015, AO-01 |
| Azure SQL Edge container (docker) at EOL March 2025 | HIGH — replace with mcr.microsoft.com/mssql/server:2022-latest | TECH-INF-003, TD-04 |
| No EF Core retry strategy for transient SQL errors | HIGH — add EnableRetryOnFailure() | TD-09 |
| Identity seeding duplicate role error on restart | MEDIUM — add existence check (AO-09) | BIZ-RULE-037 |

---

*Data Model Specification — physical SQL Server schema derived from ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*DA Agent 2 corrected field types and HiLo sequence configurations applied throughout.*
*Every table spec, EF configuration, and FK rule is traceable to DATA-ENT node IDs and evidence.*
