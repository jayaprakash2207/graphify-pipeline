# Forward Engineering Input Map — eShopOnWeb
**Source:** Foundation Synthesis Agent (BA-only run)
**Date:** 2026-06-30
**Purpose:** Maps every graph node to the forward-engineering document(s) that consume it

## Doc Reference Key

| Doc | Title | Wave |
|-----|-------|------|
| 01 | BRD | — |
| 02 | Business Capability Model | — |
| 03 | Use Case Specification | — |
| 04 | Business Process Model | — |
| 05 | Domain Model (DDD) | Wave 2 |
| 06 | Data Dictionary | — |
| 07 | Data Model Specification + DDL | **Wave 1** |
| 08 | ERD | — |
| 09 | Data Flow Diagram | — |
| 10 | Service Catalog | Wave 3 |
| 11 | API Contract Specification | Wave 4 |
| 12 | Technology Blueprint | — |
| 13 | Security Architecture | — |
| 14 | NFR Specification | — |
| 15 | Forward Engineering Specification (89 rules, 68 gates) | Governance |
| 16 | Generation Manifest (machine-readable) | Governance |
| 17 | Forward Engineering Readiness Report | Governance |
| 18 | Deployment Architecture | — |
| 19 | Frontend Architecture | Wave 5 |
| 20 | UI/UX Specification | Wave 5 |

---

## Business Layer Nodes

### Business Capabilities

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| BIZ-CAP-001 | Basket Item Addition | 01 (BRD requirement), 02 (capability hierarchy), 03 (UC: add to basket), 10 (BasketService catalog entry), 15 (generation rules for basket), 16 (manifest: basket service wave) |
| BIZ-CAP-002 | Basket Deletion | 01, 02, 03 (UC: checkout completion), 10, 15, 16 |
| BIZ-CAP-003 | Anon-to-User Basket Transfer | 01, 02, 03 (UC: login + transfer), 04 (login process), 10, 13 (security — session cookie handoff), 15, 16 |
| BIZ-CAP-004 | Basket Item Qty Update | 01, 02, 03, 10, 15, 16 |
| BIZ-CAP-005 | Basket Item Count Query | 01, 02, 03, 10, 11 (API or query contract), 15, 16 |
| BIZ-CAP-006 | Basket View with Product Details | 01, 02, 03, 09 (DFD: catalog read for basket view), 10, 19 (basket page component), 20 (basket UI spec), 15, 16 |
| BIZ-CAP-007 | Get or Create Basket | 01, 02, 03, 10, 15, 16 |
| BIZ-CAP-008 | Order Creation from Basket | 01, 02, 03, 04 (checkout process), 09 (DFD: basket->order), 10, 11 (checkout API or page), 15, 16 |
| BIZ-CAP-009 | Order Total Calculation | 01, 02, 05 (domain logic in Order entity), 10, 15, 16 |
| BIZ-CAP-010 | Order History Retrieval | 01, 02, 03, 09, 10, 11, 19, 20, 15, 16 |
| BIZ-CAP-011 | Order Detail View | 01, 02, 03, 09, 10, 11, 19, 20, 15, 16 |
| BIZ-CAP-012 | Paged Catalogue Browse | 01, 02, 03, 09, 10, 11, 19, 20, 15, 16 |
| BIZ-CAP-013 | Single Product Retrieval | 01, 02, 03, 10, 11, 19, 20, 15, 16 |
| BIZ-CAP-014 | Admin Catalogue Product Creation | 01, 02, 03, 10, 11, 13 (admin JWT auth), 15, 16 |
| BIZ-CAP-015..039 | *(not visible — see OQ-005)* | 01, 02, 03 at minimum |

### Business Actors

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| BIZ-ACT-001 | Guest Shopper | 01 (stakeholder), 03 (use case actor), 13 (anonymous session handling), 19, 20 |
| BIZ-ACT-002 | Registered Shopper | 01, 03, 13 (auth requirements), 14 (user experience NFRs), 19, 20 |
| BIZ-ACT-003 | System | 04 (system steps in processes) |
| BIZ-ACT-004 | Administrator | 01, 03, 11 (admin API contracts), 13 (JWT, RBAC), 15, 16 |

### Business Processes

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| BIZ-PROC-001 | Place an Order at Checkout | 03, 04 (process flow diagram), 09 (DFD level 1), 10, 15, 16 |
| BIZ-PROC-002 | View Order History and Order Detail | 03, 04, 09, 10, 19, 20, 15, 16 |
| BIZ-PROC-003 | Shopper Purchase Journey (Value Stream) | 02, 03, 04, 09, 19, 20 |

### Business Rules

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| BIZ-RULE-001 | Product Snapshot at Purchase | 05 (CatalogItemOrdered value object), 06 (field: immutable), 07 (DDL: snapshot fields), 15 (rule to preserve in generation), 16 |
| BIZ-RULE-002 | Anon Basket Transfer at Login | 04 (login process), 10, 13 (session security), 15, 16 |
| BIZ-RULE-003 | Order Requires Non-Empty Basket | 05 (Order invariant), 10, 15, 16 |
| BIZ-RULE-004 | Default Basket Qty 1 | 05 (BasketItem default), 10, 15, 16 |
| BIZ-RULE-005 | Admin-Only Catalogue Mutations | 11 (API authorization spec), 13 (RBAC), 15, 16 |
| BIZ-RULE-006 | Checkout Requires Auth | 13 (authentication gate), 15, 16 |
| BIZ-RULE-007 | JWT Admin Auth | 11 (API security), 12 (tech blueprint), 13, 15, 16 |
| BIZ-RULE-008 | Email No-op Stub | 01 (BRD: email req gap), 12 (infra: email provider needed), 13, 15 (gate: resolve before generation), 17 (readiness report gap) |
| BIZ-RULE-009 | Mandatory 1-sec Catalogue Delay | 14 (NFR defect: must remove), 15 (gate: remove delay), 17 |
| BIZ-RULE-010 | Admin Cache 1-min | 10, 12, 14 (caching NFR), 15, 16 |
| BIZ-RULE-011 | Order BuyerId == Buyer IdentityGuid | 05 (domain identity link), 06, 07 (FK DDL), 08 (ERD), 15, 16 |

---

## Data Layer Nodes

### Domain Entities

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| DATA-ENT-001 | CatalogItem | 05 (entity), 06 (data dictionary), 07 (DDL: CatalogItems table), 08 (ERD), 10 (service reads), 11 (API response fields), 16 |
| DATA-ENT-002 | CatalogBrand | 05, 06, 07, 08, 11 (filter param), 16 |
| DATA-ENT-003 | CatalogType | 05, 06, 07, 08, 11 (filter param), 16 |
| DATA-ENT-004 | Basket | 05, 06, 07, 08, 09, 10, 16 |
| DATA-ENT-005 | BasketItem | 05, 06, 07, 08, 09, 10, 16 |
| DATA-ENT-006 | Buyer | 05, 06, 07, 08, 10, 16 |
| DATA-ENT-007 | PaymentMethod | 05, 06, 07 (tokenised CardId — security note), 08, 13 (PCI scope), 16 |
| DATA-ENT-008 | Order | 05, 06, 07, 08, 09, 10, 11, 16 |
| DATA-ENT-009 | OrderItem | 05, 06, 07, 08, 10, 11, 16 |
| DATA-ENT-010 | Address | 05, 06, 07, 08, 16 |
| DATA-ENT-011 | CatalogItemOrdered | 05 (value object, immutable), 06, 07 (DDL: embedded/owned), 08, 16 |
| DATA-ENT-012 | ApplicationUser | 05, 06, 07 (identity tables), 12 (ASP.NET Identity), 13 (auth config), 16 |

### Aggregates

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| DATA-AGG-001 | Basket Aggregate | 05 (DDD aggregate), 07 (aggregate root pattern in DDL), 10, 15, 16 |
| DATA-AGG-002 | Order Aggregate | 05, 07, 10, 15, 16 |
| DATA-AGG-003 | Buyer Aggregate | 05, 07, 10, 15, 16 |
| DATA-AGG-004 | Catalog Pseudo-Aggregate | 05, 07, 10, 15, 16 |

### Repositories

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| DATA-REPO-001 | IBasketRepository | 05 (repository interface), 10 (service catalog — DI binding), 15, 16 |
| DATA-REPO-002 | IOrderRepository | 05, 10, 15, 16 |
| DATA-REPO-003 | ICatalogItemRepository | 05, 10, 15, 16 |
| DATA-REPO-004 | IBuyerRepository | 05, 10, 15, 16 |

---

## Application Layer Nodes

### Application Services

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| APP-SVC-001 | BasketService | 10 (catalog entry), 11 (interfaces), 15, 16 |
| APP-SVC-002 | BasketQueryService | 10, 11, 15, 16 |
| APP-SVC-003 | BasketViewModelService | 10, 11, 19 (basket page view model), 15, 16 |
| APP-SVC-004 | OrderService | 10, 11, 15, 16 |
| APP-SVC-005 | GetMyOrdersHandler | 10, 11, 15, 16 |
| APP-SVC-006 | GetOrderDetailsHandler | 10, 11, 15, 16 |
| APP-SVC-007 | CachedCatalogItemServiceDecorator | 10, 12 (caching strategy), 14 (cache NFR), 15, 16 |
| APP-SVC-008 | IdentityTokenClaimService | 10, 12, 13, 15, 16 |
| APP-SVC-009 | EmailSender (no-op stub) | 10, 12 (email provider gap), 13, 15 (gate: resolve), 17 (readiness gap) |
| APP-SVC-010 | CheckoutPageModel | 10, 19 (checkout page), 20 (UI spec: checkout), 15, 16 |
| APP-SVC-011 | LoginPageModel | 10, 13, 19 (login page), 20, 15, 16 |
| APP-SVC-012 | BasketIndexPageModel | 10, 19, 20, 15, 16 |
| APP-SVC-013 | Order Domain Total Calculation | 05 (domain logic), 10, 15, 16 |

### APIs

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| APP-API-001 | CatalogItemListPagedEndpoint | 11 (full contract: request params, response schema), 13 (open endpoint), 14 (NFR: remove 1-sec delay), 15, 16 |
| APP-API-002 | CatalogItemGetByIdEndpoint | 11, 13, 15, 16 |
| APP-API-003 | CreateCatalogItemEndpoint | 11, 13 (JWT auth spec), 15, 16 |
| APP-API-004 | UpdateCatalogItemEndpoint | 11, 13, 15, 16 |
| APP-API-005 | DeleteCatalogItemEndpoint | 11, 13, 15, 16 |

### Interfaces

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| APP-IF-001 | IBasketService | 10, 15, 16 |
| APP-IF-002 | IOrderService | 10, 15, 16 |
| APP-IF-003 | IBasketQueryService | 10, 15, 16 |
| APP-IF-004 | ICatalogItemViewModelService | 10, 15, 16 |

### Dependencies

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| APP-DEP-001 | Entity Framework Core | 07 (DDL generated by/for EF), 12 (current stack), 15, 16 |
| APP-DEP-002 | MediatR (inferred) | 10, 12, 15, 16 |

---

## Technology Layer Nodes

### Current Stack

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| TECH-CUR-001 | .NET / ASP.NET Core | 12 (tech blueprint), 15, 16, 18 (deployment: .NET host) |
| TECH-CUR-002 | Entity Framework Core | 07 (DDL / migrations), 12, 15, 16 |
| TECH-CUR-003 | SQL Server | 07 (DDL: SQL Server dialect), 12, 14 (DB performance NFRs), 18, 15, 16 |
| TECH-CUR-004 | JWT Bearer Authentication | 11 (API security headers), 12, 13 (auth architecture), 15, 16 |

### Infrastructure

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| TECH-INF-001 | SQL Server Database Instance | 12, 14, 18 (deployment: DB instance spec) |
| TECH-INF-002 | Browser Local Storage | 12, 19 (frontend: admin panel cache), 20 |

### Security

| Node ID | Node Name | Consuming Documents |
|---------|-----------|---------------------|
| TECH-SEC-001 | Cookie-Based Session / Anon Basket Tracking | 13 (session security), 15, 16 |
| TECH-SEC-002 | Role-Based Authorization (RBAC) | 11 (API authorization), 13 (RBAC model), 15, 16 |

---

## Forward Engineering Wave Alignment Summary

| Wave | Doc(s) | Nodes It Consumes |
|------|--------|-------------------|
| Wave 1 (DDL) | 07 | DATA-ENT-001..012, DATA-AGG-001..004, APP-DEP-001, TECH-CUR-002, TECH-CUR-003 |
| Wave 2 (Domain) | 05 | DATA-ENT-001..012, DATA-AGG-001..004, DATA-REPO-001..004, BIZ-RULE-001..011 (invariants) |
| Wave 3 (Services) | 10 | APP-SVC-001..013, APP-IF-001..004, BIZ-CAP-001..014 |
| Wave 4 (APIs) | 11 | APP-API-001..005, APP-IF-001..004, BIZ-RULE-005..007, BIZ-ACT-004 |
| Wave 5 (Frontend) | 19, 20 | BIZ-CAP-001, 006, 010, 011, 012, 013, BIZ-ACT-001..002, APP-SVC-010..012 |
| Governance | 15, 16 | ALL nodes — generation rules and manifest reference every node |

---

*Nodes flagged as ASMP or OQ require the respective layer to be provided (DA, TA, AA) before their consuming document entries can be fully validated.*
