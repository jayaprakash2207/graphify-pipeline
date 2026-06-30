# Business Requirements Document (BRD)

**System:** eShopOnWeb
**Source of truth:** ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline/sample-output/foundation/)
**Generated:** 2026-06-30
**Pipeline stage:** Forward Engineering — Document 01 of 20
**Confidence schema:** HIGH = direct code evidence confirmed; MEDIUM = inferred from structure; LOW = assumed from convention

> Every requirement in this document traces to a node ID in ENTERPRISE_KNOWLEDGE_GRAPH.json. No capability, rule, actor, entity, or constraint is invented beyond what the foundation files confirm.

---

## 1. Executive Summary

eShopOnWeb is the official Microsoft ASP.NET Core reference e-commerce implementation demonstrating Clean Architecture (Onion Architecture), Domain-Driven Design aggregates, and the Repository pattern. It is a **teaching codebase with multiple production-blocking gaps** documented throughout this model.

The platform delivers a public-facing MVC storefront where shoppers browse a product catalogue, add items to a basket, and complete checkout into a confirmed order. A Blazor WebAssembly single-page admin panel (BlazorAdmin) is embedded in the Web host and calls a companion REST API (PublicApi) for product administration. Two SQL Server databases back the system: CatalogDatabase (products, baskets, orders) and IdentityDatabase (users, roles).

**Enterprise Knowledge Graph summary:**
- 31 business capabilities (BIZ-CAP-001..031)
- 7 business processes (BIZ-PROC-001..007)
- 6 actors (BIZ-ACT-001..006)
- 37 business rules (BIZ-RULE-001..037)
- 13 data entities (DATA-ENT-001..013)
- 4 DDD aggregates (DATA-AGG-001..004)
- 2 repositories (DATA-REPO-001..002)
- 14 application services (APP-SVC-001..014)
- 8 REST API endpoints (APP-API-001..008)
- 6 deployable/support interfaces (APP-IF-001..006)
- 173 total graph nodes

**Primary production blockers — must resolve before any real-world deployment:**

| # | Blocker | Rule | Severity |
|---|---------|------|----------|
| 1 | Hardcoded SA database password in docker-compose.yml (`@someThingComplicated1234`) | TECH-SEC-007 | CRITICAL |
| 2 | Hardcoded JWT signing key in source code (`SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes`) | BIZ-RULE-032 | CRITICAL |
| 3 | Hardcoded seeded account passwords (`Pass@word1` for demo and admin) | BIZ-RULE-029 | CRITICAL |
| 4 | All orders record the same hardcoded shipping address (123 Main St., Kent, OH, 44240) | BIZ-RULE-015 | CRITICAL |
| 5 | Email notification system is entirely non-functional — EmailSender.cs returns immediately | BIZ-RULE-008 | CRITICAL |
| 6 | Every catalogue browse request includes a mandatory 1-second artificial delay (`await Task.Delay(1000)`) | BIZ-RULE-009 | CRITICAL |

---

## 2. Business Goals

Goals are derived from the capability hierarchy, process models, actor operating models, and the three value streams evidenced in the graph (VS-001 Shopper Purchase Journey, VS-002 Catalogue Lifecycle, VS-003 New User Onboarding).

| Goal ID | Business Goal | Derived From |
|---------|--------------|--------------|
| **G-01** | Enable self-service product discovery — let customers and anonymous shoppers browse and find products by brand and type, with paged results. | BIZ-CAP-001..009; BIZ-PROC-001; VS-001 stage 1; BIZ-ACT-001, BIZ-ACT-002 |
| **G-02** | Provide a reliable shopping basket — allow items to be added, quantities adjusted, and carts managed with session continuity across anonymous-to-registered transitions. | BIZ-CAP-010..016; BIZ-PROC-003, BIZ-PROC-004; BIZ-RULE-002, BIZ-RULE-004, BIZ-RULE-016 |
| **G-03** | Convert baskets into confirmed, correctly-priced orders — perform checkout with item snapshotting, shipping address capture, empty-basket protection, and total calculation. | BIZ-CAP-017..020; BIZ-PROC-001; BIZ-RULE-001, BIZ-RULE-003, BIZ-RULE-012 |
| **G-04** | Secure access through identity and authentication — authenticate users, issue tokens, enforce role-based access, seed identity data, and protect customer order isolation. | BIZ-CAP-021..026; BIZ-PROC-006; BIZ-RULE-005, BIZ-RULE-006, BIZ-RULE-007, BIZ-RULE-024, BIZ-RULE-025 |
| **G-05** | Empower back-office catalogue administration — let administrators list, create, update, and delete catalogue products with cache-consistent results. | BIZ-CAP-003..005, BIZ-CAP-008; BIZ-PROC-005; BIZ-RULE-020, BIZ-RULE-021, BIZ-RULE-022, BIZ-RULE-023 |
| **G-06** | Maintain a trusted operational platform — seed reference data on startup, enforce invariants at object creation, and support reliable database migration. | BIZ-CAP-009, BIZ-CAP-026, BIZ-CAP-028, BIZ-CAP-029; BIZ-PROC-007; BIZ-RULE-014, BIZ-RULE-036, BIZ-RULE-037 |
| **G-07** | (Future) Enable payment processing and buyer profile management — capture buyer records and payment method tokens (PCI-compliant) for end-to-end purchase completion. | BIZ-CAP-030, BIZ-CAP-031; BIZ-RULE-034, BIZ-RULE-035; DATA-AGG-003 (DORMANT) |

> **G-07 is OUT of current scope.** BIZ-CAP-030 and BIZ-CAP-031 are DORMANT — no service layer or DbSet exists. DATA-ENT-008 (Buyer) and DATA-ENT-009 (PaymentMethod) are structurally defined but entirely dormant per BIZ-RULE-035.

---

## 3. Business Drivers

| Driver ID | Driver | Evidence Basis |
|-----------|--------|----------------|
| **D-01** | **Self-service customer experience.** The operating model assigns customers a self-service role spanning browse, basket, and order without staff involvement. | BIZ-ACT-001; BIZ-ACT-002; VS-001 |
| **D-02** | **Frictionless conversion from anonymous to registered shopping.** Anonymous baskets must survive the login event to avoid losing carts at the point of conversion. | BIZ-CAP-012; BIZ-PROC-004; BIZ-RULE-002; Login.cshtml.cs:83-114 |
| **D-03** | **Order integrity and pricing correctness.** Orders must capture an immutable snapshot of product state at checkout and compute totals deterministically, immune to future catalogue changes. | BIZ-RULE-001; DATA-ENT-012 (CatalogItemOrdered snapshot); BIZ-RULE-012 |
| **D-04** | **Trusted access control.** Authentication, token issuance, and role/claims-based authorisation are prerequisites for basket transfer, order creation, and admin operations. | BIZ-CAP-021..026; BIZ-RULE-005, BIZ-RULE-007; BIZ-PROC-006 |
| **D-05** | **Operational catalogue agility.** Administrators need a dedicated back-office to keep product content current, with cache refresh so changes are reflected to storefront shoppers. | BIZ-CAP-003..005, BIZ-CAP-008; VS-002; BIZ-ACT-003 |
| **D-06** | **Reliable automated operations.** The system startup process performs database seeding with retry logic to ensure a consistent initial state without manual operator intervention. | BIZ-CAP-009, BIZ-CAP-029; BIZ-RULE-036; BIZ-PROC-007 |
| **D-07** | **Security and compliance hardening.** Multiple Critical-severity findings (hardcoded credentials, non-functional email confirmation, XSS-exposed JWT token) must be resolved before production deployment. | BIZ-RULE-008, BIZ-RULE-013, BIZ-RULE-027, BIZ-RULE-029, BIZ-RULE-032; TECH-SEC-007 |
| **D-08** | **PCI-compliant payment readiness.** The dormant BuyerAggregate and PaymentMethod entity contain PCI-compliance comments; activation requires integration with a PCI-compliant payment processor token, never raw card data. | BIZ-RULE-034; DATA-ENT-009; PaymentMethod.cs:7 |

---

## 4. Scope

### 4.1 In Scope

| Domain | Capabilities | Processes | Key Business Rules |
|--------|-------------|------------|-------------------|
| Catalogue browsing and retrieval | BIZ-CAP-001, BIZ-CAP-002, BIZ-CAP-006, BIZ-CAP-007 | BIZ-PROC-001 | BIZ-RULE-009 (defect — must fix), BIZ-RULE-031 |
| Admin catalogue management | BIZ-CAP-003, BIZ-CAP-004, BIZ-CAP-005, BIZ-CAP-008, BIZ-CAP-009 | BIZ-PROC-005 | BIZ-RULE-005, BIZ-RULE-020, BIZ-RULE-021, BIZ-RULE-022, BIZ-RULE-023 |
| Basket lifecycle | BIZ-CAP-010..016 | BIZ-PROC-003, BIZ-PROC-004 | BIZ-RULE-002, BIZ-RULE-004, BIZ-RULE-016, BIZ-RULE-017, BIZ-RULE-026 |
| Order creation and history | BIZ-CAP-017..020 | BIZ-PROC-001, BIZ-PROC-002 | BIZ-RULE-001, BIZ-RULE-003, BIZ-RULE-011, BIZ-RULE-012, BIZ-RULE-015 (gap), BIZ-RULE-018, BIZ-RULE-019, BIZ-RULE-033 |
| Identity and authentication | BIZ-CAP-021..026 | BIZ-PROC-006 | BIZ-RULE-006, BIZ-RULE-007, BIZ-RULE-013 (gap), BIZ-RULE-024, BIZ-RULE-025, BIZ-RULE-027 (gap), BIZ-RULE-028, BIZ-RULE-029 (gap), BIZ-RULE-032 (gap) |
| Infrastructure (seeding, repository, caching) | BIZ-CAP-028, BIZ-CAP-029 | BIZ-PROC-007 | BIZ-RULE-014, BIZ-RULE-036, BIZ-RULE-037 |
| Non-functional stub documentation | BIZ-CAP-027 | — | BIZ-RULE-008 (email non-functional stub) |

### 4.2 Out of Scope (Current) / Future

| Item | Status | Reason |
|------|--------|--------|
| **Buyer Account Structure** (BIZ-CAP-030) | DORMANT | BuyerAggregate not in CatalogContext DbSet; no service layer. DATA-ENT-008 confirmed dead. BIZ-RULE-035. |
| **Payment Method Record** (BIZ-CAP-031) | DORMANT | PaymentMethod.cs structurally defined but no service, endpoint, or DbSet. BIZ-RULE-034. |
| **Payment processing integration** | Future — AO-05 | Requires PCI-compliant processor (Stripe/Braintree) and Buyer aggregate activation. |
| **Order status lifecycle** | Future — AO-06 | Orders are currently immutable with no status field per BIZ-RULE-012. |
| **Inventory management** | Future — AO-07 | AvailableStock field exists on CatalogItem but no checkout validation rule exists. |
| **Multi-currency pricing** | Not evidenced | Price/UnitPrice are bare decimals; no currency attribute on any entity. |

---

## 5. Stakeholders

| Actor ID | Stakeholder | Type | Role and Interest | Authentication Mechanism |
|----------|-------------|------|-------------------|--------------------------|
| **BIZ-ACT-001** | Guest Shopper (Anonymous) | Human | Browses catalogue, builds anonymous basket (10-year GUID cookie). No authentication required to add to basket. Cannot check out. | GUID cookie — 10-year, marked essential, not subject to consent banners (BIZ-RULE-016) |
| **BIZ-ACT-002** | Registered Shopper (Authenticated) | Human | All of BIZ-ACT-001 plus: checks out, views own order history. Cannot view other accounts' orders (BIZ-RULE-030). | ASP.NET Core Identity cookie (Web) or JWT token (API) |
| **BIZ-ACT-003** | Product Administrator | Human | Manages product catalogue via BlazorAdmin SPA. Has ADMINISTRATORS role. Can create, update, and delete catalogue items. | JWT token — 7-day expiry (BIZ-RULE-024); role string confirmed as 'Administrators' (BIZ-RULE-005) |
| **BIZ-ACT-004** | Demo Shopper (demouser@microsoft.com) | Human (Seeded) | Pre-seeded account for demonstration. **Must not use in production** — password is hardcoded plaintext (BIZ-RULE-029). | Same as BIZ-ACT-002; password `Pass@word1` hardcoded |
| **BIZ-ACT-005** | Seeded Administrator (admin@microsoft.com) | Human (Seeded) | Pre-seeded admin account. **Must not use in production** — password is hardcoded plaintext (BIZ-RULE-013). | Same as BIZ-ACT-003; password `Pass@word1` hardcoded |
| **BIZ-ACT-006** | Application Startup Process | System | Performs database seeding for catalogue (BIZ-RULE-036) and identity (BIZ-RULE-037) on startup. No human operator required. | Internal — runs as application startup sequence |

---

## 6. Business Rules — Complete Inventory (BIZ-RULE-001..037)

All 37 business rules, sourced directly from the Enterprise Knowledge Graph `business.rules` array.

### 6.1 Order Domain Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-001** | Order records snapshot product name, picture, and catalogue ID at purchase time. Future catalogue changes do not alter order history. | High | Hard Constraint | CatalogItemOrdered.cs; OrderService.cs |
| **BIZ-RULE-003** | Placing an order requires a non-empty basket. Basket permanently deleted after order saved. | High | Hard Constraint | OrderService.CreateOrderAsync |
| **BIZ-RULE-011** | Order.BuyerId matches Buyer.IdentityGuid by string value convention — no database foreign key. | Medium | Soft Constraint | OrderConfiguration.cs; Buyer.cs |
| **BIZ-RULE-012** | Orders have no status field. Once created, orders are immutable and cannot be updated, cancelled, or progressed. | Medium | Hard Constraint | Order.cs — no status property |
| **BIZ-RULE-015** | All orders record hardcoded shipping address: 123 Main St., Kent, OH, United States, 44240. | **Critical** | Hard Constraint (Gap) | Checkout.cshtml.cs:57 |
| **BIZ-RULE-018** | Only authenticated shoppers may access checkout — unauthenticated visitors redirected to login. | High | Approval Gate | Checkout.cshtml.cs [Authorize] |
| **BIZ-RULE-019** | Basket must contain at least one item to proceed to checkout. | High | Hard Constraint | GuardExtensions.cs EmptyBasketOnCheckout |
| **BIZ-RULE-030** | Shoppers can only view their own order history and order detail — other accounts return not-found. | High | Compliance | OrderController.cs; GetOrderDetailsHandler.cs |
| **BIZ-RULE-033** | Shipping address fields have database-enforced max lengths: postcode 18, street 180, state 60, country 90, city 100 characters. | Medium | Hard Constraint | OrderConfiguration.cs |

### 6.2 Basket Domain Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-002** | On login, anonymous basket items merge into account basket; anonymous basket permanently deleted. | High | Hard Constraint | Login.cshtml.cs; BasketService.TransferBasketAsync |
| **BIZ-RULE-004** | Basket add without explicit quantity defaults to quantity 1. | Low | Soft Constraint | BasketService.AddItemToBasket |
| **BIZ-RULE-006** | Anonymous shoppers may add to basket; only authenticated shoppers may proceed to checkout. | High | Hard Constraint | Checkout.cshtml.cs [Authorize] |
| **BIZ-RULE-016** | Anonymous shoppers identified by 10-year GUID cookie marked as essential and not subject to consent banners. | High | Compliance | Basket/Index.cshtml.cs:94-96 |
| **BIZ-RULE-017** | Basket transfer at login only occurs if cookie value is a valid GUID. | Medium | Hard Constraint | Login.cshtml.cs:111 |
| **BIZ-RULE-026** | Checkout form submission updates basket item quantities before order is created. | Medium | Soft Constraint | Checkout.cshtml.cs:55-57 |

### 6.3 Catalogue Domain Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-005** | Only ADMINISTRATORS role may create, update, or delete catalogue products. | High | Approval Gate | [Authorize(Roles = 'ADMINISTRATORS')] on write endpoints |
| **BIZ-RULE-009** | Every catalogue browse API request includes a mandatory 1-second artificial delay. This is a known performance defect. | **Critical** | Performance Defect | CatalogItemListPagedEndpoint.cs:42 `await Task.Delay(1000)` |
| **BIZ-RULE-010** | Admin panel caches product list in browser localStorage for 1 minute; any write immediately clears and reloads. | Medium | Soft Constraint | CachedCatalogItemServiceDecorator.cs; DA confirmed 1-min TTL |
| **BIZ-RULE-020** | Catalogue product names must be unique. | High | Hard Constraint | CreateCatalogItemEndpoint.cs:43-47 |
| **BIZ-RULE-021** | Catalogue product price must be greater than zero. | High | Hard Constraint | Guard.Against.NegativeOrZero |
| **BIZ-RULE-022** | Product name and description must not be empty at creation and update. | High | Hard Constraint | Guard.Against.NullOrEmpty |
| **BIZ-RULE-023** | New catalogue products always receive a default placeholder image; direct image upload from admin UI is permanently disabled. | Medium | Hard Constraint | CreateCatalogItemEndpoint.cs:59 |
| **BIZ-RULE-031** | Initial catalogue seeded with 5 brands, 4 types, 12 products — skipped if data already exists. | Low | Soft Constraint | CatalogContextSeed.cs |

### 6.4 Identity Domain Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-007** | Admin API authentication uses JWT tokens carrying user name and all assigned roles as claims. | High | Compliance | IdentityTokenClaimService.cs |
| **BIZ-RULE-013** | Demo shopper and administrator accounts seeded on startup with hardcoded default password. | **Critical** | Security Risk | AuthorizationConstants.cs:8 |
| **BIZ-RULE-024** | JWT tokens expire 7 days after issue. | Medium | SLA | IdentityTokenClaimService.cs:41 |
| **BIZ-RULE-025** | Account lockout enabled — repeated failed password attempts lock the account. | High | Compliance | AuthenticateEndpoint.cs:44; Login.cshtml.cs:77 |
| **BIZ-RULE-027** | New user registration does not require email confirmation — account activated immediately after registration. | **Critical** | Compliance Gap | Register.cshtml.cs:77-88 |
| **BIZ-RULE-028** | Registration requires valid email, password 6-100 characters, and matching confirmation password. | High | Hard Constraint | Register.cshtml.cs InputModel |
| **BIZ-RULE-029** | Default seeded account passwords are hardcoded plaintext constants in source code — must not use in production. | **Critical** | Security Risk | AuthorizationConstants.cs:8 — explicit TODO comment |
| **BIZ-RULE-032** | JWT signing secret key hardcoded as plaintext constant in source code — must not use in production. | **Critical** | Security Risk | AuthorizationConstants.cs:12 — explicit TODO comment |

### 6.5 Buyer Domain Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-034** | Payment method must never store full card details — only PCI-compliant token, alias, and last 4 digits. | **Critical** | Compliance | PaymentMethod.cs:7 — explicit PCI comment referencing Stripe |
| **BIZ-RULE-035** | Buyer aggregate and PaymentMethod entity are structurally defined but entirely dormant — no active service layer creates or queries them. | Medium | Structural Gap | DA confirmed DEAD — not registered in CatalogContext |

### 6.6 Infrastructure and Application Rules

| Rule ID | Rule | Severity | Type | Evidence |
|---------|------|----------|------|----------|
| **BIZ-RULE-008** | Email notification system is non-functional — all send calls silently return without delivering any message. | **Critical** | Compliance Gap | EmailSender.cs returns Task.CompletedTask |
| **BIZ-RULE-014** | Domain entity constructors use guard clauses to enforce invariants at object creation, before data reaches database. | High | Hard Constraint | GuardExtensions.cs |
| **BIZ-RULE-036** | Catalogue seeding retries up to 10 times on database failure before aborting application startup. | Medium | SLA | CatalogContextSeed.cs:50-56 |
| **BIZ-RULE-037** | Identity seeding does not check if ADMINISTRATORS role exists before creating it — produces duplicate role error on restart. | Medium | Soft Constraint (Bug) | AppIdentityDbContextSeed.cs:18 |

---

## 7. Assumptions

### 7.1 Foundation Assumptions (from Enterprise Knowledge Graph)

| ID | Assumption | Confidence | Impact |
|----|-----------|------------|--------|
| **ASMP-001** | BuyerId in Basket and Order stores the user's email address, not a GUID. Unit test evidence uses `testuser@microsoft.com` as BuyerId. | MEDIUM | If confirmed, PII sensitivity of Orders.BuyerId and Baskets.BuyerId should be elevated to HIGH |
| **ASMP-002** | No GDPR right-to-erasure workflow exists in the codebase. | MEDIUM | Significant compliance gap if confirmed absent |
| **ASMP-003** | Azure SQL Edge EOL container is used only for local development — production uses Azure SQL Database. | MEDIUM | If Azure SQL Edge is in production, security patch coverage gap |
| **ASMP-004** | A CORS policy for BlazorAdmin-to-PublicApi cross-origin calls exists in Program.cs startup code. | MEDIUM | If absent, browser blocks all cross-origin admin API calls |
| **ASMP-005** | Swagger UI is gated behind IsDevelopment() check — not served in production. | MEDIUM | If not gated, full API surface map is publicly accessible |
| **ASMP-006** | No scheduled jobs, background services, or message queue consumers exist. | MEDIUM | If a basket expiry job exists but was not captured, abandoned basket accumulation risk may already be addressed |
| **ASMP-007** | The system is the well-known eShopOnWeb Microsoft reference implementation. The AA pipeline reported system_name as 'unknown'. | HIGH | Naming only; no node semantics affected |

### 7.2 Forward-Engineering Assumptions

| ID | Assumption | Basis |
|----|-----------|-------|
| **ASMP-FE-001** | Buyer/Payment capabilities (BIZ-CAP-030, BIZ-CAP-031) require an explicit activation decision before any persistence is generated. | BIZ-RULE-035; DATA-AGG-003 DORMANT |
| **ASMP-FE-002** | Multi-currency pricing is not derivable from current evidence — Price/UnitPrice are bare decimals. | No currency attribute on any entity |
| **ASMP-FE-003** | Business goals G-01..G-06 are inferred from capabilities, processes, actors, and value-stream evidence — no separate motivation_model node exists in the graph. | Foundation metadata |
| **ASMP-FE-004** | The modernisation programme team (architects, platform owners) is an implicit stakeholder set not represented as a BIZ-ACT node. | No engineering actor in business.actors |

---

## 8. Constraints

| ID | Constraint | Evidence |
|----|-----------|---------|
| **C-01** | All 11 architecture violations (ARCH-VIOL-001..011) must be addressed before contexts can deploy independently. Notably: 6 PublicApi endpoints depend directly on EfRepository, bypassing domain service abstraction. | ARCH-VIOL-001..009 |
| **C-02** | Module dependency cycle detected: Admin → ApplicationCore → Basket → Catalog → DataAccess → Identity → Order → Web. Must be broken before independent module deployment. | ARCH-VIOL-008 |
| **C-03** | ApplicationCore references BlazorShared — domain layer depends on UI-shared library, violating the Clean Architecture dependency rule. | ARCH-VIOL-011 |
| **C-04** | Shared CatalogContext persists Catalog, Basket, and Order entities in one DbContext — one persistence boundary crossing three functional domains. Must be split per domain. | DATA-REPO-001 |
| **C-05** | Azure SQL Edge (sqlserver Docker container) reached end-of-life March 2025. Must be replaced with SQL Server 2022 before any networked deployment. | TECH-INF-003 |
| **C-06** | Docker Compose `depends_on` has no health-gate — startup race condition exists where application containers may start before SQL Server is ready. | TECH-INF-003 |
| **C-07** | BlazorAdmin JWT token is stored in browser localStorage — accessible via XSS attack, exposing admin credentials. | TECH-CUR-012 |
| **C-08** | Identity password minimum length of 6 characters is below NIST SP 800-63B minimum of 8. | nfr_registry.undeclared_framework_defaults |
| **C-09** | No retry or circuit-breaker pattern on BlazorAdmin HTTP calls to PublicApi — transient failures cause immediate user-facing errors. | nfr_registry.nfr_gaps |
| **C-10** | No health check endpoints confirmed in either service — cannot distinguish healthy/unhealthy containers in orchestration. | nfr_registry.nfr_gaps |

---

## 9. Success Criteria

Measurable, behaviour-preserving criteria tied to the 31 capabilities and 7 processes. Scope is implemented capabilities only (BIZ-RULE-035 dormant capabilities excluded from acceptance criteria).

| ID | Success Criterion | Tied Capabilities/Processes |
|----|------------------|-----------------------------|
| **SC-01** | Paged catalogue browse returns correct product/brand/type data for all 12 seeded products, with zero regressions. The mandatory 1-second artificial delay (BIZ-RULE-009) is **removed** in the forward-engineered system. | BIZ-CAP-001, BIZ-CAP-006, BIZ-CAP-007; BIZ-PROC-001 |
| **SC-02** | Admin can create, update, and delete catalogue products with name uniqueness (BIZ-RULE-020), price > 0 (BIZ-RULE-021), non-empty name/description (BIZ-RULE-022), and default image assignment (BIZ-RULE-023) enforced in 100% of tested cases. | BIZ-CAP-003, BIZ-CAP-004, BIZ-CAP-005; BIZ-PROC-005 |
| **SC-03** | Basket operations: add to basket defaults to qty 1 (BIZ-RULE-004), auto-merges on duplicate, anonymous-to-user transfer loses 0 items (BIZ-RULE-002), GUID validation enforced (BIZ-RULE-017). | BIZ-CAP-010..016; BIZ-PROC-003, BIZ-PROC-004 |
| **SC-04** | Checkout produces an order only for non-empty authenticated baskets, with immutable product snapshot (BIZ-RULE-001), correct buyer reference (BIZ-RULE-011), and shipping address **collected from user** (replaces BIZ-RULE-015 hardcoded gap). | BIZ-CAP-017..020; BIZ-PROC-001, BIZ-PROC-002 |
| **SC-05** | JWT authentication issues a signed token with identity + role claims for valid, non-locked-out credentials (BIZ-RULE-007). Token expires in exactly 7 days (BIZ-RULE-024). Account lockout enforced after failed attempts (BIZ-RULE-025). JWT signing key is **externalised to environment variable or secrets manager** (replaces BIZ-RULE-032 gap). | BIZ-CAP-021..023; BIZ-PROC-006 |
| **SC-06** | User registration activates account with **email confirmation required** (replaces BIZ-RULE-027 gap). Seeded account passwords are **externalised** (replaces BIZ-RULE-029 gap). | BIZ-CAP-024; BIZ-PROC-006 |
| **SC-07** | Order history returns only the requesting shopper's orders — cross-account access returns not-found in 100% of tested cases (BIZ-RULE-030). | BIZ-CAP-019, BIZ-CAP-020 |
| **SC-08** | All 8 REST API endpoints (APP-API-001..008) retain equivalent observable behaviour post-modernisation; ADMINISTRATORS role enforcement confirmed on all write endpoints. | APP-API-001..008; BIZ-RULE-005 |
| **SC-09** | Architecture violations ARCH-VIOL-001..007 (direct endpoint → EfRepository dependencies) are eliminated — endpoints route through domain service abstractions. | ARCH-VIOL-001..007 |
| **SC-10** | All Critical-severity security gaps resolved: JWT key externalised (BIZ-RULE-032), seeded passwords externalised (BIZ-RULE-029, BIZ-RULE-013), SA password externalised (TECH-SEC-007), email confirmation activated (BIZ-RULE-027), artificial delay removed (BIZ-RULE-009). | TECH-SEC-007; BIZ-RULE-008, 009, 013, 027, 029, 032 |

---

## 10. Traceability Matrix — Goals to Capabilities

| Goal | BIZ-CAP IDs | Supporting BIZ-PROC IDs | Domain |
|------|------------|------------------------|--------|
| **G-01** Self-service discovery | BIZ-CAP-001, 002, 006, 007 | BIZ-PROC-001 | Catalog |
| **G-02** Reliable basket | BIZ-CAP-010, 011, 012, 013, 014, 015, 016 | BIZ-PROC-003, BIZ-PROC-004 | Basket |
| **G-03** Basket to order | BIZ-CAP-017, 018, 019, 020 | BIZ-PROC-001, BIZ-PROC-002 | Order |
| **G-04** Secure access | BIZ-CAP-021, 022, 023, 024, 025, 026 | BIZ-PROC-006 | Identity |
| **G-05** Catalogue admin | BIZ-CAP-003, 004, 005, 008, 009 | BIZ-PROC-005 | Catalog / Admin |
| **G-06** Trusted operations | BIZ-CAP-028, 029 | BIZ-PROC-007 | Infrastructure |
| **G-07** *(Future)* Payment | BIZ-CAP-030, 031 | — | Buyer (DORMANT) |

---

## 11. Production Readiness Roadmap

Derived from the Enterprise Knowledge Graph `business.roadmap` section.

### Wave 1 — Critical Blockers (AO-01..05)

| ID | Action | Effort | Evidence |
|----|--------|--------|---------|
| **AO-01** | Collect shipping address at checkout — replace BIZ-RULE-015 hardcoded address with a user-input form | Medium | Checkout.cshtml.cs:57 |
| **AO-02** | Implement transactional email delivery (SendGrid or SMTP) — replace BIZ-RULE-008 non-functional stub | Low-Medium | EmailSender.cs |
| **AO-03** | Externalise secrets: move JWT key (BIZ-RULE-032) and default passwords (BIZ-RULE-029) to environment variables or Azure Key Vault | Low | AuthorizationConstants.cs |
| **AO-04** | Remove 1-second artificial catalogue delay — delete `await Task.Delay(1000)` from CatalogItemListPagedEndpoint.cs:42 | Minimal | BIZ-RULE-009 |
| **AO-05** | Integrate payment processing: activate BuyerAggregate with Stripe or Braintree (PCI-compliant) | High | BIZ-RULE-034; DATA-AGG-003 |

### Wave 2 — High Priority (AO-06..08)

| ID | Action | Effort |
|----|--------|--------|
| **AO-06** | Add order status lifecycle: PLACED → PROCESSING → SHIPPED → DELIVERED → CANCELLED | High |
| **AO-07** | Add inventory management: StockQuantity validation at checkout | High |
| **AO-08** | Enforce email confirmation after AO-02 complete | Low-Medium |

### Wave 3 — Medium Priority (AO-09..10)

| ID | Action | Effort |
|----|--------|--------|
| **AO-09** | Fix identity seeding idempotency: wrap role creation in existence check (BIZ-RULE-037) | Minimal |
| **AO-10** | Cache brand and type lookups separately in BlazorAdmin | Low |

---

## Appendix A — Open Questions

| OQ | Question | Priority | Impact |
|----|---------|----------|--------|
| **OQ-001** | Does BuyerId in Basket and Order store the user's email address or GUID? | HIGH | Affects PII sensitivity classification |
| **OQ-002** | Is there a GDPR right-to-erasure / user deletion workflow? | HIGH | Significant GDPR compliance gap if absent |
| **OQ-003** | What is the data retention policy for Orders and OrderItems (financial records)? | HIGH | Legal/compliance requirement |
| **OQ-004** | Does SQL Server TDE apply to either database in any deployment environment? | MEDIUM | Determines encrypted-at-rest status for all PII fields |
| **OQ-005** | Are seeded demo credentials rotated before any non-local deployment? | HIGH | Security blocker — repo access can forge valid JWT tokens |
| **OQ-006** | Is there a basket expiry or purge mechanism not found in the extracted source tree? | MEDIUM | If absent, abandoned baskets accumulate indefinitely |
| **OQ-007** | Is Redis planned as a distributed cache? (infra/abbreviations.json defines a Redis naming prefix) | LOW | Determines whether caching strategy should be redesigned for multi-instance |
| **OQ-008** | What PCI-compliant payment processor is planned for the dormant BuyerAggregate? | LOW | Architecture decision required before implementing AO-05 |

---

*Business Requirements Document — generated from ENTERPRISE_KNOWLEDGE_GRAPH.json (graphify-pipeline Foundation Layer).*
*Every fact in this document traces to a specific graph node ID and source file evidence reference.*
*Node count basis: 31 BIZ-CAP, 7 BIZ-PROC, 6 BIZ-ACT, 37 BIZ-RULE, 173 total graph nodes.*
