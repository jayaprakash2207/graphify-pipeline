# 13. Security Architecture — eShopOnWeb

**Forward Engineering Document 13 of 20**
**Generated:** 2026-06-30
**Pipeline Stage:** Forward Engineering (Layer 6)
**Source Foundation:** ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md + CANONICAL_ENTERPRISE_MODEL.md
**Confidence Schema:** HIGH = direct code evidence; MEDIUM = structural inference; LOW = convention assumption.

---

## Document Purpose

This document specifies the complete security architecture for eShopOnWeb's forward-engineered system. It covers all 7 security components (TECH-SEC-001..007), both authentication mechanisms (JWT Bearer and ASP.NET Core Identity cookie), the full RBAC authorization model, and a complete remediation plan for the **6 critical production blockers** (BR-08, BR-09, BR-15, BR-27, BR-29, BR-32) identified in the foundation. Every security control and finding traces to a node ID.

**The 6 critical production blockers that MUST be resolved before any production deployment:**

| # | Rule ID | Description | Location |
|---|---|---|---|
| 1 | BR-32 | JWT signing key hardcoded as plaintext in source | AuthorizationConstants.cs:12 |
| 2 | BR-29 | Seeded account passwords hardcoded as plaintext | AuthorizationConstants.cs:8 |
| 3 | BR-15 | All orders record hardcoded shipping address | Checkout.cshtml.cs:57 |
| 4 | BR-08 | Email system entirely non-functional (stub returns immediately) | EmailSender.cs |
| 5 | BR-27 | New user registration does not require email confirmation | Register.cshtml.cs:77-88 |
| 6 | BR-09 | Every catalogue browse request has 1-second artificial delay | CatalogItemListPagedEndpoint.cs:42 |

---

## 13.1 Security Architecture Overview

### 13.1.1 Trust Surfaces

The system exposes three trust surfaces, each with a distinct security posture:

| Surface | Deployable Unit | Node | Actor | Auth Mechanism | Trust Level |
|---|---|---|---|---|---|
| Public REST API | eshoppublicapi | APP-IF-002 | BIZ-ACT-001 (Customer), BIZ-ACT-004 (Service Account) | JWT Bearer (TECH-SEC-002) — token issued by APP-API-001 | Internet-facing, token-gated write operations |
| Web Storefront | eshopwebmvc | APP-IF-001 | BIZ-ACT-001 (Customer), BIZ-ACT-002 (Anonymous Shopper) | ASP.NET Core Identity Cookie (TECH-SEC-001) | Internet-facing, session-gated checkout |
| Admin SPA | BlazorAdmin | APP-IF-003 (served from APP-IF-001) | BIZ-ACT-003 (Product Administrator) | JWT Bearer via CustomAuthStateProvider (APP-SVC-013) | Admin-only; JWT stored in browser localStorage (XSS risk — TD-03) |

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet / Public                        │
│  [Anonymous Shopper]  [Registered User]  [Admin]           │
└──────────────────┬──────────────────┬──────────────────────┘
                   │                  │
    ┌──────────────▼──────────────┐   │  ┌──────────────────────┐
    │  eshopwebmvc (APP-IF-001)   │   │  │  eshoppublicapi       │
    │  Cookie Auth (TECH-SEC-001) │   └─►│  (APP-IF-002)         │
    │  CSRF (TECH-SEC-006)        │      │  JWT Bearer            │
    │  Hosts BlazorAdmin WASM     │      │  (TECH-SEC-002)        │
    └──────────────┬──────────────┘      └──────────┬───────────┘
                   │                               │
                   └────────────────────────────────┘
                                  │
                   ┌──────────────▼──────────────┐
                   │  SQL Server (TECH-INF-003)  │
                   │  DATA-REPO-001 CatalogDB    │
                   │  DATA-REPO-002 IdentityDB   │
                   └─────────────────────────────┘
```

---

## 13.2 Authentication

### 13.2.1 Web Storefront — Cookie Authentication (TECH-SEC-001)

**Component:** ASP.NET Core Identity cookie authentication
**Node:** TECH-SEC-001
**Confidence:** HIGH
**Surface:** eshopwebmvc (APP-IF-001)

**Current implementation:**
- ASP.NET Core Identity backed by EF Core + AppIdentityDbContext (DATA-REPO-002)
- Cookie issued on successful login (POST /account/login)
- Cookie triggers anonymous basket transfer to user basket on login — Web path only (BIZ-RULE-002)
- CSRF anti-forgery tokens on all forms (TECH-SEC-006)

**Known gaps:**
- Password minimum length is 6 characters — below NIST SP 800-63B minimum of 8 (TD-21)
- No email confirmation required after registration (BR-27 — production blocker)

**Forward-engineered requirements:**
- Minimum password length: 8 characters (NIST 800-63B compliance, TD-21 fix)
- `RequireConfirmedEmail = true` after AO-02 (email service) is implemented
- Cookie `SecurePolicy = SameAsRequest` (dev) / `Always` (production)
- Cookie `SameSite = Strict` or `Lax` depending on redirect flows
- `RequireUniqueEmail = true`

### 13.2.2 Public API — JWT Bearer Authentication (TECH-SEC-002)

**Component:** JWT Bearer Authentication
**Node:** TECH-SEC-002
**Confidence:** HIGH (package reference confirmed; configuration evidence MEDIUM)
**Surface:** eshoppublicapi (APP-IF-002), BlazorAdmin (APP-IF-003)

**Current implementation:**
- POST /api/authenticate (APP-API-001) issues JWT via IdentityTokenClaimService (APP-SVC-007)
- JWT claims: username + all assigned roles (BIZ-RULE-007)
- JWT expiry: 7 days (BIZ-RULE-024)
- JWT stored in browser localStorage by BlazorAdmin (TD-03 — XSS risk)
- **CRITICAL VULNERABILITY (BR-32):** JWT signing key is `SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes` hardcoded in `AuthorizationConstants.cs:12`

**Forward-engineered requirements — BR-32 remediation:**

```csharp
// CORRECT pattern (AO-03 fix):
var jwtKey = configuration["Auth:JwtKey"]
             ?? throw new InvalidOperationException("Auth:JwtKey not configured");

// WRONG pattern (must NOT appear in generated code):
// var jwtKey = AuthorizationConstants.JwtSecretKey;  // BR-32 — NEVER DO THIS
```

**JWT configuration requirements:**
- Key source: `IConfiguration["Auth:JwtKey"]` — populated from:
  - Development: User Secrets (`dotnet user-secrets set "Auth:JwtKey" "..."`)
  - Docker/CI: environment variable `Auth__JwtKey`
  - Azure: Azure Key Vault (TECH-INF-004) via DefaultAzureCredential (TECH-SEC-004)
- Minimum key length: 32 bytes (256-bit minimum for HMAC-SHA-256)
- Algorithm: HS256 (current) or RS256 (recommended for multi-service environments)
- Issuer: configured value (not hardcoded)
- Audience: configured value (not hardcoded)

**BlazorAdmin JWT storage — TD-03 note:**
Current: `Blazored.LocalStorage` (browser localStorage) — XSS-accessible (HIGH risk, TD-03).
Forward engineering recommendation: Migrate to httpOnly cookie (BFF pattern). This is HIGH effort and is flagged as a follow-on task (not blocking Wave 4 generation).

### 13.2.3 Authentication Flow Diagram

```
Web Login (Cookie Auth):
  POST /account/login
    ├─► SignInManager.PasswordSignInAsync()
    │     ├─ Success: Issue cookie, trigger basket transfer (BIZ-RULE-002)
    │     └─ Failed: Account lockout after N attempts (BIZ-RULE-025)
    └─► Redirect to return URL

API Login (JWT Auth):
  POST /api/authenticate (APP-API-001)
    ├─► SignInManager.CheckPasswordSignInAsync()
    │     ├─ Success: IdentityTokenClaimService.GetTokenAsync()
    │     │     ├─ Load user + all roles from IdentityDatabase (DATA-REPO-002)
    │     │     └─ Build JWT (sub=username, roles=[...], exp=now+7days)
    │     └─ Failed: 401 Unauthorized
    └─► Return { "token": "..." }

NOTE: API login does NOT trigger anonymous basket transfer (BIZ-RULE-002 scope = Web only)
```

---

## 13.3 Authorization and RBAC

### 13.3.1 Role Model

**Confirmed roles from source evidence:**

| Role | Evidence | Confidence | Scope |
|---|---|---|---|
| `ADMINISTRATORS` | `[Authorize(Roles="ADMINISTRATORS")]` on APP-API-005, 006, 007; AppIdentityDbContextSeed | HIGH | Catalog write operations via PublicApi |
| `(Default authenticated user)` | Any authenticated user via cookie or JWT | HIGH | Checkout, order history, account management |
| `(Anonymous)` | GUID cookie (BIZ-RULE-016) | HIGH | Browse catalog, add to basket |

**No other roles are evidenced in the foundation.** Do not invent additional roles in generated code.

### 13.3.2 Authorization Matrix — All 8 REST Endpoints

| Endpoint | Auth Required | Role Required | Rule Reference |
|---|---|---|---|
| POST /api/authenticate | No | None | Issues JWT |
| GET /api/catalog-brands | No | None | Public read |
| GET /api/catalog-items | No | None | Public read |
| GET /api/catalog-items/{id} | No | None | Public read |
| GET /api/catalog-types | No | None | Public read |
| POST /api/catalog-items | **Yes** | ADMINISTRATORS | BIZ-RULE-005 |
| PUT /api/catalog-items | **Yes** | ADMINISTRATORS | BIZ-RULE-005 |
| DELETE /api/catalog-items/{id} | **Yes** | ADMINISTRATORS | BIZ-RULE-005 |

**Business rule BIZ-RULE-005:** Only the ADMINISTRATORS role may create, update, or delete catalog products. This rule must be enforced by the framework (`[Authorize(Roles="ADMINISTRATORS")]` attribute or equivalent policy), not only by business logic.

### 13.3.3 Authorization Matrix — Web MVC Routes

| Route | Auth Required | Notes |
|---|---|---|
| GET /catalog | No | Public storefront browse |
| POST /basket/add | No | Anonymous basket allowed (BIZ-RULE-016) |
| GET /basket | No | Anonymous basket view |
| POST /basket/checkout (step 1) | No | Pre-checkout quantity update |
| GET /checkout | **Yes** | [Authorize] — BIZ-RULE-006, BIZ-RULE-018 |
| POST /basket/checkout | **Yes** | [Authorize] — order creation |
| GET /order/my-orders | **Yes** | [Authorize] — own orders only (BIZ-RULE-030) |
| GET /order/detail/{orderId} | **Yes** | [Authorize] — own order only; 404 for others (BIZ-RULE-030) |
| POST /account/login | No | Identity page |
| GET /account/register | No | Identity page |
| POST /account/register | No | New user registration |
| GET /manage/* | **Yes** | Account management — requires authenticated user |

### 13.3.4 Row-Level Authorization

**BIZ-RULE-030 — Order ownership:**
- `GetMyOrdersHandler` (APP-SVC-005): Returns only orders where `Order.BuyerId == currentUser.UserName`
- `GetOrderDetailsHandler` (APP-SVC-006): Returns 404 if requested order's BuyerId does not match current user
- Must be enforced in the query specification, not only in the controller action

**Cross-domain identity reference (BIZ-RULE-011):**
- `Order.BuyerId` and `Basket.BuyerId` link to `AspNetUsers.Id` by string value convention
- No database foreign key constraint (cross-database soft reference — DATA-REPO-001 vs DATA-REPO-002)
- Identity consistency is application-code responsibility

---

## 13.4 Secrets Management

### 13.4.1 Current State — 3 Critical Vulnerabilities

| Vulnerability | Node | Severity | Location | Plaintext Value |
|---|---|---|---|---|
| JWT signing key hardcoded | TECH-SEC-002, BR-32 | CRITICAL | AuthorizationConstants.cs:12 | `SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes` |
| Seeded passwords hardcoded | BR-29 | CRITICAL | AuthorizationConstants.cs:8 | `Pass@word1` |
| SA database password hardcoded | TECH-SEC-007, TD-01 | CRITICAL | docker-compose.yml | `@someThingComplicated1234` |

**Both BR-29 and BR-32 carry explicit TODO comments in the source code warning against production use.** These are acknowledged teaching-codebase gaps.

### 13.4.2 Forward-Engineered Secrets Configuration (AO-03 remediation)

**Architecture (multi-environment secret sourcing):**

```
Development environment:
  dotnet user-secrets set "Auth:JwtKey" "<random-256-bit-key>"
  dotnet user-secrets set "Seeding:AdminPassword" "<secure-password>"
  dotnet user-secrets set "ConnectionStrings:CatalogConnection" "<connection-string>"

Docker / CI environment:
  Environment variables: Auth__JwtKey, Seeding__AdminPassword
  SA_PASSWORD via Docker secret or environment variable (never in compose file)

Azure production:
  Azure Key Vault (TECH-INF-004):
    - Auth:JwtKey → Key Vault secret "jwtSigningKey"
    - Seeding:AdminPassword → Key Vault secret "appAdminPassword"
    - SA password → Key Vault secret "sqlAdminPassword"
  Access: DefaultAzureCredential (TECH-SEC-004) via Azure Managed Identity
```

**Required configuration keys (generated code must read these — never hardcode):**

| Config Key | Purpose | FE Document |
|---|---|---|
| `Auth:JwtKey` | JWT HMAC signing key | FE-15, FE-17 |
| `Seeding:AdminPassword` | Seeded admin account password | FE-15, FE-17 |
| `Seeding:DemoPassword` | Seeded demo account password | FE-15, FE-17 |
| `ConnectionStrings:CatalogConnection` | CatalogDatabase connection | FE-03, FE-17 |
| `ConnectionStrings:IdentityConnection` | IdentityDatabase connection | FE-03, FE-17 |

### 13.4.3 Docker Compose Secret Remediation (TECH-SEC-007)

```yaml
# CORRECT (generated pattern):
services:
  sqlserver:
    environment:
      - SA_PASSWORD=${SA_PASSWORD:?SA_PASSWORD environment variable is required}
    # Or using Docker secrets:
    secrets:
      - sa_password

# WRONG (must not appear in generated docker-compose.yml):
# environment:
#   - SA_PASSWORD=@someThingComplicated1234   # TECH-SEC-007 — NEVER DO THIS
```

---

## 13.5 Encryption

### 13.5.1 Data in Transit

**Current state:**
- Development: HTTPS on 44315 (Web) and 5099 (PublicApi) via dev certificate
- Docker Compose: HTTP only on ports 5106 and 5200 (plain HTTP — gap)

**Forward-engineered requirements:**
- Production: TLS 1.2 minimum; TLS 1.3 preferred
- Docker Compose: Use HTTPS even for local Docker; or document that plain HTTP is development-only
- HSTS header on all production responses
- Redirect HTTP to HTTPS

### 13.5.2 Data at Rest — Password Hashing

**Current:** ASP.NET Core Identity uses PBKDF2/SHA-256 (DATA-ENT-010.PasswordHash — HIGH PII, PII-03)

**Forward-engineered requirements:**
- Retain PBKDF2/SHA-256 (current) as minimum
- Do not store raw passwords anywhere — database, logs, or telemetry
- `PasswordHash` column must not appear in structured logs

### 13.5.3 PII Protection

All 8 PII fields identified in the foundation must be handled according to sensitivity:

| PII-ID | Table | Column | Sensitivity | Protection Rule |
|---|---|---|---|---|
| PII-01 | AspNetUsers | Email | HIGH | Right to erasure; GDPR Article 17 |
| PII-02 | AspNetUsers | UserName | MEDIUM | Likely = email; right to erasure applies |
| PII-03 | AspNetUsers | PasswordHash | HIGH | Never log; PBKDF2/SHA-256; not reversible |
| PII-04 | AspNetUsers | PhoneNumber | MEDIUM | Optional; right to erasure if populated |
| PII-05 | Orders | BuyerId | MEDIUM/HIGH | If BuyerId = email: HIGH PII; erasure complexity (OQ-001) |
| PII-06 | Orders | ShipToAddress_* | HIGH | Full physical address; right to erasure |
| PII-07 | Baskets | BuyerId | LOW/MEDIUM | Orphan baskets on user deletion |
| PII-08 | AspNetUserTokens | Value | HIGH | Auth token; right to erasure |

---

## 13.6 Critical Production Blockers — Full Remediation Plan

### BR-32 — Hardcoded JWT Signing Key

**Current:** `SecretKeyOfDoomThatMustBeAMinimumNumberOfBytes` in `AuthorizationConstants.cs:12`
**Risk:** Anyone with repository access can forge admin JWT tokens.
**Remediation (FE-15, FE-17):**
1. Delete `AuthorizationConstants.JwtSecretKey` constant
2. Generate minimum 32-byte random key
3. Store in User Secrets (dev) / environment variable (Docker/CI) / Azure Key Vault (prod)
4. Read via `IConfiguration["Auth:JwtKey"]` in `IdentityTokenClaimService`
5. Throw `InvalidOperationException` on startup if key is not configured
**Wave:** Wave 4 (FE-15) + Wave 5 (FE-17)

### BR-29 — Hardcoded Seeded Passwords

**Current:** `Pass@word1` for both admin and demo accounts in `AuthorizationConstants.cs:8`
**Risk:** Any deployed instance with default passwords is immediately compromised.
**Remediation (FE-15, FE-17):**
1. Delete `AuthorizationConstants.DefaultPassword` constant
2. Store default passwords in User Secrets / environment variable / Azure Key Vault
3. Read via `IConfiguration["Seeding:AdminPassword"]` and `IConfiguration["Seeding:DemoPassword"]`
4. `AppIdentityDbContextSeed` must read from configuration, never from constants
5. Fix seeding idempotency bug (AO-09): wrap role creation in `if (!await roleManager.RoleExistsAsync(role))`
**Wave:** Wave 4 (FE-15) + Wave 5 (FE-17)

### BR-15 — Hardcoded Shipping Address

**Current:** `"123 Main St., Kent, OH, United States, 44240"` hardcoded at `Checkout.cshtml.cs:57`
**Risk:** Every order in the system records the same fake address. Zero real-world utility.
**Remediation (FE-10):**
1. `OrderService.CreateOrderAsync(buyerId, shipToAddress, basketItems)` must accept `shipToAddress` as a parameter
2. Checkout page must collect real shipping address from user before calling `CreateOrderAsync`
3. Address fields: Street (nvarchar 180), City (100), State (60, nullable), Country (90), ZipCode (18) — from DATA-ENT-011 / BIZ-RULE-033
4. Address form validation in Checkout.cshtml.cs
**Wave:** Wave 3 (FE-10)

### BR-08 — Non-Functional Email System

**Current:** `EmailSender.cs` returns `Task.CompletedTask` without any email delivery.
**Risk:** Password reset, email confirmation, and order confirmation emails are silently discarded.
**Remediation (FE-15, AO-02):**
1. Implement `IEmailSender` with a real SMTP client or transactional email provider (SendGrid / SMTP)
2. Read SMTP credentials from configuration (never hardcoded)
3. Email service must be wired in DI startup (Program.cs)
4. Stub behavior must NOT be the default in any environment except local unit tests
**Wave:** Wave 4 (FE-15) — requires AO-02 decision on email provider

### BR-27 — No Email Confirmation on Registration

**Current:** `Register.cshtml.cs:77-88` activates accounts immediately without email confirmation.
**Risk:** Fake account creation; no email ownership verification.
**Remediation (FE-15, AO-08):**
1. `RequireConfirmedEmail = true` in Identity options
2. Send confirmation email via `IEmailSender` on registration
3. Block login until email confirmed
**Note:** This requires BR-08 (email service) to be resolved first. Implement after AO-02.
**Wave:** Post-Wave 5 (AO-08 — depends on AO-02)

### BR-09 — Artificial 1-Second Delay

**Current:** `await Task.Delay(1000)` at `CatalogItemListPagedEndpoint.cs:42`
**Risk:** Every catalog browse request takes at least 1 second regardless of DB performance.
**Remediation (FE-14):**
1. Delete the line `await Task.Delay(1000);` from `CatalogItemListPagedEndpoint`
2. The generated endpoint must not contain any `Task.Delay` call
3. Verify p95 latency target (≤ 300ms per NFR-PERF-001) is achievable without artificial delay
**Wave:** Wave 4 (FE-14)

---

## 13.7 Security Findings Register

All security findings from the ARCHITECTURE_INVENTORY.md Technical Debt Register that relate to security:

| Finding | Severity | Node | Status | Remediation |
|---|---|---|---|---|
| SA password hardcoded in docker-compose.yml | Critical | TECH-SEC-007, TD-01 | OPEN | Move to Docker secret/env var (FE-17, FE-20) |
| JWT token stored in browser localStorage (XSS accessible) | Critical | TD-03 | OPEN | Migrate to httpOnly cookie (follow-on, high effort) |
| No secret scanning in CI pipeline | Critical | TD-02 | OPEN | Add Gitleaks/TruffleHog step to GitHub Actions (FE-20) |
| JWT signing key hardcoded | Critical | TECH-SEC-002, BR-32 | OPEN | Externalize to config/Key Vault (FE-15, FE-17) |
| Seeded passwords hardcoded | Critical | BR-29 | OPEN | Externalize to config/Key Vault (FE-15, FE-17) |
| CORS policy absent or AllowAnyOrigin | High | TD-06 | OPEN | Configure allow-list in Program.cs (FE-16) |
| Swagger UI not gated behind IsDevelopment() | Medium | TD-22 | OPEN | Add environment gate (FE-16) |
| Identity password minimum 6 chars (below NIST 800-63B) | Medium | TD-21 | OPEN | Set minimum to 8 in Identity options (FE-16) |

---

## 13.8 Security Boundaries and Trust Levels

### 13.8.1 Per-Unit Trust Model

| Deployable Unit | Exposed to Internet | Authentication Required | Contains Admin Functions |
|---|---|---|---|
| APP-IF-001 (eshopwebmvc) | YES | Partial (checkout/orders require auth; browse is anonymous) | NO (admin SPA is embedded but JWT-gated) |
| APP-IF-002 (eshoppublicapi) | YES | Partial (reads are public; writes require ADMINISTRATORS JWT) | YES — catalog write operations |
| APP-IF-003 (BlazorAdmin, served from APP-IF-001) | Via APP-IF-001 | YES — JWT Bearer ADMINISTRATORS role required | YES — all admin operations |

### 13.8.2 Network Exposure Policy

**Principle of least exposure (TECH-INF-003):**
- SQL Server container port 1433 MUST NOT be publicly exposed in any environment
- Only app containers (APP-IF-001, APP-IF-002) require internet-reachable ports
- In Docker Compose: sql container should use internal network only; remove host port binding for 1433 in production

---

## 13.9 Auth Startup Wiring Requirements (FE-16)

The following security components must be wired in Program.cs / startup:

```csharp
// 1. Cookie authentication (TECH-SEC-001)
services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
  .AddCookie(options => {
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always; // production
    options.Cookie.SameSite = SameSiteMode.Lax;
    options.LoginPath = "/account/login";
  })
  // 2. JWT Bearer (TECH-SEC-002) — key from config ONLY (BR-32 fix)
  .AddJwtBearer(options => {
    var jwtKey = configuration["Auth:JwtKey"]
      ?? throw new InvalidOperationException("Auth:JwtKey not configured");
    options.TokenValidationParameters = new TokenValidationParameters {
      ValidateIssuerSigningKey = true,
      IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
      ValidateIssuer = true,
      ValidIssuer = configuration["Auth:Issuer"],
      ValidateAudience = true,
      ValidAudience = configuration["Auth:Audience"]
    };
  });

// 3. Authorization (TECH-SEC-003)
services.AddAuthorization(options => {
  options.AddPolicy("AdminOnly", policy =>
    policy.RequireRole("ADMINISTRATORS"));
});

// 4. CORS — allow-list for BlazorAdmin origin (ASMP-004 — TD-06 fix)
services.AddCors(options => {
  options.AddPolicy("BlazorAdminPolicy", builder =>
    builder.WithOrigins(
      configuration["Cors:AllowedOrigins:BlazorAdmin"] // from config, NOT hardcoded
    )
    .AllowAnyMethod()
    .AllowAnyHeader()
    .AllowCredentials());
});

// 5. CSRF anti-forgery (TECH-SEC-006)
services.AddAntiforgery();

// 6. Identity options (TD-21 fix — password min length 8)
services.Configure<IdentityOptions>(options => {
  options.Password.RequiredLength = 8; // NIST 800-63B minimum
  options.Lockout.AllowedForNewUsers = true; // BIZ-RULE-025
  options.Lockout.MaxFailedAccessAttempts = 5;
});

// 7. Swagger — gated behind IsDevelopment() (ASMP-005 / TD-22 fix)
if (app.Environment.IsDevelopment()) {
  app.UseSwagger();
  app.UseSwaggerUI();
}
```

---

## 13.10 OWASP Top 10 Mapping

| OWASP 2021 | Risk | Applicable Finding | Remediation |
|---|---|---|---|
| A01 Broken Access Control | High | Catalog write endpoints require ADMINISTRATORS — must be enforced at framework level | `[Authorize(Roles="ADMINISTRATORS")]` + policy (FE-14, FE-16) |
| A02 Cryptographic Failures | Critical | JWT key hardcoded (BR-32); SA password hardcoded (TECH-SEC-007); HTTP in Docker | Externalize secrets (FE-15, FE-17); TLS everywhere |
| A03 Injection | Low | EF Core parameterized queries prevent SQL injection by default | Retain EF Core parameterized queries (FE-13) |
| A04 Insecure Design | High | Hardcoded shipping address (BR-15); email stub (BR-08) | AO-01 (FE-10); AO-02 (FE-15) |
| A05 Security Misconfiguration | Critical | AllowAnyOrigin CORS (TD-06); Swagger not gated (TD-22) | CORS allow-list; IsDevelopment() gate (FE-16) |
| A06 Vulnerable Components | High | Azure SQL Edge EOL (TECH-INF-003); BlazorInputFile superseded | Replace EOL image (FE-20) |
| A07 Identification and Auth Failures | Critical | JWT in localStorage (TD-03); no email confirmation (BR-27); password min 6 chars (TD-21) | httpOnly cookie (follow-on); require confirmation (AO-08); min 8 chars (FE-16) |
| A08 Software and Data Integrity Failures | Medium | No secret scanning in CI (TD-02) | Add Gitleaks to GitHub Actions (FE-20) |
| A09 Security Logging and Monitoring Failures | High | No audit logging evidenced | Implement structured logging + audit events (FE-18) |
| A10 SSRF | Low | No outbound HTTP calls from server except email (stub) | No action required currently |

---

## 13.11 Security Traceability Summary

| Security Requirement | Resolves | FE Document | Foundation Node(s) |
|---|---|---|---|
| Externalize JWT key to configuration | BR-32, TECH-SEC-002 | FE-15, FE-17 | AuthorizationConstants.cs:12 |
| Externalize seeded passwords to configuration | BR-29 | FE-15, FE-17 | AuthorizationConstants.cs:8 |
| Remove SA_PASSWORD from docker-compose.yml | TECH-SEC-007, TD-01 | FE-17, FE-20 | docker-compose.yml |
| Enforce ADMINISTRATORS role on catalog writes | BIZ-RULE-005, APP-API-005..007 | FE-14 | ARCH-VIOL-003..005 |
| Collect real shipping address at checkout | BR-15 | FE-10 | Checkout.cshtml.cs:57 |
| Wire real email sender | BR-08 | FE-15 (AO-02) | EmailSender.cs |
| Require email confirmation | BR-27 | FE-15 (AO-08) | Register.cshtml.cs:77-88 |
| Remove Task.Delay from catalog endpoint | BR-09 | FE-14 | CatalogItemListPagedEndpoint.cs:42 |
| CORS allow-list for BlazorAdmin | TD-06, ASMP-004 | FE-16 | PublicApi Program.cs |
| Swagger gated behind IsDevelopment() | TD-22, TECH-CUR-014 | FE-16 | Program.cs |
| Password minimum 8 characters | TD-21 | FE-16 | Identity options |
| Add secret scanning to CI | TD-02 | FE-20 | .github/workflows/dotnetcore.yml |
| Fix seeding idempotency | AO-09, BIZ-RULE-037 | FE-15 | AppIdentityDbContextSeed |
| EF Core retry on transient SQL errors | TD-09 | FE-18 | Infrastructure startup |
| Health check endpoints | TD-08 | FE-18 | Program.cs |

---

*Document 13 of 20 — Security Architecture*
*All security controls, findings, and production blockers trace to node IDs in ENTERPRISE_KNOWLEDGE_GRAPH.json.*
*The 6 critical production blockers (BR-08, BR-09, BR-15, BR-27, BR-29, BR-32) are fully documented with remediation plans and FE document assignments.*
