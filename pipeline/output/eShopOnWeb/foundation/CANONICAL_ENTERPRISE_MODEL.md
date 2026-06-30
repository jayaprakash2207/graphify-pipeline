# Canonical Enterprise Model — eShopOnWeb
**Source:** Foundation Synthesis Agent (BA-only run)
**Date:** 2026-06-30
**Status:** PARTIAL — DA, TA, AA layers absent; BA layer truncated at 3,000 chars/file

---

## 1. Bounded Contexts (Canonical Domain Boundaries)

| Domain | Aggregate Root(s) | Entities | Value Objects | Cross-Domain Dependencies |
|--------|-------------------|----------|---------------|--------------------------|
| **Catalog** | CatalogItem (DATA-ENT-001) | CatalogBrand, CatalogType | — | Referenced by Basket (by ID), snapshotted into Order |
| **Basket** | Basket (DATA-ENT-004) | BasketItem | — | Reads CatalogItem by ID; consumed by Order at checkout |
| **Order** | Order (DATA-ENT-008) | OrderItem | Address, CatalogItemOrdered | Snapshot of CatalogItem; references Buyer.IdentityGuid |
| **Buyer** | Buyer (DATA-ENT-006) | PaymentMethod | — | IdentityGuid ties to Identity domain |
| **Identity** | ApplicationUser (DATA-ENT-012) | — | — | IdentityGuid propagated to Buyer and Basket.BuyerId |

---

## 2. Canonical Entity Registry

| Node ID | Name | Type | Domain | Confidence | Primary Evidence |
|---------|------|------|--------|------------|-----------------|
| DATA-ENT-001 | CatalogItem | Entity (Aggregate Root) | Catalog | HIGH | 05_data_model.md |
| DATA-ENT-002 | CatalogBrand | Entity | Catalog | HIGH | 05_data_model.md |
| DATA-ENT-003 | CatalogType | Entity | Catalog | HIGH | 05_data_model.md |
| DATA-ENT-004 | Basket | Entity (Aggregate Root) | Basket | HIGH | 05_data_model.md |
| DATA-ENT-005 | BasketItem | Entity | Basket | HIGH | 05_data_model.md |
| DATA-ENT-006 | Buyer | Entity (Aggregate Root) | Buyer | HIGH | 05_data_model.md |
| DATA-ENT-007 | PaymentMethod | Entity | Buyer | HIGH | 05_data_model.md |
| DATA-ENT-008 | Order | Entity (Aggregate Root) | Order | HIGH | 05_data_model.md |
| DATA-ENT-009 | OrderItem | Entity | Order | HIGH | 05_data_model.md |
| DATA-ENT-010 | Address | Value Object | Order | HIGH | 05_data_model.md |
| DATA-ENT-011 | CatalogItemOrdered | Value Object | Order | HIGH | 05_data_model.md |
| DATA-ENT-012 | ApplicationUser | Entity | Identity | HIGH | 05_data_model.md (truncated) |

---

## 3. Canonical Capability Registry

| Node ID | Name | Domain | Actor | Backing Service | Confidence |
|---------|------|--------|-------|-----------------|------------|
| BIZ-CAP-001 | Basket Item Addition | Basket | Guest/Registered Shopper | BasketService | HIGH |
| BIZ-CAP-002 | Basket Deletion | Basket | System | BasketService | HIGH |
| BIZ-CAP-003 | Anonymous-to-User Basket Transfer | Basket | System (at login) | BasketService | HIGH |
| BIZ-CAP-004 | Basket Item Quantity Update | Basket | Registered Shopper | BasketService | HIGH |
| BIZ-CAP-005 | Basket Item Count Query | Basket | Registered Shopper | BasketQueryService | HIGH |
| BIZ-CAP-006 | Basket View with Product Details | Basket | Registered Shopper | BasketViewModelService | HIGH |
| BIZ-CAP-007 | Get or Create Basket | Basket | Guest/Registered Shopper | BasketViewModelService | HIGH |
| BIZ-CAP-008 | Order Creation from Basket | Order | System | OrderService | HIGH |
| BIZ-CAP-009 | Order Total Calculation | Order | System (domain logic) | Order entity | HIGH |
| BIZ-CAP-010 | Order History Retrieval | Order | Registered Shopper | GetMyOrdersHandler | HIGH |
| BIZ-CAP-011 | Order Detail View | Order | Registered Shopper | GetOrderDetailsHandler | HIGH |
| BIZ-CAP-012 | Paged Catalogue Browse | Catalog | Guest/Registered Shopper | CatalogItemListPagedEndpoint | HIGH |
| BIZ-CAP-013 | Single Product Retrieval | Catalog | Guest/Registered Shopper | CatalogItemGetByIdEndpoint | HIGH |
| BIZ-CAP-014 | Admin Catalogue Product Creation | Catalog | Administrator | CreateCatalogItemEndpoint | HIGH |
| BIZ-CAP-015..039 | *(25 capabilities not visible — BA doc truncated)* | — | — | — | OQ-005 |

---

## 4. Critical Business Rules (Canonical)

| Node ID | Rule | Domain | Severity | Defect? |
|---------|------|--------|----------|---------|
| BIZ-RULE-001 | Product name/picture/id snapshotted at purchase; immutable in order history | Order | High | No |
| BIZ-RULE-002 | Anonymous basket transferred to authenticated account at login | Basket | High | No |
| BIZ-RULE-003 | Order placement requires non-empty basket; basket deleted after order saved | Order | High | No |
| BIZ-RULE-004 | Default quantity 1 when adding item without explicit quantity | Basket | Low | No |
| BIZ-RULE-005 | Administrator role required to create/update/delete catalogue products | Catalog | High | No |
| BIZ-RULE-006 | Checkout requires authenticated session; basket add is open | Basket | High | No |
| BIZ-RULE-007 | Admin API uses JWT with username+role claims | Identity | High | No |
| BIZ-RULE-008 | Email notifications are a no-op stub — all silently discarded | Infrastructure | **Critical** | **YES** |
| BIZ-RULE-009 | Mandatory 1-second delay on public catalogue API (CatalogItemListPagedEndpoint:42) | Catalog | **Critical** | **YES** |
| BIZ-RULE-010 | Admin panel product list cached in browser localStorage for 1 minute | Catalog | Medium | No |
| BIZ-RULE-011 | Order.BuyerId == Buyer.IdentityGuid (same identity value) | Order | High | No |

---

## 5. Canonical Actor Model

| Node ID | Actor | Authentication | Authorized Capabilities |
|---------|-------|---------------|------------------------|
| BIZ-ACT-001 | Guest Shopper | Anonymous (cookie) | Browse, add to basket, view basket |
| BIZ-ACT-002 | Registered Shopper | ASP.NET Core Identity cookie | All guest capabilities + checkout + order history |
| BIZ-ACT-003 | System | N/A (internal) | Basket transfer, order creation, basket deletion |
| BIZ-ACT-004 | Administrator | JWT Bearer (role claim) | Catalogue CRUD (create/update/delete) |

---

## 6. Cross-Domain Data Flow — Purchase Path

```
Guest Shopper
    |
    v
[Catalogue Browse]         CatalogItem (DATA-ENT-001)
    |                          |
    v                          | price locked at add time
[Basket Building]          BasketItem (DATA-ENT-005)
    |                          | CatalogItemId (FK by ID only)
    v
[Login Gate]               Anonymous basket -> Account basket
    |                      (BIZ-RULE-002)
    v
[Checkout]                 Basket (DATA-ENT-004) consumed ->
    |                      Order (DATA-ENT-008) created
    |                      CatalogItemOrdered snapshot (DATA-ENT-011)
    |                      (BIZ-RULE-001: immutable product record)
    v
[Order Confirmation]       Basket permanently deleted (BIZ-RULE-003)
```

---

## 7. Known Defects in Current System (Forward Engineering Must Address)

| ID | Defect | Location | Severity | FE Action Required |
|----|--------|----------|----------|--------------------|
| BIZ-RULE-008 | Email notifications are a no-op stub | EmailSender.cs | Critical | Provision real email provider or confirm stub is intentional |
| BIZ-RULE-009 | Mandatory 1-second artificial delay on catalogue API | CatalogItemListPagedEndpoint.cs:42 | Critical | Remove delay in target application |
| ASMP-005 | Shipping address hardcoded to demo address | Address entity / Checkout flow | Medium | Parameterize default shipping address |

---

## 8. Synthesis Coverage — Confidence Summary

| Layer | Status | Coverage | Gap |
|-------|--------|----------|-----|
| Business (BA) | Partial (3,000 char truncation) | 14/39 capabilities, 11/37 rules, 3/10 processes | See ASMP-004, OQ-005 |
| Data (DA) | Absent | 12 entities from BA evidence | Physical schema, DDL, migrations unverified |
| Application (AA) | Inferred | 13 services, 5 APIs, 4 interfaces | DI wiring, full contracts unconfirmed |
| Technology (TA) | Inferred | 4 stack items, 2 infra, 2 security | Deployment topology, NFRs, full security posture absent |
