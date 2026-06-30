# Business Capability Model

**System:** eShopOnWeb
**Source of truth:** ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline/sample-output/foundation/)
**Generated:** 2026-06-30
**Pipeline stage:** Forward Engineering — Document 02 of 20
**Confidence schema:** HIGH = direct code evidence confirmed; MEDIUM = inferred from structure; LOW = assumed from convention

> Every capability, domain grouping, status, heat-map rating, and gap below traces to node IDs in ENTERPRISE_KNOWLEDGE_GRAPH.json. All 31 BIZ-CAP nodes (BIZ-CAP-001..031) appear at least once.

---

## 1. Capability Inventory — All 31 Capabilities

### 1.1 Catalog Domain (BIZ-CAP-001..009)

| ID | Capability Name | Status | Confidence | Backing Service | Key Defects/Gaps |
|----|----------------|--------|------------|-----------------|-----------------|
| **BIZ-CAP-001** | Catalogue Discovery (Paged Browse) | Active | HIGH | CatalogItemListPagedEndpoint (GET /api/catalog-items) | Mandatory 1-second artificial delay — BIZ-RULE-009 |
| **BIZ-CAP-002** | Single Product Retrieval | Active | HIGH | CatalogItemGetByIdEndpoint (GET /api/catalog-items/{id}) | — |
| **BIZ-CAP-003** | Admin Catalogue Product Creation | Active | HIGH | CreateCatalogItemEndpoint (POST /api/catalog-items) | Admin only; ARCH-VIOL-003 (direct EfRepository dep) |
| **BIZ-CAP-004** | Admin Catalogue Product Update | Active | HIGH | UpdateCatalogItemEndpoint (PUT /api/catalog-items) | Admin only; ARCH-VIOL-005 |
| **BIZ-CAP-005** | Admin Catalogue Product Deletion | Active | HIGH | DeleteCatalogItemEndpoint (DELETE /api/catalog-items/{id}) | Admin only; ARCH-VIOL-004 |
| **BIZ-CAP-006** | Brand List Retrieval | Active | HIGH | CatalogBrandListEndpoint (GET /api/catalog-brands) | ARCH-VIOL-001 (direct EfRepository dep) |
| **BIZ-CAP-007** | Type List Retrieval | Active | HIGH | CatalogTypeListEndpoint (GET /api/catalog-types) | ARCH-VIOL-006 |
| **BIZ-CAP-008** | Admin Browser-Cached Catalogue View | Active | HIGH | CachedCatalogItemServiceDecorator (localStorage, 1-min TTL) | Write-through for items only; brands/types TTL-only |
| **BIZ-CAP-009** | Database Catalogue Seeding | Active | HIGH | CatalogContextSeed | Skipped if data already exists (BIZ-RULE-031) |

### 1.2 Basket Domain (BIZ-CAP-010..016)

| ID | Capability Name | Status | Confidence | Backing Service | Key Defects/Gaps |
|----|----------------|--------|------------|-----------------|-----------------|
| **BIZ-CAP-010** | Basket Item Addition | Active | HIGH | BasketService | Auto-merges on duplicate (confirmed — not exception); price locked at add-time |
| **BIZ-CAP-011** | Basket Deletion | Active | HIGH | BasketService | Triggered at checkout (BIZ-RULE-003) and after transfer |
| **BIZ-CAP-012** | Anonymous-to-User Basket Transfer | Active | HIGH | BasketService.TransferBasketAsync | Web login path only — API login does NOT trigger (BIZ-RULE-002) |
| **BIZ-CAP-013** | Basket Item Quantity Update | Active | HIGH | BasketService | — |
| **BIZ-CAP-014** | Basket Item Count Query | Active | HIGH | BasketQueryService | — |
| **BIZ-CAP-015** | Basket View with Product Details | Active | HIGH | BasketViewModelService | — |
| **BIZ-CAP-016** | Get or Create Basket | Active | HIGH | BasketViewModelService | — |

### 1.3 Order Domain (BIZ-CAP-017..020)

| ID | Capability Name | Status | Confidence | Backing Service | Key Defects/Gaps |
|----|----------------|--------|------------|-----------------|-----------------|
| **BIZ-CAP-017** | Order Creation from Basket | Active | HIGH | OrderService | Hardcoded shipping address (BIZ-RULE-015); no payment processing |
| **BIZ-CAP-018** | Order Total Calculation | Active | HIGH | Order.Total() method | Computed from OrderItems (price × qty) |
| **BIZ-CAP-019** | Order History Retrieval | Active | HIGH | GetMyOrdersHandler | Returns only own orders (BIZ-RULE-030) |
| **BIZ-CAP-020** | Order Detail View | Active | HIGH | GetOrderDetailsHandler | Returns own orders only (BIZ-RULE-030) |

### 1.4 Identity Domain (BIZ-CAP-021..026)

| ID | Capability Name | Status | Confidence | Backing Service | Key Defects/Gaps |
|----|----------------|--------|------------|-----------------|-----------------|
| **BIZ-CAP-021** | User Authentication (Web — Cookie) | Active | HIGH | ASP.NET Core Identity SignInManager | Triggers basket transfer (BIZ-RULE-002) |
| **BIZ-CAP-022** | User Authentication (API — JWT Issue) | Active | HIGH | AuthenticateEndpoint (POST /api/authenticate) | Does NOT trigger basket transfer |
| **BIZ-CAP-023** | JWT Token Generation | Active | HIGH | IdentityTokenClaimService | JWT key hardcoded (BIZ-RULE-032 — CRITICAL) |
| **BIZ-CAP-024** | New User Registration | Active | HIGH | Register.cshtml.cs | Email confirmation silently discarded (BIZ-RULE-027 — CRITICAL) |
| **BIZ-CAP-025** | BlazorAdmin Authentication State (60s poll) | Active | HIGH | CustomAuthStateProvider | 60-second poll interval |
| **BIZ-CAP-026** | Identity and Role Seeding | Active | HIGH | AppIdentityDbContextSeed | Hardcoded passwords (BIZ-RULE-029, BIZ-RULE-037) |

### 1.5 Infrastructure Domain (BIZ-CAP-027..029)

| ID | Capability Name | Status | Confidence | Backing Service | Key Defects/Gaps |
|----|----------------|--------|------------|-----------------|-----------------|
| **BIZ-CAP-027** | Email Notification | **NON-FUNCTIONAL (Stub)** | HIGH | EmailSender | Returns Task.CompletedTask immediately — no delivery (BIZ-RULE-008) |
| **BIZ-CAP-028** | Generic Data Repository (EF Core) | Active | HIGH | EfRepository | Coupling score 16 (ARCH-VIOL-009); 6 API endpoints depend directly |
| **BIZ-CAP-029** | Database Seed and Migration on Startup | Active | HIGH | CatalogContextSeed / AppIdentityDbContextSeed | 10 retries before abort (BIZ-RULE-036) |

### 1.6 Buyer Domain (BIZ-CAP-030..031) — DORMANT

| ID | Capability Name | Status | Confidence | Backing Service | Key Notes |
|----|----------------|--------|------------|-----------------|-----------|
| **BIZ-CAP-030** | Buyer Account Structure | **DORMANT — no service layer** | HIGH | BuyerAggregate (no active service) | Not in CatalogContext DbSet; confirmed dead (BIZ-RULE-035) |
| **BIZ-CAP-031** | Payment Method Record | **DORMANT — no service layer** | HIGH | PaymentMethod (no active service) | PCI comment in source (BIZ-RULE-034); no checkout integration |

---

## 2. Capability Heat Map

The heat map classifies all 31 capabilities across three dimensions: **operational status**, **strategic importance**, and **production readiness**. Cells are colour-coded: Active (green), Active-with-defect (amber), Non-functional stub (red), Dormant (grey).

### 2.1 Status Classification

| Status | Count | Capabilities |
|--------|-------|-------------|
| **Active — Fully Functional** | 25 | BIZ-CAP-001*, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 018, 019, 020, 021, 022, 023, 025, 026, 028, 029 |
| **Active — Critical Defect** | 3 | BIZ-CAP-001 (artificial delay), BIZ-CAP-017 (hardcoded address), BIZ-CAP-024 (no email confirmation) |
| **Non-Functional Stub** | 1 | BIZ-CAP-027 (EmailSender) |
| **Dormant — No Service Layer** | 2 | BIZ-CAP-030 (Buyer), BIZ-CAP-031 (PaymentMethod) |

*BIZ-CAP-001 counted as Active with defect due to BIZ-RULE-009.

### 2.2 Capability Heat Map Table

```
DOMAIN          | CAPABILITY                              | HEAT  | STATUS    | PRIORITY
----------------|----------------------------------------|-------|-----------|----------
CATALOG         | BIZ-CAP-001 Paged Browse               | AMBER | Active*   | CRITICAL-FIX
                | BIZ-CAP-002 Single Product Retrieval   | GREEN | Active    | HIGH
                | BIZ-CAP-003 Admin Product Creation     | GREEN | Active    | HIGH
                | BIZ-CAP-004 Admin Product Update       | GREEN | Active    | HIGH
                | BIZ-CAP-005 Admin Product Deletion     | GREEN | Active    | HIGH
                | BIZ-CAP-006 Brand List Retrieval       | GREEN | Active    | MEDIUM
                | BIZ-CAP-007 Type List Retrieval        | GREEN | Active    | MEDIUM
                | BIZ-CAP-008 Admin Browser Cache        | GREEN | Active    | MEDIUM
                | BIZ-CAP-009 DB Catalogue Seeding       | GREEN | Active    | LOW
BASKET          | BIZ-CAP-010 Item Addition              | GREEN | Active    | HIGH
                | BIZ-CAP-011 Basket Deletion            | GREEN | Active    | HIGH
                | BIZ-CAP-012 Anon-to-User Transfer      | GREEN | Active    | HIGH
                | BIZ-CAP-013 Quantity Update            | GREEN | Active    | MEDIUM
                | BIZ-CAP-014 Item Count Query           | GREEN | Active    | MEDIUM
                | BIZ-CAP-015 View with Product Details  | GREEN | Active    | MEDIUM
                | BIZ-CAP-016 Get or Create Basket       | GREEN | Active    | MEDIUM
ORDER           | BIZ-CAP-017 Order Creation             | AMBER | Active*   | CRITICAL-FIX
                | BIZ-CAP-018 Order Total Calculation    | GREEN | Active    | HIGH
                | BIZ-CAP-019 Order History Retrieval    | GREEN | Active    | HIGH
                | BIZ-CAP-020 Order Detail View          | GREEN | Active    | HIGH
IDENTITY        | BIZ-CAP-021 Web Authentication         | GREEN | Active    | HIGH
                | BIZ-CAP-022 API Authentication (JWT)  | GREEN | Active    | HIGH
                | BIZ-CAP-023 JWT Token Generation       | AMBER | Active*   | CRITICAL-FIX
                | BIZ-CAP-024 User Registration          | AMBER | Active*   | CRITICAL-FIX
                | BIZ-CAP-025 BlazorAdmin Auth State     | GREEN | Active    | MEDIUM
                | BIZ-CAP-026 Identity & Role Seeding    | AMBER | Active*   | CRITICAL-FIX
INFRASTRUCTURE  | BIZ-CAP-027 Email Notification         | RED   | STUB      | CRITICAL-FIX
                | BIZ-CAP-028 Generic Repository (EF)   | AMBER | Active*   | HIGH (refactor)
                | BIZ-CAP-029 DB Seed on Startup         | GREEN | Active    | LOW
BUYER (DORMANT) | BIZ-CAP-030 Buyer Account Structure    | GREY  | DORMANT   | FUTURE (AO-05)
                | BIZ-CAP-031 Payment Method Record      | GREY  | DORMANT   | FUTURE (AO-05)
```

*Active with Critical Defect — see Section 4 Gap Analysis

### 2.3 Domain Coverage Summary

| Domain | Total Capabilities | Active (clean) | Active (defect) | Non-Functional | Dormant |
|--------|-------------------|---------------|-----------------|----------------|---------|
| Catalog | 9 | 7 | 1 (BIZ-CAP-001) | 0 | 0 |
| Basket | 7 | 7 | 0 | 0 | 0 |
| Order | 4 | 3 | 1 (BIZ-CAP-017) | 0 | 0 |
| Identity | 6 | 2 | 4 (BIZ-CAP-023, 024, 026, +022*) | 0 | 0 |
| Infrastructure | 3 | 1 | 1 (BIZ-CAP-028) | 1 (BIZ-CAP-027) | 0 |
| Buyer | 2 | 0 | 0 | 0 | 2 |
| **TOTAL** | **31** | **20** | **7** | **1** | **2** |

---

## 3. Domain Grouping and Ownership

### 3.1 Catalog Domain

**Owner:** BA (Business Architecture), backed by AA Application layer  
**Primary value stream:** VS-002 Catalogue Lifecycle (Admin)  
**Backing entities:** DATA-ENT-001 (CatalogItem), DATA-ENT-002 (CatalogBrand), DATA-ENT-003 (CatalogType)  
**Key interfaces:** APP-API-002..008 (7 of 8 total REST endpoints)  
**Caching layers:**
- Web MVC: ASP.NET Core IMemoryCache (CACHE-001) — 30-second sliding TTL, server-side
- BlazorAdmin: Blazored.LocalStorage (CACHE-002) — 1-minute TTL, browser-side, write-through on item mutations

**Capability grouping (read/write split):**
- **Read capabilities:** BIZ-CAP-001 (paged browse), BIZ-CAP-002 (single item), BIZ-CAP-006 (brands), BIZ-CAP-007 (types)
- **Write capabilities (Admin only):** BIZ-CAP-003 (create), BIZ-CAP-004 (update), BIZ-CAP-005 (delete)
- **Cache capability:** BIZ-CAP-008 (admin cached view)
- **Seeding capability:** BIZ-CAP-009 (startup seed)

**Architecture violations in this domain:**
- ARCH-VIOL-001: CatalogBrandListEndpoint → EfRepository (direct)
- ARCH-VIOL-002: CatalogItemGetByIdEndpoint → EfRepository (direct)
- ARCH-VIOL-003: CreateCatalogItemEndpoint → EfRepository (direct)
- ARCH-VIOL-004: DeleteCatalogItemEndpoint → EfRepository (direct)
- ARCH-VIOL-005: UpdateCatalogItemEndpoint → EfRepository (direct)
- ARCH-VIOL-006: CatalogTypeListEndpoint → EfRepository (direct)

### 3.2 Basket Domain

**Owner:** BA (Business Architecture), backed by AA Application layer  
**Primary value stream:** VS-001 Shopper Purchase Journey (stages 3-4)  
**Backing entities:** DATA-ENT-004 (Basket), DATA-ENT-005 (BasketItem)  
**Aggregate:** DATA-AGG-001 BasketAggregate (Basket as root, BasketItem as child)  

**Important behavioral note:** Basket transfer at login is triggered **only via the Web MVC login path** (Login.cshtml.cs:83-114). API login via POST /api/authenticate does NOT trigger basket transfer. This asymmetry is by design — BlazorAdmin users never get anonymous basket merged.

**Anonymous shopper identification:** 10-year GUID cookie (BIZ-RULE-016). Cookie is marked as essential and is not subject to consent banner restrictions. Transfer validation checks GUID format before proceeding (BIZ-RULE-017).

### 3.3 Order Domain

**Owner:** BA (Business Architecture), backed by AA Application layer  
**Primary value stream:** VS-001 Shopper Purchase Journey (stages 5-7)  
**Backing entities:** DATA-ENT-006 (Order), DATA-ENT-007 (OrderItem), DATA-ENT-011 (Address VO), DATA-ENT-012 (CatalogItemOrdered VO)  
**Aggregate:** DATA-AGG-002 OrderAggregate (Order as root, OrderItems with embedded snapshots)  

**Snapshot pattern (BIZ-RULE-001):** Product name, picture URI, and catalogue ID are captured at purchase time into CatalogItemOrdered value objects. This makes order history immune to future catalogue changes — a deliberate DDD design decision.

**Critical gap:** BIZ-RULE-015 — all orders currently record the same hardcoded shipping address. This is a production blocker (AO-01).

**Immutability constraint:** BIZ-RULE-012 — orders have no status field and are immutable after creation. Order status lifecycle is a future capability (AO-06).

### 3.4 Identity Domain

**Owner:** BA (Business Architecture), backed by ASP.NET Core Identity  
**Primary value stream:** VS-003 New User Onboarding  
**Backing entities:** DATA-ENT-010 (ApplicationUser), DATA-ENT-009 (Role in IdentityDatabase)  
**Repository:** DATA-REPO-002 IdentityDatabase (AppIdentityDbContext) — already isolated from CatalogContext  

**Dual authentication architecture:**
- **Web MVC path:** ASP.NET Core Identity cookie → triggers anonymous basket transfer on login
- **API path:** JWT Bearer token (7-day expiry, BIZ-RULE-024) → does NOT trigger basket transfer

**Seeded accounts (production risk):**
- demouser@microsoft.com (BIZ-ACT-004) — BIZ-RULE-029
- admin@microsoft.com (BIZ-ACT-005) — BIZ-RULE-013

### 3.5 Infrastructure Domain

**Owner:** BA (Business Architecture)  
**Key service:** EfRepository (APP-SVC-008) — generic Repository pattern implementing Ardalis.Specification  
**Architecture concern:** EfRepository has coupling score of 16 (ARCH-VIOL-009). Six API endpoints bypass domain service abstraction to call it directly (ARCH-VIOL-001..007).  
**Email stub:** BIZ-CAP-027 (EmailSender.cs) is entirely non-functional — returns Task.CompletedTask on every invocation (BIZ-RULE-008).  
**Startup seeding:** BIZ-CAP-029 — 10 retries with exponential back-off before aborting startup (BIZ-RULE-036).

### 3.6 Buyer Domain (DORMANT)

**Status:** Structurally defined in ApplicationCore but confirmed dead — not registered in any DbContext.  
**Evidence:** DA Agent 2 confirmed Buyer and PaymentMethod have no DbSet in CatalogContext (BIZ-RULE-035; DISC-003 in normalization log).  
**Future activation path:** AO-05 — requires PCI-compliant payment processor integration.  
**PCI constraint:** BIZ-RULE-034 — payment method must never store full card details; only token, alias, and last 4 digits.

---

## 4. Gap Analysis

### 4.1 Critical Gaps (Production Blockers)

| Gap ID | Affected Capability | Gap Description | Business Rule | Resolution Action |
|--------|-------------------|-----------------|---------------|------------------|
| **GAP-001** | BIZ-CAP-001 | 1-second artificial delay on every catalogue browse | BIZ-RULE-009 | AO-04: Delete `await Task.Delay(1000)` from CatalogItemListPagedEndpoint.cs:42 |
| **GAP-002** | BIZ-CAP-017 | All orders record hardcoded shipping address | BIZ-RULE-015 | AO-01: Add shipping address form to checkout |
| **GAP-003** | BIZ-CAP-023 | JWT signing key hardcoded in source code | BIZ-RULE-032 | AO-03: Move to environment variable or Azure Key Vault |
| **GAP-004** | BIZ-CAP-024 | Email confirmation silently discarded on registration | BIZ-RULE-027 | AO-02 + AO-08: Implement email and activate confirmation |
| **GAP-005** | BIZ-CAP-026 | Seeded account passwords hardcoded as plaintext | BIZ-RULE-029, BIZ-RULE-013 | AO-03: Externalise to environment variables |
| **GAP-006** | BIZ-CAP-027 | Email notification entirely non-functional stub | BIZ-RULE-008 | AO-02: Implement SendGrid or SMTP transactional email |
| **GAP-007** | BIZ-CAP-030, BIZ-CAP-031 | Payment processing absent — BuyerAggregate dormant | BIZ-RULE-034, BIZ-RULE-035 | AO-05: Activate BuyerAggregate with PCI-compliant payment processor |

### 4.2 High-Priority Architecture Gaps

| Gap ID | Affected Capabilities | Gap Description | Evidence | Resolution Action |
|--------|----------------------|-----------------|----------|------------------|
| **GAP-008** | BIZ-CAP-003..007 | 6 API endpoints bypass domain service abstraction | ARCH-VIOL-001..007 | Route all endpoints through domain service interfaces; remove direct EfRepository references |
| **GAP-009** | All domains | Module dependency cycle spans all bounded contexts | ARCH-VIOL-008 | Break cycle by introducing dependency-inversion seams between modules |
| **GAP-010** | BIZ-CAP-028 | EfRepository coupling score 16 — highest in codebase | ARCH-VIOL-009 | Introduce per-context repository abstractions |
| **GAP-011** | All | Shared CatalogContext persists Catalog, Basket, and Order in one DbContext | DATA-REPO-001 | Split into per-domain DbContexts |
| **GAP-012** | BIZ-CAP-023, BIZ-CAP-025 | JWT token stored in browser localStorage (XSS accessible) | TECH-CUR-012 | Move to httpOnly cookie or secure token storage |
| **GAP-013** | All | ApplicationCore references BlazorShared — domain layer depends on UI library | ARCH-VIOL-011 | Invert dependency; remove BlazorShared reference from ApplicationCore |

### 4.3 Medium-Priority Gaps

| Gap ID | Gap Description | Evidence | Roadmap Item |
|--------|----------------|----------|-------------|
| **GAP-014** | Identity seeding creates ADMINISTRATORS role without existence check — duplicate role error on restart | BIZ-RULE-037 | AO-09 |
| **GAP-015** | Web MVC IMemoryCache (30s) not invalidated on admin writes — storefront shows stale data for up to 30s after any admin change | CACHE-001; CACHE-002 cross-cache staleness | AO-10 |
| **GAP-016** | No retry or circuit-breaker on BlazorAdmin HTTP calls — transient failures cause immediate user-facing errors | nfr_registry.nfr_gaps | Future NFR |
| **GAP-017** | No health check endpoints confirmed in either service | nfr_registry.nfr_gaps | Future NFR |
| **GAP-018** | Azure SQL Edge Docker image is end-of-life (March 2025) | TECH-INF-003 | Immediate infrastructure fix |
| **GAP-019** | No EF Core retry strategy for transient SQL errors | nfr_registry.nfr_gaps | Future NFR |
| **GAP-020** | Identity password minimum length 6 is below NIST SP 800-63B minimum of 8 | nfr_registry | Future security hardening |

---

## 5. Capability Relationships and Dependencies

### 5.1 Inter-Domain Capability Dependencies

```
IDENTITY (BIZ-CAP-021..026)
    |
    |-- [login event] --> BASKET Transfer (BIZ-CAP-012)  [Web path only]
    |-- [buyer id] -----> ORDER Creation (BIZ-CAP-017)
    |-- [JWT auth] ------> CATALOG Admin (BIZ-CAP-003..005)

CATALOG (BIZ-CAP-001..009)
    |
    |-- [price at add-time] --> BASKET Item Addition (BIZ-CAP-010)
    |-- [product snapshot] --> ORDER Creation (BIZ-CAP-017) via CatalogItemOrdered

BASKET (BIZ-CAP-010..016)
    |
    |-- [basket consumed] --> ORDER Creation (BIZ-CAP-017)
    |-- [basket deleted] --> after order saved (BIZ-RULE-003)
```

### 5.2 Capability Dependency Matrix

| Dependent Capability | Depends On | Dependency Type |
|---------------------|-----------|----------------|
| BIZ-CAP-012 (Add to Basket) | BIZ-CAP-001 (Catalogue — item exists) | Data read — price locked at add-time |
| BIZ-CAP-012 (Add to Basket) | DATA-ENT-001 (CatalogItem.Price) | Cross-domain price capture |
| BIZ-CAP-012 (Anon Transfer) | BIZ-CAP-021 (Web login event) | Event-triggered — Web path only |
| BIZ-CAP-017 (Order Creation) | BIZ-CAP-010..016 (Basket must exist) | Basket consumed at checkout |
| BIZ-CAP-017 (Order Creation) | BIZ-CAP-022 (JWT Auth — API path) | Buyer authentication required |
| BIZ-CAP-018 (Order Total) | DATA-ENT-007 (OrderItem.UnitPrice * Units) | Computed from order items |
| BIZ-CAP-003..005 (Admin CRUD) | BIZ-CAP-022 (JWT Auth) | ADMINISTRATORS role required |
| BIZ-CAP-008 (Admin Cache) | BIZ-CAP-003..005 (Write operations) | Write-through cache invalidation |
| BIZ-CAP-029 (DB Seed) | DATA-REPO-001 (CatalogDatabase) | Startup dependency |
| BIZ-CAP-026 (Identity Seed) | DATA-REPO-002 (IdentityDatabase) | Startup dependency |

### 5.3 Value Stream Alignment

**VS-001 Shopper Purchase Journey (7 stages):**
1. Browse catalogue → BIZ-CAP-001
2. View product → BIZ-CAP-002
3. Add to basket → BIZ-CAP-010
4. Login / transfer basket → BIZ-CAP-021, BIZ-CAP-012
5. Checkout → BIZ-CAP-017, BIZ-CAP-018
6. Order confirmation → BIZ-CAP-019, BIZ-CAP-020
7. Email notification → BIZ-CAP-027 (**STUB — non-functional**)

**VS-002 Catalogue Lifecycle Admin (7 stages):**
1. JWT authenticate → BIZ-CAP-022, BIZ-CAP-023
2. View catalogue (cached) → BIZ-CAP-008
3. Create product → BIZ-CAP-003
4. Update product → BIZ-CAP-004
5. Delete product → BIZ-CAP-005
6. Cache refresh → BIZ-CAP-008 (write-through)
7. Storefront update (30s delay) → CACHE-001 TTL expiry

**VS-003 New User Onboarding (4 stages):**
1. Registration form → BIZ-CAP-024
2. Account activation → BIZ-CAP-024 (immediate — email confirmation gap BIZ-RULE-027)
3. First login → BIZ-CAP-021
4. Anonymous basket transfer → BIZ-CAP-012

---

## 6. Capability Prioritization

Prioritisation is based on (a) capability status/confidence, (b) value stream position, (c) production gap severity, and (d) dependency order.

### 6.1 Generation Priority Tiers

| Priority | Domain | Capabilities | Rationale |
|----------|--------|-------------|-----------|
| **P1 — Identity First** | Identity | BIZ-CAP-021..026 | Cross-cutting prerequisite for basket transfer, order buyer ID, admin auth. IdentityDatabase already isolated — cleanest cut. |
| **P2 — Catalogue** | Catalog | BIZ-CAP-001..009 | Upstream reference data for Basket/Order. Highest coupling module — generate early to force shared CatalogContext split. |
| **P3 — Basket** | Basket | BIZ-CAP-010..016 | Depends on Catalogue (item refs) and Identity (buyer ID). Well-defined BasketAggregate boundary. |
| **P4 — Order** | Order | BIZ-CAP-017..020 | Consumes Basket handoff; downstream of Catalogue snapshot. Lowest core coupling. |
| **P5 — Infrastructure** | Infrastructure | BIZ-CAP-027..029 | Cross-cutting seeding and repository concerns. BIZ-CAP-027 stub requires activation (AO-02). |
| **P6 — Buyer (Future)** | Buyer | BIZ-CAP-030..031 | DORMANT. Only on explicit decision to activate BuyerAggregate (AO-05). |

### 6.2 Capability Priority Table

| Tier | ID | Capability | Production Status | Next Action |
|------|----|-----------|-------------------|-------------|
| P1 | BIZ-CAP-022 | API Authentication (JWT) | Active — key hardcoded | AO-03 |
| P1 | BIZ-CAP-021 | Web Authentication (Cookie) | Active | Preserve |
| P1 | BIZ-CAP-023 | JWT Token Generation | Active — key hardcoded | AO-03 |
| P1 | BIZ-CAP-024 | New User Registration | Active — no email confirm | AO-02, AO-08 |
| P1 | BIZ-CAP-025 | BlazorAdmin Auth State | Active | Preserve |
| P1 | BIZ-CAP-026 | Identity & Role Seeding | Active — hardcoded passwords | AO-03 |
| P2 | BIZ-CAP-001 | Catalogue Paged Browse | Active — 1s delay | AO-04 |
| P2 | BIZ-CAP-002 | Single Product Retrieval | Active | Preserve |
| P2 | BIZ-CAP-003 | Admin Product Creation | Active | Fix ARCH-VIOL-003 |
| P2 | BIZ-CAP-004 | Admin Product Update | Active | Fix ARCH-VIOL-005 |
| P2 | BIZ-CAP-005 | Admin Product Deletion | Active | Fix ARCH-VIOL-004 |
| P2 | BIZ-CAP-006 | Brand List Retrieval | Active | Fix ARCH-VIOL-001 |
| P2 | BIZ-CAP-007 | Type List Retrieval | Active | Fix ARCH-VIOL-006 |
| P2 | BIZ-CAP-008 | Admin Browser Cache | Active | Preserve |
| P2 | BIZ-CAP-009 | DB Catalogue Seeding | Active | Preserve |
| P3 | BIZ-CAP-010 | Basket Item Addition | Active | Preserve |
| P3 | BIZ-CAP-011 | Basket Deletion | Active | Preserve |
| P3 | BIZ-CAP-012 | Anon-to-User Transfer | Active | Preserve |
| P3 | BIZ-CAP-013 | Basket Quantity Update | Active | Preserve |
| P3 | BIZ-CAP-014 | Basket Item Count Query | Active | Preserve |
| P3 | BIZ-CAP-015 | Basket View with Details | Active | Preserve |
| P3 | BIZ-CAP-016 | Get or Create Basket | Active | Preserve |
| P4 | BIZ-CAP-017 | Order Creation | Active — hardcoded address | AO-01 |
| P4 | BIZ-CAP-018 | Order Total Calculation | Active | Preserve |
| P4 | BIZ-CAP-019 | Order History Retrieval | Active | Preserve |
| P4 | BIZ-CAP-020 | Order Detail View | Active | Preserve |
| P5 | BIZ-CAP-027 | Email Notification (Stub) | NON-FUNCTIONAL | AO-02 |
| P5 | BIZ-CAP-028 | Generic Repository (EF) | Active | Refactor — reduce coupling |
| P5 | BIZ-CAP-029 | DB Seed on Startup | Active | Preserve |
| P6 | BIZ-CAP-030 | Buyer Account Structure | DORMANT | AO-05 (future) |
| P6 | BIZ-CAP-031 | Payment Method Record | DORMANT | AO-05 (future) |

---

*Business Capability Model — generated from ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline Foundation Layer).*
*All 31 BIZ-CAP nodes (BIZ-CAP-001..031) are covered.*
*Heat map: 20 Active-clean, 7 Active-with-defect, 1 Non-functional stub, 2 Dormant, 1 Critical infrastructure gap.*
