# Architecture Inventory — eShopOnWeb
**Source:** Foundation Synthesis Agent (BA-only run)
**Date:** 2026-06-30
**Status:** PARTIAL — DA, TA, AA layers absent; 3,000-char truncation per BA doc

---

## Section 1 — Business Layer Inventory

### 1.1 Business Capabilities (14 of 39 confirmed in this run)

| ID | Name | Domain | Actor(s) | Confidence |
|----|------|--------|----------|------------|
| BIZ-CAP-001 | Basket Item Addition | Basket | BIZ-ACT-001, BIZ-ACT-002 | HIGH |
| BIZ-CAP-002 | Basket Deletion | Basket | BIZ-ACT-003 | HIGH |
| BIZ-CAP-003 | Anonymous-to-User Basket Transfer | Basket | BIZ-ACT-003 | HIGH |
| BIZ-CAP-004 | Basket Item Quantity Update | Basket | BIZ-ACT-002 | HIGH |
| BIZ-CAP-005 | Basket Item Count Query | Basket | BIZ-ACT-002 | HIGH |
| BIZ-CAP-006 | Basket View with Product Details | Basket | BIZ-ACT-002 | HIGH |
| BIZ-CAP-007 | Get or Create Basket | Basket | BIZ-ACT-001, BIZ-ACT-002 | HIGH |
| BIZ-CAP-008 | Order Creation from Basket | Order | BIZ-ACT-003 | HIGH |
| BIZ-CAP-009 | Order Total Calculation | Order | BIZ-ACT-003 | HIGH |
| BIZ-CAP-010 | Order History Retrieval | Order | BIZ-ACT-002 | HIGH |
| BIZ-CAP-011 | Order Detail View | Order | BIZ-ACT-002 | HIGH |
| BIZ-CAP-012 | Paged Catalogue Browse | Catalog | BIZ-ACT-001, BIZ-ACT-002 | HIGH |
| BIZ-CAP-013 | Single Product Retrieval | Catalog | BIZ-ACT-001, BIZ-ACT-002 | HIGH |
| BIZ-CAP-014 | Admin Catalogue Product Creation | Catalog | BIZ-ACT-004 | HIGH |
| BIZ-CAP-015..039 | *(not visible — truncation)* | — | — | OQ-005 |

### 1.2 Business Actors (4 confirmed)

| ID | Actor | Auth Type |
|----|-------|-----------|
| BIZ-ACT-001 | Guest Shopper | Anonymous cookie |
| BIZ-ACT-002 | Registered Shopper | ASP.NET Core Identity session cookie |
| BIZ-ACT-003 | System | Internal |
| BIZ-ACT-004 | Administrator | JWT Bearer with role claim |

### 1.3 Business Processes (3 of 10 confirmed in this run)

| ID | Name | Domain | Steps | Trigger |
|----|------|--------|-------|---------|
| BIZ-PROC-001 | Place an Order at Checkout | Order | 9 | Shopper submits checkout form |
| BIZ-PROC-002 | View Order History and Order Detail | Order | 5 | Shopper navigates to My Orders |
| BIZ-PROC-003 | Shopper Purchase Journey (Value Stream) | Cross-domain | 7 stages | Visitor arrives at storefront |

### 1.4 Business Rules (11 of 37 confirmed in this run)

| ID | Rule Name | Domain | Type | Severity |
|----|-----------|--------|------|----------|
| BIZ-RULE-001 | Product Snapshot at Purchase | Order | Hard Constraint | High |
| BIZ-RULE-002 | Anonymous Basket Transfer at Login | Basket | Hard Constraint | High |
| BIZ-RULE-003 | Order Requires Non-Empty Basket | Order | Hard Constraint | High |
| BIZ-RULE-004 | Default Basket Quantity 1 | Basket | Soft Constraint | Low |
| BIZ-RULE-005 | Administrator-Only Catalogue Mutations | Catalog | Approval Gate | High |
| BIZ-RULE-006 | Checkout Requires Authentication | Basket | Hard Constraint | High |
| BIZ-RULE-007 | JWT-Based Admin Authentication | Identity | Compliance | High |
| BIZ-RULE-008 | **Email Notifications Disabled** | Infrastructure | **Defect** | **Critical** |
| BIZ-RULE-009 | **Mandatory 1-Second Catalogue API Delay** | Catalog | **Defect** | **Critical** |
| BIZ-RULE-010 | Admin Panel Product List Cache (1 min) | Catalog | Soft Constraint | Medium |
| BIZ-RULE-011 | Order BuyerId Equals Buyer IdentityGuid | Order | Hard Constraint | High |

---

## Section 2 — Data Layer Inventory

### 2.1 Domain Entities (12 confirmed — all from BA layer)

| ID | Name | Domain | Type | Aggregate | Confidence |
|----|------|--------|------|-----------|------------|
| DATA-ENT-001 | CatalogItem | Catalog | Entity (Root) | DATA-AGG-004 | HIGH |
| DATA-ENT-002 | CatalogBrand | Catalog | Entity | DATA-AGG-004 | HIGH |
| DATA-ENT-003 | CatalogType | Catalog | Entity | DATA-AGG-004 | HIGH |
| DATA-ENT-004 | Basket | Basket | Entity (Root) | DATA-AGG-001 | HIGH |
| DATA-ENT-005 | BasketItem | Basket | Entity | DATA-AGG-001 | HIGH |
| DATA-ENT-006 | Buyer | Buyer | Entity (Root) | DATA-AGG-003 | HIGH |
| DATA-ENT-007 | PaymentMethod | Buyer | Entity | DATA-AGG-003 | HIGH |
| DATA-ENT-008 | Order | Order | Entity (Root) | DATA-AGG-002 | HIGH |
| DATA-ENT-009 | OrderItem | Order | Entity | DATA-AGG-002 | HIGH |
| DATA-ENT-010 | Address | Order | Value Object | DATA-AGG-002 | HIGH |
| DATA-ENT-011 | CatalogItemOrdered | Order | Value Object | DATA-AGG-002 | HIGH |
| DATA-ENT-012 | ApplicationUser | Identity | Entity | — | HIGH (partial) |

### 2.2 Aggregates (4 confirmed)

| ID | Name | Root | Members | Confidence |
|----|------|------|---------|------------|
| DATA-AGG-001 | Basket Aggregate | DATA-ENT-004 | Basket, BasketItem | HIGH |
| DATA-AGG-002 | Order Aggregate | DATA-ENT-008 | Order, OrderItem, Address, CatalogItemOrdered | HIGH |
| DATA-AGG-003 | Buyer Aggregate | DATA-ENT-006 | Buyer, PaymentMethod | HIGH |
| DATA-AGG-004 | Catalog Pseudo-Aggregate | DATA-ENT-001 | CatalogItem, CatalogBrand, CatalogType | MEDIUM |

### 2.3 Repositories (4 inferred)

| ID | Name | Domain | Aggregate | Confidence |
|----|------|--------|-----------|------------|
| DATA-REPO-001 | IBasketRepository | Basket | DATA-AGG-001 | MEDIUM |
| DATA-REPO-002 | IOrderRepository | Order | DATA-AGG-002 | MEDIUM |
| DATA-REPO-003 | ICatalogItemRepository | Catalog | DATA-AGG-004 | MEDIUM |
| DATA-REPO-004 | IBuyerRepository | Buyer | DATA-AGG-003 | MEDIUM |

---

## Section 3 — Application Layer Inventory

### 3.1 Application Services (13 confirmed/inferred)

| ID | Name | Type | Domain | Confidence |
|----|------|------|--------|------------|
| APP-SVC-001 | BasketService | Service | Basket | HIGH |
| APP-SVC-002 | BasketQueryService | Service | Basket | HIGH |
| APP-SVC-003 | BasketViewModelService | Service | Basket | HIGH |
| APP-SVC-004 | OrderService | Service | Order | HIGH |
| APP-SVC-005 | GetMyOrdersHandler | Query Handler | Order | HIGH |
| APP-SVC-006 | GetOrderDetailsHandler | Query Handler | Order | HIGH |
| APP-SVC-007 | CachedCatalogItemServiceDecorator | Decorator | Catalog | HIGH |
| APP-SVC-008 | IdentityTokenClaimService | Service | Identity | HIGH |
| APP-SVC-009 | EmailSender | Infra Service (no-op stub) | Infrastructure | HIGH |
| APP-SVC-010 | CheckoutPageModel | Page Model | Order | HIGH |
| APP-SVC-011 | LoginPageModel | Page Model | Identity | HIGH |
| APP-SVC-012 | BasketIndexPageModel | Page Model | Basket | MEDIUM |
| APP-SVC-013 | Order Domain Total Calculation | Domain Logic | Order | HIGH |

### 3.2 APIs (5 confirmed)

| ID | Name | Method | Domain | Authorization | Confidence |
|----|------|--------|--------|---------------|------------|
| APP-API-001 | CatalogItemListPagedEndpoint | GET | Catalog | Open | HIGH |
| APP-API-002 | CatalogItemGetByIdEndpoint | GET | Catalog | Open | HIGH |
| APP-API-003 | CreateCatalogItemEndpoint | POST | Catalog | Administrator (JWT) | HIGH |
| APP-API-004 | UpdateCatalogItemEndpoint | PUT | Catalog | Administrator (JWT) | HIGH |
| APP-API-005 | DeleteCatalogItemEndpoint | DELETE | Catalog | Administrator (JWT) | HIGH |

### 3.3 Interfaces (4 inferred)

| ID | Name | Domain | Confidence |
|----|------|--------|------------|
| APP-IF-001 | IBasketService | Basket | MEDIUM |
| APP-IF-002 | IOrderService | Order | MEDIUM |
| APP-IF-003 | IBasketQueryService | Basket | MEDIUM |
| APP-IF-004 | ICatalogItemViewModelService | Catalog | MEDIUM |

### 3.4 Dependencies (2 confirmed/inferred)

| ID | Name | Type | Confidence |
|----|------|------|------------|
| APP-DEP-001 | Entity Framework Core | ORM | HIGH |
| APP-DEP-002 | MediatR | Messaging | MEDIUM |

---

## Section 4 — Technology Layer Inventory

### 4.1 Current Stack (4 confirmed from BA evidence)

| ID | Name | Type | Confidence |
|----|------|------|------------|
| TECH-CUR-001 | .NET / ASP.NET Core | Framework | HIGH |
| TECH-CUR-002 | Entity Framework Core | ORM | HIGH |
| TECH-CUR-003 | SQL Server | Database | HIGH |
| TECH-CUR-004 | JWT Bearer Authentication | Security Mechanism | HIGH |

### 4.2 Infrastructure (2 confirmed)

| ID | Name | Type | Confidence |
|----|------|------|------------|
| TECH-INF-001 | SQL Server Database Instance | Infrastructure | HIGH |
| TECH-INF-002 | Browser Local Storage | Client-Side Cache | HIGH |

### 4.3 Security Components (2 confirmed)

| ID | Name | Type | Confidence |
|----|------|------|------------|
| TECH-SEC-001 | Cookie-Based Session / Anonymous Basket Tracking | Security Component | HIGH |
| TECH-SEC-002 | Role-Based Authorization (RBAC) | Security Component | HIGH |

---

## Section 5 — Cross-Layer Dependency Summary

| From | To | Relationship | Confidence |
|------|----|-------------|------------|
| BIZ-CAP-001..004 | APP-SVC-001 | Implemented by BasketService | HIGH |
| BIZ-CAP-008 | APP-SVC-004 | Implemented by OrderService | HIGH |
| BIZ-CAP-012 | APP-API-001 | Exposed by CatalogItemListPagedEndpoint | HIGH |
| BIZ-PROC-001 | DATA-ENT-004, DATA-ENT-008 | Reads Basket, creates Order | HIGH |
| BIZ-RULE-001 | DATA-ENT-011 | Enforced by CatalogItemOrdered value object | HIGH |
| BIZ-RULE-005 | APP-API-003..005 | Guards catalogue mutation APIs | HIGH |
| DATA-ENT-005 | DATA-ENT-001 | BasketItem.CatalogItemId references CatalogItem | HIGH |
| DATA-ENT-009 | DATA-ENT-011 | OrderItem embeds CatalogItemOrdered snapshot | HIGH |
| DATA-ENT-008 | DATA-ENT-006 | Order.BuyerId == Buyer.IdentityGuid | HIGH |
| APP-SVC-007 | APP-IF-004 | Decorator pattern on ICatalogItemViewModelService | HIGH |
| APP-DEP-001 | TECH-CUR-003 | Entity Framework Core -> SQL Server | HIGH |
| TECH-SEC-002 | APP-API-003..005 | RBAC guards admin catalogue APIs | HIGH |

---

## Section 6 — Gap Register

| Gap | Root Cause | Resolution |
|-----|------------|-----------|
| 25 missing capabilities (BIZ-CAP-015..039) | BA doc truncation at 3,000 chars | Increase limit in foundation_runner.py |
| 26 missing business rules (BIZ-RULE-012..037) | BA doc truncation at 3,000 chars | Increase limit in foundation_runner.py |
| 7 missing processes | BA doc truncation at 3,000 chars | Increase limit in foundation_runner.py |
| Physical DB schema (DDL, migrations, indexes) | DA layer not provided | Run DA agents |
| DI wiring, service lifetimes, full API contracts | AA layer not provided | Run AA agents |
| Deployment topology, NFRs, container strategy | TA layer not provided | Run TA agents |
| GR-08 target stack decision | Stakeholder decision pending | User/stakeholder choice |
