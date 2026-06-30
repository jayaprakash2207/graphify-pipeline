# 11. API Contract Specification — eShopOnWeb

**Forward Engineering Document 11 of 20**
**Generated:** 2026-06-30
**Pipeline Stage:** Forward Engineering (Layer 6)
**Source Foundation:** ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md
**Confidence Schema:** Every claim traces to a node ID. HIGH = direct code evidence. MEDIUM = structural inference. LOW = convention assumption.

---

## Document Purpose

This document specifies the complete externally-observable REST API contract for eShopOnWeb's forward-engineered system. It covers all 8 confirmed REST endpoints (APP-API-001 through APP-API-008) surfaced by the PublicApi deployable unit (APP-IF-002), with full OpenAPI-style schemas, authentication requirements, validation rules, and error contracts. All endpoints are technology-neutral — the contract is realizable on any target backend stack.

**Architecture violations corrected in this specification:**
- ARCH-VIOL-001 through ARCH-VIOL-007: Endpoints no longer inject EfRepository directly; they depend on domain service interfaces or IReadRepository/IRepository abstractions.
- Production blocker BR-09 removed: GET /api/catalog-items does NOT contain `await Task.Delay(1000)`.
- Production blocker BR-32: JWT signing key is read from configuration, never hardcoded.

---

## 11.1 Scope and Conventions

### 11.1.1 Interface Surface Covered

The PublicApi deployable unit (APP-IF-002, `eshoppublicapi`, port 5200:8080) exposes exactly **8 REST/JSON endpoints**:

| Range | Module | Count |
|---|---|---|
| APP-API-001 | Identity | 1 |
| APP-API-002, APP-API-008 | Catalog — Read (Brands, Types) | 2 |
| APP-API-003, APP-API-004 | Catalog — Read (Items) | 2 |
| APP-API-005, APP-API-006, APP-API-007 | Catalog — Write (Create, Delete, Update) | 3 |

The Web MVC (APP-IF-001) and BlazorAdmin (APP-IF-003) surfaces are HTML/browser surfaces not JSON APIs and are out of scope for this REST contract document.

### 11.1.2 Technology-Neutral Type Vocabulary

| Neutral Type | Description | .NET Example | Java Example | Node.js Example |
|---|---|---|---|---|
| `Identifier` | Integer surrogate key (HiLo or IDENTITY) | `int` | `Long` | `number` |
| `String(N)` | UTF-8 text, max N chars | `string` | `String` | `string` |
| `Text` | Unbounded UTF-8 text | `string` | `String` | `string` |
| `Decimal(p,s)` | Fixed-precision monetary amount | `decimal` | `BigDecimal` | `number` |
| `Integer` | Whole number | `int` | `int` | `number` |
| `Boolean` | true/false | `bool` | `boolean` | `boolean` |
| `DateTime` | ISO-8601 timestamp | `DateTimeOffset` | `OffsetDateTime` | `Date` |
| `Uri` | Resource locator string | `string` | `String` | `string` |
| `Token` | Opaque signed JWT | `string` | `String` | `string` |

### 11.1.3 Authentication Baseline

| Endpoint Group | Auth Required | Mechanism |
|---|---|---|
| POST /api/authenticate | None (issues JWT) | Issues Token via TECH-SEC-002 |
| GET /api/catalog-brands | None (public read) | — |
| GET /api/catalog-items | None (public read) | — |
| GET /api/catalog-items/{id} | None (public read) | — |
| GET /api/catalog-types | None (public read) | — |
| POST /api/catalog-items | **Required — ADMINISTRATORS role** | JWT Bearer, TECH-SEC-002 |
| PUT /api/catalog-items | **Required — ADMINISTRATORS role** | JWT Bearer, TECH-SEC-002 |
| DELETE /api/catalog-items/{id} | **Required — ADMINISTRATORS role** | JWT Bearer, TECH-SEC-002 |

**Security note (BR-32 — production blocker):** The JWT signing key MUST be sourced from `IConfiguration["Auth:JwtKey"]` (environment variable, User Secrets, or Azure Key Vault via TECH-INF-004). It must NEVER be hardcoded (as it currently is in `AuthorizationConstants.cs:12`). FE-15 and FE-17 address this remediation.

### 11.1.4 Common Request Headers

| Header | Required | Value |
|---|---|---|
| `Content-Type` | For POST/PUT with body | `application/json` |
| `Authorization` | For protected endpoints | `Bearer <jwt-token>` |
| `Accept` | Optional | `application/json` |

---

## 11.2 Endpoint Catalog — All 8 REST Endpoints

| ID | Method | Path | Auth | Capability | Preserve in FE | Source Handler |
|---|---|---|---|---|---|---|
| APP-API-001 | POST | `/api/authenticate` | None — issues JWT | BIZ-CAP-022, BIZ-CAP-023 | YES | AuthenticateEndpoint.cs:36 |
| APP-API-002 | GET | `/api/catalog-brands` | None — public | BIZ-CAP-006 | YES | CatalogBrandListEndpoint.cs:27 |
| APP-API-003 | GET | `/api/catalog-items/{catalogItemId}` | None — public | BIZ-CAP-002 | YES | CatalogItemGetByIdEndpoint.cs:25 |
| APP-API-004 | GET | `/api/catalog-items` | None — public | BIZ-CAP-001 | YES — remove Task.Delay (BR-09) | CatalogItemListPagedEndpoint.cs:31 |
| APP-API-005 | POST | `/api/catalog-items` | ADMINISTRATORS | BIZ-CAP-003 | YES | CreateCatalogItemEndpoint.cs:29 |
| APP-API-006 | DELETE | `/api/catalog-items/{catalogItemId}` | ADMINISTRATORS | BIZ-CAP-005 | YES | DeleteCatalogItemEndpoint.cs:20 |
| APP-API-007 | PUT | `/api/catalog-items` | ADMINISTRATORS | BIZ-CAP-004 | YES | UpdateCatalogItemEndpoint.cs:27 |
| APP-API-008 | GET | `/api/catalog-types` | None — public | BIZ-CAP-007 | YES | CatalogTypeListEndpoint.cs:27 |

---

## 11.3 Identity Endpoints

### APP-API-001 — POST /api/authenticate

**Capability:** BIZ-CAP-022 (User Authentication — API — JWT), BIZ-CAP-023 (JWT Token Generation)
**Handler (current):** `AuthenticateEndpoint` → `APP-SVC-007` (IdentityTokenClaimService)
**Auth:** None (this endpoint IS the authentication entry point)
**Module:** MOD-007 (Identity)
**Source:** `src/PublicApi/AuthEndpoints/AuthenticateEndpoint.cs:36`

#### Request

```
POST /api/authenticate
Content-Type: application/json
```

**Request Body:**

```json
{
  "username": "String(256) — required — user email/username",
  "password": "String(100) — required"
}
```

| Field | Type | Constraints | Validation Rule |
|---|---|---|---|
| `username` | String(256) | Required, non-empty | Guard.Against.NullOrEmpty |
| `password` | String(100) | Required, non-empty | Guard.Against.NullOrEmpty |

#### Response — 200 OK

```json
{
  "token": "Token — signed JWT; 7-day expiry (BIZ-RULE-024)"
}
```

| Field | Type | Notes |
|---|---|---|
| `token` | Token | JWT signed with key from config (AO-03 / BR-32). Claims: username, all assigned roles (BIZ-RULE-007). Expiry: DateTime.UtcNow.AddDays(7). |

**JWT Claims (BIZ-RULE-007, BIZ-CAP-023):**
- `sub` — username
- `roles` — all roles assigned to the user (e.g., "ADMINISTRATORS")
- `exp` — Unix timestamp 7 days from issue (BIZ-RULE-024)

#### Response — 401 Unauthorized

```json
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.5.2",
  "title": "Authentication failed",
  "status": 401,
  "detail": "Invalid username or password."
}
```

**Account lockout (BIZ-RULE-025):** After repeated failed attempts, the account is locked. Locked accounts return 401 with `"detail": "Account locked out."`.

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Credentials valid — token issued |
| 400 | Missing or empty username/password |
| 401 | Invalid credentials or account locked (BIZ-RULE-025) |
| 500 | Unexpected server error |

---

## 11.4 Catalog Read Endpoints

### APP-API-002 — GET /api/catalog-brands

**Capability:** BIZ-CAP-006 (Brand List Retrieval)
**Handler (current):** `CatalogBrandListEndpoint`
**Auth:** None (public)
**Fix applied:** ARCH-VIOL-001 resolved — no direct EfRepository injection; uses IReadRepository or ICatalogBrandService.
**Source:** `src/PublicApi/CatalogBrandEndpoints/CatalogBrandListEndpoint.cs:27`

#### Request

```
GET /api/catalog-brands
```

No query parameters. No request body.

#### Response — 200 OK

```json
{
  "catalogBrands": [
    {
      "id": "Identifier — HiLo (catalog_brand_hilo)",
      "brand": "String(100) — brand name"
    }
  ]
}
```

| Field | Type | Source Entity | Notes |
|---|---|---|---|
| `catalogBrands` | Array | DATA-ENT-002 (CatalogBrand) | All brands; no pagination (small, bounded list) |
| `id` | Identifier | DATA-ENT-002.Id | HiLo-generated integer |
| `brand` | String(100) | DATA-ENT-002.Brand | nvarchar(100) per DA evidence |

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Success (may be empty array if no brands seeded) |
| 500 | Database unreachable or unexpected error |

---

### APP-API-003 — GET /api/catalog-items/{catalogItemId}

**Capability:** BIZ-CAP-002 (Single Product Retrieval)
**Handler (current):** `CatalogItemGetByIdEndpoint`
**Auth:** None (public)
**Fix applied:** ARCH-VIOL-002 resolved — no direct EfRepository injection.
**Source:** `src/PublicApi/CatalogItemEndpoints/CatalogItemGetByIdEndpoint.cs:25`

#### Request

```
GET /api/catalog-items/{catalogItemId}
```

| Parameter | Location | Type | Required | Notes |
|---|---|---|---|---|
| `catalogItemId` | Path | Identifier | Yes | HiLo integer; must be > 0 |

#### Response — 200 OK

```json
{
  "id": "Identifier",
  "name": "String(50) — product name",
  "description": "Text — product description",
  "price": "Decimal(18,2) — unit price in base currency",
  "pictureUri": "Uri — product image URI (Text / nvarchar(max))",
  "catalogTypeId": "Identifier — foreign key to CatalogType",
  "catalogBrandId": "Identifier — foreign key to CatalogBrand",
  "catalogType": {
    "id": "Identifier",
    "type": "String(100)"
  },
  "catalogBrand": {
    "id": "Identifier",
    "brand": "String(100)"
  }
}
```

**Field constraints (from DATA-ENT-001):**

| Field | Type | Column | Constraint |
|---|---|---|---|
| `id` | Identifier | Catalog.Id | HiLo integer |
| `name` | String(50) | Name | nvarchar(50) NOT NULL |
| `description` | Text | Description | nvarchar(max) |
| `price` | Decimal(18,2) | Price | decimal(18,2); must be > 0 (BIZ-RULE-021) |
| `pictureUri` | Uri | PictureUri | nvarchar(max) |
| `catalogTypeId` | Identifier | CatalogTypeId | FK to CatalogTypes (RESTRICT) |
| `catalogBrandId` | Identifier | CatalogBrandId | FK to CatalogBrands (RESTRICT) |

**Fields explicitly EXCLUDED (DISC-001 — verified discrepancy):**
`AvailableStock`, `RestockThreshold`, `MaxStockThreshold`, `OnReorder` — not present in eShopOnWeb source. Do not add to generated contracts.

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Item found |
| 404 | No item with the given catalogItemId |
| 400 | catalogItemId is not a valid integer or is <= 0 |
| 500 | Unexpected server error |

---

### APP-API-004 — GET /api/catalog-items

**Capability:** BIZ-CAP-001 (Catalogue Discovery — Paged Browse)
**Handler (current):** `CatalogItemListPagedEndpoint`
**Auth:** None (public)
**Critical fix (AO-04 / BR-09 — production blocker):** The generated endpoint MUST NOT contain `await Task.Delay(1000)`. This artificial 1-second delay exists at `CatalogItemListPagedEndpoint.cs:42` in the source and must be removed.
**Fix applied:** ARCH-VIOL-004 resolved — no direct EfRepository injection.
**Source:** `src/PublicApi/CatalogItemEndpoints/CatalogItemListPagedEndpoint.cs:31`

#### Request

```
GET /api/catalog-items?pageSize=10&pageIndex=0&catalogBrandId=1&catalogTypeId=2
```

| Parameter | Location | Type | Required | Default | Notes |
|---|---|---|---|---|---|
| `pageSize` | Query | Integer | No | 10 | Max recommended: 100 |
| `pageIndex` | Query | Integer | No | 0 | Zero-based page index |
| `catalogBrandId` | Query | Identifier | No | null | Filter by brand; omit for all brands |
| `catalogTypeId` | Query | Identifier | No | null | Filter by type; omit for all types |

#### Response — 200 OK

```json
{
  "pageIndex": "Integer — current zero-based page",
  "pageSize": "Integer — items per page",
  "count": "Integer — total matching items (for pagination UI)",
  "data": [
    {
      "id": "Identifier",
      "name": "String(50)",
      "description": "Text",
      "price": "Decimal(18,2)",
      "pictureUri": "Uri",
      "catalogTypeId": "Identifier",
      "catalogBrandId": "Identifier",
      "catalogType": { "id": "Identifier", "type": "String(100)" },
      "catalogBrand": { "id": "Identifier", "brand": "String(100)" }
    }
  ]
}
```

**Caching note (CACHE-001):** The Web MVC catalog browse is cached server-side with 30-second IMemoryCache sliding TTL (APP-SVC-014, CachedCatalogViewModelService). Admin writes to this endpoint's underlying data do NOT invalidate the Web MVC cache — staleness of up to 30s is by design. See FE-11, FE-19.

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Success (may be empty `data` array) |
| 400 | Invalid pageIndex or pageSize (negative values) |
| 500 | Unexpected server error |

---

### APP-API-008 — GET /api/catalog-types

**Capability:** BIZ-CAP-007 (Type List Retrieval)
**Handler (current):** `CatalogTypeListEndpoint`
**Auth:** None (public)
**Fix applied:** ARCH-VIOL-006 resolved — no direct EfRepository injection.
**Source:** `src/PublicApi/CatalogTypeEndpoints/CatalogTypeListEndpoint.cs:27`

#### Request

```
GET /api/catalog-types
```

No query parameters. No request body.

#### Response — 200 OK

```json
{
  "catalogTypes": [
    {
      "id": "Identifier — HiLo (catalog_type_hilo)",
      "type": "String(100) — category/type name"
    }
  ]
}
```

| Field | Type | Source Entity | Notes |
|---|---|---|---|
| `catalogTypes` | Array | DATA-ENT-003 (CatalogType) | All types; no pagination |
| `id` | Identifier | DATA-ENT-003.Id | HiLo integer |
| `type` | String(100) | DATA-ENT-003.Type | nvarchar(100) per DA evidence |

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Success |
| 500 | Unexpected server error |

---

## 11.5 Catalog Write Endpoints (ADMINISTRATORS Role Required)

### APP-API-005 — POST /api/catalog-items

**Capability:** BIZ-CAP-003 (Admin Product Creation)
**Handler (current):** `CreateCatalogItemEndpoint`
**Auth:** JWT Bearer — `[Authorize(Roles="ADMINISTRATORS")]`
**Fix applied:** ARCH-VIOL-003 resolved — no direct EfRepository injection.
**Source:** `src/PublicApi/CatalogItemEndpoints/CreateCatalogItemEndpoint.cs:29`

#### Request

```
POST /api/catalog-items
Authorization: Bearer <admin-jwt>
Content-Type: application/json
```

**Request Body:**

```json
{
  "name": "String(50) — required — product name",
  "description": "Text — required",
  "price": "Decimal(18,2) — required — must be > 0",
  "pictureUri": "Uri — optional — defaults to placeholder image if omitted",
  "catalogTypeId": "Identifier — required — must reference existing CatalogType",
  "catalogBrandId": "Identifier — required — must reference existing CatalogBrand"
}
```

| Field | Type | Required | Validation Rule |
|---|---|---|---|
| `name` | String(50) | Yes | Non-empty (BIZ-RULE-022); unique across catalog (BIZ-RULE-020); max 50 chars |
| `description` | Text | Yes | Non-empty (BIZ-RULE-022) |
| `price` | Decimal(18,2) | Yes | > 0 (BIZ-RULE-021) — Guard.Against.NegativeOrZero |
| `pictureUri` | Uri | No | Defaults to default placeholder image (BIZ-RULE-023) |
| `catalogTypeId` | Identifier | Yes | Must reference existing CatalogType (RESTRICT FK) |
| `catalogBrandId` | Identifier | Yes | Must reference existing CatalogBrand (RESTRICT FK) |

**Business rules enforced:**
- BIZ-RULE-020: Product name must be unique. Check before insert; return 400/409 on duplicate.
- BIZ-RULE-021: Price must be > 0.
- BIZ-RULE-022: Name and description must not be empty.
- BIZ-RULE-023: New items always receive a default placeholder image — admin image upload is permanently disabled.

#### Response — 201 Created

```json
{
  "id": "Identifier — newly assigned HiLo ID",
  "name": "String(50)",
  "description": "Text",
  "price": "Decimal(18,2)",
  "pictureUri": "Uri — default placeholder",
  "catalogTypeId": "Identifier",
  "catalogBrandId": "Identifier"
}
```

`Location` header: `/api/catalog-items/{id}`

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 201 | Created successfully |
| 400 | Validation failure (empty name, price <= 0, missing required field) |
| 401 | Missing or invalid JWT |
| 403 | Valid JWT but not ADMINISTRATORS role |
| 409 | Name already exists in catalog (BIZ-RULE-020) |
| 500 | Unexpected server error |

---

### APP-API-006 — DELETE /api/catalog-items/{catalogItemId}

**Capability:** BIZ-CAP-005 (Admin Product Deletion)
**Handler (current):** `DeleteCatalogItemEndpoint`
**Auth:** JWT Bearer — `[Authorize(Roles="ADMINISTRATORS")]`
**Fix applied:** ARCH-VIOL-004 resolved.
**Source:** `src/PublicApi/CatalogItemEndpoints/DeleteCatalogItemEndpoint.cs:20`

#### Request

```
DELETE /api/catalog-items/{catalogItemId}
Authorization: Bearer <admin-jwt>
```

| Parameter | Location | Type | Required | Notes |
|---|---|---|---|---|
| `catalogItemId` | Path | Identifier | Yes | HiLo integer; must be > 0 |

#### Response — 204 No Content

Empty body on successful deletion.

**Referential integrity note:** CatalogItem FK references from BasketItems use a soft reference (no DB FK constraint — DATA-ENT-005: "soft ref to CatalogItem (no FK)"). Deletion does not cascade to BasketItems at the DB level. Application-level handling may be required.

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 204 | Deleted successfully |
| 401 | Missing or invalid JWT |
| 403 | Valid JWT but not ADMINISTRATORS role |
| 404 | No item with the given catalogItemId |
| 400 | Invalid catalogItemId |
| 500 | Unexpected server error |

---

### APP-API-007 — PUT /api/catalog-items

**Capability:** BIZ-CAP-004 (Admin Product Update)
**Handler (current):** `UpdateCatalogItemEndpoint`
**Auth:** JWT Bearer — `[Authorize(Roles="ADMINISTRATORS")]`
**Fix applied:** ARCH-VIOL-005 resolved.
**Source:** `src/PublicApi/CatalogItemEndpoints/UpdateCatalogItemEndpoint.cs:27`

#### Request

```
PUT /api/catalog-items
Authorization: Bearer <admin-jwt>
Content-Type: application/json
```

**Request Body (full replacement):**

```json
{
  "id": "Identifier — required — item to update",
  "name": "String(50) — required",
  "description": "Text — required",
  "price": "Decimal(18,2) — required — must be > 0",
  "pictureUri": "Uri — optional",
  "catalogTypeId": "Identifier — required",
  "catalogBrandId": "Identifier — required"
}
```

| Field | Type | Required | Validation Rule |
|---|---|---|---|
| `id` | Identifier | Yes | Must reference existing item |
| `name` | String(50) | Yes | Non-empty (BIZ-RULE-022); max 50 chars |
| `description` | Text | Yes | Non-empty (BIZ-RULE-022) |
| `price` | Decimal(18,2) | Yes | > 0 (BIZ-RULE-021) |
| `pictureUri` | Uri | No | Optional update |
| `catalogTypeId` | Identifier | Yes | Must reference existing CatalogType |
| `catalogBrandId` | Identifier | Yes | Must reference existing CatalogBrand |

**Important snapshot semantics (BIZ-RULE-001):** Updating a CatalogItem's price does NOT retroactively change the price stored in existing OrderItems. `OrderItem.ItemOrdered_*` fields are immutable snapshots captured at checkout time. This is by design.

#### Response — 200 OK

```json
{
  "id": "Identifier",
  "name": "String(50)",
  "description": "Text",
  "price": "Decimal(18,2)",
  "pictureUri": "Uri",
  "catalogTypeId": "Identifier",
  "catalogBrandId": "Identifier"
}
```

#### Error Codes

| HTTP Status | Condition |
|---|---|
| 200 | Updated successfully |
| 400 | Validation failure (empty name, price <= 0) |
| 401 | Missing or invalid JWT |
| 403 | Valid JWT but not ADMINISTRATORS role |
| 404 | No item with the given id |
| 500 | Unexpected server error |

---

## 11.6 Common Error Contract (RFC 9457 Problem Detail)

All error responses follow the RFC 9457 / RFC 7807 problem-detail envelope:

```json
{
  "type": "String — URI identifying problem type (e.g. https://tools.ietf.org/html/rfc9110#section-15.5.4)",
  "title": "String — short human-readable summary",
  "status": "Integer — HTTP status code",
  "detail": "String — human-readable explanation specific to this occurrence",
  "instance": "Uri — optional — specific resource URI that triggered this error",
  "errors": {
    "fieldName": ["Array of validation messages"]
  }
}
```

**Standard problem type URIs:**

| Status | Type URI |
|---|---|
| 400 | `https://tools.ietf.org/html/rfc9110#section-15.5.1` |
| 401 | `https://tools.ietf.org/html/rfc9110#section-15.5.2` |
| 403 | `https://tools.ietf.org/html/rfc9110#section-15.5.4` |
| 404 | `https://tools.ietf.org/html/rfc9110#section-15.5.5` |
| 409 | `https://tools.ietf.org/html/rfc9110#section-15.5.10` |
| 500 | `https://tools.ietf.org/html/rfc9110#section-15.6.1` |

---

## 11.7 API Versioning Strategy

**Current state (foundation evidence):** No versioning is present in the source codebase. All 8 endpoints use unversioned paths (`/api/...`).

**Forward engineering recommendation (ASMP-FE-101):** Introduce URI versioning for the target system to enable non-breaking evolution:

```
/api/v1/authenticate
/api/v1/catalog-items
/api/v1/catalog-brands
/api/v1/catalog-types
```

**Versioning rules:**
- Add `v1` as the initial version for all 8 endpoints.
- Maintain backward compatibility — do not remove or rename fields in v1 without introducing v2.
- Deprecate versions with `Sunset` and `Deprecation` HTTP response headers.
- Version prefix must appear in path, not in Accept header or query parameter (URI versioning is the simplest and most widely supported pattern).

---

## 11.8 Capability-to-Endpoint Traceability

```
BIZ-CAP-001 (Catalogue Discovery)     --> APP-API-004  GET /api/catalog-items
BIZ-CAP-002 (Single Product)          --> APP-API-003  GET /api/catalog-items/{id}
BIZ-CAP-003 (Admin Create)            --> APP-API-005  POST /api/catalog-items
BIZ-CAP-004 (Admin Update)            --> APP-API-007  PUT /api/catalog-items
BIZ-CAP-005 (Admin Delete)            --> APP-API-006  DELETE /api/catalog-items/{id}
BIZ-CAP-006 (Brand List)              --> APP-API-002  GET /api/catalog-brands
BIZ-CAP-007 (Type List)               --> APP-API-008  GET /api/catalog-types
BIZ-CAP-022 (API Authentication)      --> APP-API-001  POST /api/authenticate
BIZ-CAP-023 (JWT Generation)          --> APP-API-001  (internal: APP-SVC-007)

Data entities serving these endpoints:
  DATA-ENT-001 (CatalogItem)   -- all catalog-items endpoints
  DATA-ENT-002 (CatalogBrand)  -- catalog-brands + as nested in items
  DATA-ENT-003 (CatalogType)   -- catalog-types + as nested in items
  DATA-ENT-010 (ApplicationUser) -- authenticate endpoint (via TECH-CUR-007 Identity)

Repositories:
  DATA-REPO-001 (CatalogDatabase / CatalogContext) -- all catalog + auth data
  DATA-REPO-002 (IdentityDatabase / AppIdentityDbContext) -- user + role data
```

---

## 11.9 Production Readiness Checklist for API Layer

| Item | Status | FE Document | Node Reference |
|---|---|---|---|
| Remove Task.Delay(1000) from GET /api/catalog-items | MUST DO | FE-14 | BR-09, APP-API-004 |
| JWT key from config, not hardcoded | MUST DO | FE-15, FE-17 | BR-32, TECH-SEC-002 |
| Enforce [Authorize(Roles=ADMINISTRATORS)] on write endpoints | CONFIRMED | FE-14 | APP-API-005,006,007 |
| Remove direct EfRepository injection from all endpoints | MUST DO | FE-13, FE-14 | ARCH-VIOL-001..007 |
| Swagger gated behind IsDevelopment() | MUST DO | FE-16 | TECH-CUR-014, ASMP-005 |
| CORS allow-list configured for BlazorAdmin origin | MUST DO | FE-16 | TD-06, ASMP-004 |
| Account lockout enabled | CONFIRMED | FE-15 | BIZ-RULE-025 |
| Problem-detail error envelope on all error responses | MUST DO | FE-14 | §11.6 |

---

## 11.10 Assumptions and Open Questions

| ID | Statement | Impact |
|---|---|---|
| ASMP-FE-101 | URI versioning (`/api/v1/...`) is the selected versioning strategy | All 8 routes will be prefixed `/api/v1/` in generated code |
| ASMP-FE-102 | Authenticated endpoints enforce JWT at the framework level (`[Authorize]`), not only at business logic level | Authorization must be wired in startup (FE-16) |
| OQ-001 | BuyerId = email address or GUID? | Affects PII sensitivity classification for Orders/Baskets. Generate with `string BuyerId`; document ambiguity in code comments. |
| OQ-005 | Default demo credentials rotated before deployment? | AO-03 mandatory: read passwords from config, never constants (BR-29) |

---

*Document 11 of 20 — API Contract Specification*
*Every endpoint, field, and constraint in this document traces to a node ID in ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md.*
*No endpoints have been invented. All 8 REST endpoints are from the foundation graph.*
