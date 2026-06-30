# 14. Non-Functional Requirements Specification — eShopOnWeb

**Forward Engineering Document 14 of 20**
**Generated:** 2026-06-30
**Pipeline Stage:** Forward Engineering (Layer 6)
**Source Foundation:** ENTERPRISE_KNOWLEDGE_GRAPH.json + ARCHITECTURE_INVENTORY.md + CANONICAL_ENTERPRISE_MODEL.md
**Confidence Schema:** MEASURED = directly evidenced from source code or infrastructure. RECOMMENDED BASELINE = no direct evidence; forward-engineering default derived from system type and production readiness.

---

## Document Purpose

This document specifies all non-functional requirements (NFRs) for the forward-engineered eShopOnWeb system. NFRs are organized across 7 categories: Performance, Availability, Reliability, Scalability, Security, Maintainability, and Observability. Every requirement traces to a foundation node. Where a gap exists in the current system, the NFR describes the target state that resolves it.

**NFR Notation:**
- `[MEASURED]` — evidence from source code/infrastructure confirms the current behavior
- `[RECOMMENDED BASELINE]` — no direct evidence; standard for this class of system
- `[MUST FIX]` — current state violates this NFR; remediation is required before production
- `[GATE]` — this NFR is a release-blocking requirement

---

## 14.1 Performance NFRs

### NFR-PERF-001 — Catalog Read Latency

**Category:** Performance
**Status:** [MUST FIX] — current system violates this NFR due to BR-09
**Node Reference:** BR-09, APP-API-004, CatalogItemListPagedEndpoint.cs:42

| Metric | Target | Current State | Evidence |
|---|---|---|---|
| GET /api/catalog-items p95 latency | ≤ 300ms | ≥ 1000ms (artificial delay) | BR-09: `await Task.Delay(1000)` at line 42 |
| GET /api/catalog-items p99 latency | ≤ 800ms | ≥ 1000ms | Same |
| GET /api/catalog-items/{id} p95 latency | ≤ 200ms | Unknown (no monitoring) | No observability (TD-08) |
| GET /api/catalog-brands p95 latency | ≤ 150ms | Unknown | Same |
| GET /api/catalog-types p95 latency | ≤ 150ms | Unknown | Same |

**Remediation:** Delete `await Task.Delay(1000)` from `CatalogItemListPagedEndpoint.cs:42` (FE-14 / AO-04). After removal, expected p95 latency for a properly indexed SQL query should be well within 300ms target.

**Rationale for 300ms p95:** Standard e-commerce catalog browse SLA; accounts for network latency, query execution, and JSON serialization. The Web MVC IMemoryCache (30s TTL, CACHE-001) will further reduce latency for repeat browse requests.

---

### NFR-PERF-002 — Catalog Write Latency

**Category:** Performance
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-API-005, APP-API-006, APP-API-007, DATA-REPO-001

| Metric | Target |
|---|---|
| POST /api/catalog-items p95 | ≤ 700ms |
| PUT /api/catalog-items p95 | ≤ 700ms |
| DELETE /api/catalog-items/{id} p95 | ≤ 500ms |
| POST /api/catalog-items p99 | ≤ 1500ms |

---

### NFR-PERF-003 — Authentication Latency

**Category:** Performance
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-API-001, APP-SVC-007, DATA-REPO-002

| Metric | Target | Notes |
|---|---|---|
| POST /api/authenticate p95 | ≤ 500ms | Includes PBKDF2 password verification (computationally intensive by design) |
| POST /api/authenticate p99 | ≤ 1000ms | PBKDF2 iteration count affects latency |

---

### NFR-PERF-004 — Request Throughput

**Category:** Performance
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-IF-001 (eshopwebmvc), APP-IF-002 (eshoppublicapi)

| Metric | Target |
|---|---|
| Catalog read endpoints sustained throughput | ≥ 200 requests/second per instance |
| Catalog write endpoints sustained throughput | ≥ 50 requests/second per instance |
| Web MVC page renders | ≥ 100 requests/second per instance |

---

### NFR-PERF-005 — Database Query Timeout

**Category:** Performance
**Status:** [RECOMMENDED BASELINE — no timeout configured in current source]
**Node Reference:** DATA-REPO-001, DATA-REPO-002, TECH-CUR-006

| Requirement | Target | Notes |
|---|---|---|
| EF Core command timeout | 30 seconds maximum | No explicit timeout configured in current source (gap) |
| EF Core retry on transient failure | Enable with 3 retries, exponential backoff | TD-09: no retry strategy configured currently |

**Forward-engineering requirement (TD-09 fix, FE-18):**
```csharp
options.UseSqlServer(connectionString, sqlOptions => {
  sqlOptions.CommandTimeout(30);
  sqlOptions.EnableRetryOnFailure(
    maxRetryCount: 3,
    maxRetryDelay: TimeSpan.FromSeconds(10),
    errorNumbersToAdd: null);
});
```

---

### NFR-PERF-006 — Cache Performance

**Category:** Performance
**Status:** [MEASURED — CACHE-001, CACHE-002]
**Node Reference:** CACHE-001 (IMemoryCache), CACHE-002 (Blazored.LocalStorage), APP-SVC-014, APP-SVC-009

| Cache | TTL | Hit Latency Target | Invalidation |
|---|---|---|---|
| CACHE-001 Web MVC IMemoryCache | 30 seconds sliding (MEASURED) | ≤ 5ms (in-process) | TTL only — NOT invalidated on admin writes |
| CACHE-002 BlazorAdmin localStorage | 1 minute (MEASURED) | Browser-local (< 1ms) | Write-through for items; TTL-only for brands/types |

**Important constraint:** CACHE-001 is per-instance in-process memory. With horizontal scaling (≥ 2 instances), different instances may serve different cached versions of the catalog. Redis (IDistributedCache) is required for consistent cache across instances (TD-12, OQ-007). See NFR-SCAL-003.

**Request size limit:**
- Maximum request body size: 4MB (RECOMMENDED BASELINE for catalog admin operations)

---

## 14.2 Availability NFRs

### NFR-AVL-001 — Service Uptime

**Category:** Availability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-IF-001, APP-IF-002

| Service | Monthly Uptime Target |
|---|---|
| eshopwebmvc (APP-IF-001) | ≥ 99.9% (≤ 43.8 minutes downtime per month) |
| eshoppublicapi (APP-IF-002) | ≥ 99.9% |
| SQL Server (DATA-REPO-001, DATA-REPO-002) | ≥ 99.95% |

---

### NFR-AVL-002 — Health Check Endpoints

**Category:** Availability
**Status:** [MUST FIX — no health checks confirmed in source]
**Node Reference:** TD-08, APP-IF-001, APP-IF-002
**Gate:** [GATE] — Docker Compose depends_on with health-gate requires this endpoint

**Required endpoints:**

| Endpoint | Type | Unit | Returns |
|---|---|---|---|
| GET /health | Liveness | APP-IF-001, APP-IF-002 | 200 if process alive |
| GET /health/ready | Readiness | APP-IF-001, APP-IF-002 | 200 only when DB connections verified |

**Docker Compose health check configuration (TD-11 fix, FE-18):**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

The sqlserver container must also have a health check before app containers start:
```yaml
sqlserver:
  healthcheck:
    test: ["CMD", "/opt/mssql-tools/bin/sqlcmd", "-S", "localhost", "-U", "sa", "-P", "${SA_PASSWORD}", "-Q", "SELECT 1"]
    interval: 10s
    timeout: 5s
    retries: 10
    start_period: 40s
```

---

### NFR-AVL-003 — Startup Health Gating

**Category:** Availability
**Status:** [MUST FIX — current Docker Compose has no health gate (TD-11)]
**Node Reference:** TD-11, TECH-INF-003

The app containers must not accept traffic until SQL Server is healthy and both databases are migrated. Current `depends_on` has no `condition: service_healthy` — this is a startup race condition.

**FE-18 fix:** All `depends_on` entries must use `condition: service_healthy`.

---

### NFR-AVL-004 — Database Availability

**Category:** Availability
**Status:** [MUST FIX — Azure SQL Edge EOL]
**Node Reference:** TECH-INF-003, TD-04

Replace EOL Azure SQL Edge with SQL Server 2022 (`mcr.microsoft.com/mssql/server:2022-latest`) to restore vendor support and security patches.

---

### NFR-AVL-005 — Runtime Engine Currency

**Category:** Availability
**Status:** [MUST MONITOR]
**Node Reference:** TECH-CUR-001

.NET 8 LTS support ends November 2026. Migration plan to .NET 9 (or .NET 10 LTS) must begin before November 2026.

---

## 14.3 Reliability NFRs

### NFR-REL-001 — Retry Policy

**Category:** Reliability
**Status:** [MUST FIX — no retry policy in current source]
**Node Reference:** TD-07, TD-09, APP-SVC-013, TECH-CUR-006

| Component | Current State | Required |
|---|---|---|
| BlazorAdmin HTTP calls to PublicApi (APP-SVC-013) | No retry or circuit breaker (TD-07) | Polly retry (3 attempts, exponential backoff) + circuit breaker |
| EF Core SQL Server connections | No retry strategy (TD-09) | EnableRetryOnFailure() (see NFR-PERF-005) |

**Polly policy for BlazorAdmin HTTP client (FE-18):**
```csharp
services.AddHttpClient<ICatalogItemService>()
  .AddPolicyHandler(Policy.Handle<HttpRequestException>()
    .WaitAndRetryAsync(3, retryAttempt =>
      TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))))
  .AddPolicyHandler(Policy.Handle<HttpRequestException>()
    .CircuitBreakerAsync(5, TimeSpan.FromSeconds(30)));
```

---

### NFR-REL-002 — Connection Pool Management

**Category:** Reliability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** DATA-REPO-001, DATA-REPO-002, TECH-CUR-006

| Requirement | Target |
|---|---|
| Connection pool size | Default ADO.NET pool (min: 0, max: 100); document and tune per load |
| Connection timeout | 30 seconds (EF Core default) |
| Pool exhaustion behavior | Throw `SqlException` — not silently queue indefinitely |

---

### NFR-REL-003 — Transactional Order Consistency

**Category:** Reliability
**Status:** [MEASURED — current OrderService uses EF Core transaction]
**Node Reference:** APP-SVC-004, DATA-AGG-002, BIZ-RULE-003

Order creation must be transactional:
1. Create `Order` + all `OrderItems` in a single EF Core `SaveChanges()` call
2. Delete `Basket` after successful order save (BIZ-RULE-003)
3. If order creation fails, basket must NOT be deleted

---

### NFR-REL-004 — Toolchain Version Pinning

**Category:** Reliability
**Status:** [RECOMMENDED BASELINE — MEDIUM confidence on current pinning]
**Node Reference:** TECH-CUR-001, TECH-CUR-016

| Requirement | Implementation |
|---|---|
| .NET SDK version | Pin in `global.json` with `rollForward: "latestPatch"` |
| Docker base images | Pin to specific digest or version tag (not `latest`) |
| NuGet packages | Use `Directory.Packages.props` for centralized version management |

---

### NFR-REL-005 — Disaster Recovery

**Category:** Reliability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** DATA-REPO-001, DATA-REPO-002

| Metric | Target |
|---|---|
| Recovery Point Objective (RPO) | ≤ 15 minutes (maximum acceptable data loss) |
| Recovery Time Objective (RTO) | ≤ 1 hour (maximum acceptable downtime after failure) |
| Database backup frequency | ≥ 1 backup per hour (in production) |

---

## 14.4 Scalability NFRs

### NFR-SCAL-001 — Horizontal Scaling

**Category:** Scalability
**Status:** [RECOMMENDED BASELINE — current system is single-instance]
**Node Reference:** APP-IF-001, APP-IF-002

| Requirement | Target |
|---|---|
| Maximum concurrent instances | ≥ 5 per service (eshopwebmvc, eshoppublicapi) |
| Scaling efficiency | Near-linear throughput increase (≥ 80% linear) |
| Session state requirement | None — stateless instances required (see NFR-SCAL-002) |

---

### NFR-SCAL-002 — Stateless Instances

**Category:** Scalability
**Status:** [PARTIALLY MET — MUST FIX CACHE]
**Node Reference:** APP-IF-001, APP-IF-002, CACHE-001, TD-12

Application instances must be stateless with respect to user session data. Exception: the current IMemoryCache (CACHE-001) is in-process and per-instance — this causes stale-cache divergence under horizontal scaling.

| Requirement | Status | Action |
|---|---|---|
| No in-memory user session state | Met — Identity uses cookie/JWT | — |
| In-process cache consistent across instances | NOT MET — CACHE-001 is per-instance | Migrate to IDistributedCache (Redis) for multi-instance (TD-12, FE-19, OQ-007) |
| No process-affinity requirement | Met | — |

---

### NFR-SCAL-003 — Distributed Cache (Multi-Instance Requirement)

**Category:** Scalability
**Status:** [MUST FIX for multi-instance deployments]
**Node Reference:** TD-12, CACHE-001, OQ-007

When running ≥ 2 instances of eshopwebmvc:
- Current IMemoryCache (CACHE-001) will diverge across instances
- Different users may see different catalog versions depending on which instance they hit
- **Remediation:** Replace `IMemoryCache` with `IDistributedCache` backed by Redis

**FE-19 implementation note:** Generate with `IMemoryCache` for Wave 5 initial delivery. Add a `TODO` comment in `Program.cs` and `CachedCatalogViewModelService` flagging the Redis migration requirement for OQ-007 resolution.

---

### NFR-SCAL-004 — Resource Limits

**Category:** Scalability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** TECH-INF-001, TECH-INF-002

Each container must have explicit resource limits to prevent noisy-neighbor problems:

| Service | CPU Limit | Memory Limit |
|---|---|---|
| eshopwebmvc (APP-IF-001) | 1 CPU | 512MB |
| eshoppublicapi (APP-IF-002) | 1 CPU | 512MB |
| sqlserver (TECH-INF-003) | 2 CPU | 2GB |

---

### NFR-SCAL-005 — Data Scaling

**Category:** Scalability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** DATA-REPO-001, DATA-REPO-002

| Database | Scaling Approach |
|---|---|
| DATA-REPO-001 (CatalogDatabase) | Vertical scaling + read replicas for catalog queries; separate connection string for read replicas if needed |
| DATA-REPO-002 (IdentityDatabase) | Vertical scaling sufficient for identity workload |

Autoscale trigger: CPU utilization ≥ 70% sustained for 5 minutes → add instance.

---

## 14.5 Security NFRs

(Cross-reference with Document 13 — Security Architecture for full security specification)

### NFR-SEC-001 — Zero Committed Secrets

**Category:** Security
**Status:** [MUST FIX — 3 violations exist]
**Node Reference:** BR-32, BR-29, TECH-SEC-007
**Gate:** [GATE] — no deployment allowed with committed secrets

No secret (JWT key, password, SA password, API key, connection string with credentials) may appear in any committed source file, including `docker-compose.yml`, `appsettings.*.json`, or `AuthorizationConstants.cs`.

---

### NFR-SEC-002 — Authentication Enforcement

**Category:** Security
**Status:** [MUST FIX — CORS and JWT enforcement not confirmed in source]
**Node Reference:** APP-API-005..007, TECH-SEC-002, BIZ-RULE-005
**Gate:** [GATE]

All write endpoints must reject unauthenticated and unauthorized requests at the framework middleware level, not only in business logic.

---

### NFR-SEC-003 — Role-Based Authorization

**Category:** Security
**Status:** [MEASURED]
**Node Reference:** TECH-SEC-003, BIZ-RULE-005, APP-API-005..007

ADMINISTRATORS role required for all catalog write operations. Deny-by-default posture: endpoints with `[Authorize(Roles="ADMINISTRATORS")]` return 403 for any JWT without the ADMINISTRATORS claim.

---

### NFR-SEC-004 — CORS Allow-List

**Category:** Security
**Status:** [MUST FIX — AllowAnyOrigin or missing (TD-06)]
**Node Reference:** TD-06, ASMP-004
**Gate:** [GATE]

CORS policy must specify an explicit origin allow-list. `AllowAnyOrigin()` is NOT permitted in any environment.

---

### NFR-SEC-005 — TLS Everywhere

**Category:** Security
**Status:** [MUST FIX for Docker environment]
**Node Reference:** TECH-INF-001, TECH-INF-002

All inter-service communication and client-server communication must use TLS in production. Plain HTTP is acceptable only for local development with explicit documentation.

---

### NFR-SEC-006 — Database Not Host-Exposed

**Category:** Security
**Status:** [MUST FIX for production]
**Node Reference:** TECH-INF-003

SQL Server port 1433 must not be bound to the host in production deployments. In Docker Compose, use internal network only for the sqlserver container.

---

### NFR-SEC-007 — PII Data Protection

**Category:** Security
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** PII-01..PII-08, DATA-REPO-002

PII fields (email, address, password hash, tokens) must not appear in structured logs. Application code must never log: `Email`, `PasswordHash`, `ShipToAddress_*`, `BuyerId` (if = email), `AspNetUserTokens.Value`.

---

### NFR-SEC-008 — CI/CD Security Scanning

**Category:** Security
**Status:** [MUST FIX — no secret scanning in CI]
**Node Reference:** TD-02, TECH-CUR-017

GitHub Actions pipeline must include:
1. Secret scanning step (Gitleaks or TruffleHog)
2. Dependency vulnerability scanning (OWASP Dependency Check or `dotnet audit`)
3. Static analysis (optional but recommended)

Pipeline must FAIL if secrets are detected.

---

### NFR-SEC-009 — Audit Logging

**Category:** Security
**Status:** [MUST FIX — no audit logging found in source]
**Node Reference:** CANONICAL_ENTERPRISE_MODEL.md §6.7

Security-relevant events must produce structured audit log entries:
- Authentication success/failure (user, IP, timestamp)
- Authorization failure (user, resource, action, timestamp)
- Admin catalog operations (create/update/delete — user, item ID, timestamp)
- Account lockout events

---

### NFR-SEC-010 — Password Policy (NIST 800-63B)

**Category:** Security
**Status:** [MUST FIX — current minimum is 6 chars]
**Node Reference:** TD-21, TECH-CUR-007

| Requirement | Current | Target |
|---|---|---|
| Minimum password length | 6 characters | 8 characters (NIST SP 800-63B minimum) |
| Maximum password length | 100 characters | 100 characters (current — acceptable) |
| Complexity requirements | Mixed (uppercase, digit, special) | Retain current complexity rules |

---

## 14.6 Maintainability NFRs

### NFR-MNT-001 — Zero Module Dependency Cycles

**Category:** Maintainability
**Status:** [MUST FIX — ARCH-VIOL-008 exists]
**Node Reference:** ARCH-VIOL-008, MOD-001..013
**Gate:** [GATE]

The module dependency cycle (Admin → ApplicationCore → Basket → Catalog → DataAccess → Identity → Order → Web → Admin) must be eliminated. Forward-engineered code must have a directed acyclic dependency graph across all modules.

---

### NFR-MNT-002 — Per-Component Coupling Thresholds

**Category:** Maintainability
**Status:** [MUST FIX — ARCH-VIOL-009, ARCH-VIOL-010]
**Node Reference:** ARCH-VIOL-009 (EfRepository coupling=16), ARCH-VIOL-010 (UriComposer coupling=8)

| Component | Current Coupling | Target Coupling |
|---|---|---|
| EfRepository (APP-SVC-008) | 16 (highest in codebase) | ≤ 4 (consumed only via IRepository<T> interface) |
| UriComposer | 8 | ≤ 3 (Infrastructure concern, not domain) |
| All other components | Varied | ≤ 10 per component |

---

### NFR-MNT-003 — No Endpoint-to-Repository Shortcuts

**Category:** Maintainability
**Status:** [MUST FIX — 6 violations in current source]
**Node Reference:** ARCH-VIOL-001..007
**Gate:** [GATE]

API endpoint handlers must not directly inject `EfRepository<T>` or any concrete repository type. All data access must flow through domain service interfaces (`IBasketService`, `ICatalogItemService`, etc.) or read repository abstractions (`IReadRepository<T>`).

---

### NFR-MNT-004 — 100% Versioned Dependencies

**Category:** Maintainability
**Status:** [MEDIUM confidence — `UNKNOWN` versions in several TECH-CUR nodes]
**Node Reference:** TECH-CUR-006..014, TECH-CUR-018..022

All NuGet package versions must be explicitly declared. `Directory.Packages.props` must pin every dependency to a specific version. No implicit `latest` or version ranges in production.

---

### NFR-MNT-005 — Test Coverage

**Category:** Maintainability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** TECH-CUR-018, MOD-012

| Layer | Coverage Target |
|---|---|
| Domain logic (ApplicationCore) | ≥ 80% line coverage |
| Application services | ≥ 70% line coverage |
| API endpoints (integration tests) | 100% of 8 endpoints |
| Overall system | ≥ 70% line coverage |

---

### NFR-MNT-006 — API Contract Stability

**Category:** Maintainability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-API-001..008

The 8 PublicApi REST endpoint paths, methods, and required request/response fields must not change without a version increment (see FE-11 versioning strategy, ASMP-FE-101). Additive changes (new optional fields) are allowed in the current version.

---

### NFR-MNT-007 — Engine Currency

**Category:** Maintainability
**Status:** [MUST MONITOR]
**Node Reference:** TECH-CUR-001, TECH-INF-003

| Component | EOL | Action Required By |
|---|---|---|
| Azure SQL Edge (TECH-INF-003) | March 2025 (PAST DUE) | Immediate — replace before any deployment |
| .NET 8 (TECH-CUR-001) | November 2026 | Plan migration to .NET 9+ before this date |
| BlazorInputFile (TECH-CUR-021) | Superseded (since .NET 5) | Replace in FE-20 |
| BuildBundlerMinifier (TECH-CUR-022) | Deprecated | Replace in FE-20 |

---

## 14.7 Observability NFRs

### NFR-OBS-001 — Structured Centralized Logging

**Category:** Observability
**Status:** [MUST FIX — no structured logging confirmed]
**Node Reference:** CANONICAL_ENTERPRISE_MODEL.md §6.7, TD-08

All application logs must be structured (JSON format) and include:
- `timestamp` (ISO-8601)
- `level` (INFO/WARN/ERROR/CRITICAL)
- `service` (eshopwebmvc or eshoppublicapi)
- `correlationId` (request trace ID)
- `message`
- `exception` (for errors — full stack trace)

**PII exclusion rule:** Email addresses, passwords, shipping addresses must NOT appear in any log entry (see NFR-SEC-007, PII-01..08).

**Logging adapter requirement:** The current system uses no confirmed logging framework beyond `Console.WriteLine` or basic ILogger. The forward-engineered system must use a structured logging library:
- .NET: Serilog or Microsoft.Extensions.Logging with structured sinks
- Java: SLF4J + Logback with JSON encoder
- Node.js: Pino or Winston with JSON format

---

### NFR-OBS-002 — Application Metrics (RED Method)

**Category:** Observability
**Status:** [MUST FIX — no metrics confirmed in source]
**Node Reference:** APP-IF-001, APP-IF-002

Each service must emit the following RED metrics:
- **Rate:** Requests per second per endpoint
- **Errors:** Error rate (4xx/5xx) per endpoint
- **Duration:** p50/p95/p99 latency per endpoint

Metrics endpoint: `/metrics` (Prometheus-compatible format recommended for Kubernetes compatibility).

---

### NFR-OBS-003 — Distributed Tracing

**Category:** Observability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-IF-001, APP-IF-002

Each request must carry a correlation ID from entry point through all downstream calls. For the multi-service architecture (eshopwebmvc → eshoppublicapi → sqlserver), trace context must propagate via W3C Trace Context headers (`traceparent`/`tracestate`).

---

### NFR-OBS-004 — Health Signal Freshness

**Category:** Observability
**Status:** [MUST FIX — no health endpoints confirmed]
**Node Reference:** TD-08, NFR-AVL-002

Health state changes (healthy → unhealthy, or unhealthy → healthy) must be detectable within ≤ 30 seconds. This requires:
- Health check poll interval ≤ 10 seconds (Docker: `interval: 10s`)
- Readiness probe failing immediately on DB connection loss (not waiting for TTL)

---

### NFR-OBS-005 — SLO Alerting

**Category:** Observability
**Status:** [RECOMMENDED BASELINE]
**Node Reference:** APP-IF-001, APP-IF-002, NFR-PERF-001, NFR-AVL-001

Alerting thresholds:
- Error rate > 5% sustained for 1 minute → alert
- p95 latency > 500ms sustained for 5 minutes → alert
- Service health check failing > 30 seconds → alert (page)

---

## 14.8 NFR-to-Foundation Traceability Summary

| NFR ID | Category | Key Node References | FE Documents |
|---|---|---|---|
| NFR-PERF-001 | Performance | BR-09, APP-API-004 | FE-14 (remove Task.Delay) |
| NFR-PERF-005 | Performance | TD-09, TECH-CUR-006 | FE-18 (EF Core retry) |
| NFR-PERF-006 | Performance | CACHE-001, CACHE-002, TD-12 | FE-11, FE-12, FE-19 |
| NFR-AVL-002 | Availability | TD-08 | FE-18 (health checks) |
| NFR-AVL-003 | Availability | TD-11 | FE-20 (Docker health gate) |
| NFR-AVL-004 | Availability | TECH-INF-003, TD-04 | FE-20 (SQL Server image) |
| NFR-REL-001 | Reliability | TD-07, TD-09 | FE-18 (Polly + EF retry) |
| NFR-SCAL-002 | Scalability | CACHE-001, TD-12 | FE-19 (cache strategy) |
| NFR-SEC-001 | Security | BR-32, BR-29, TECH-SEC-007 | FE-15, FE-17 |
| NFR-SEC-002 | Security | APP-API-005..007 | FE-14, FE-16 |
| NFR-SEC-004 | Security | TD-06, ASMP-004 | FE-16 (CORS) |
| NFR-SEC-008 | Security | TD-02, TECH-CUR-017 | FE-20 (CI scanning) |
| NFR-MNT-001 | Maintainability | ARCH-VIOL-008 | FE-01 (clean modules) |
| NFR-MNT-003 | Maintainability | ARCH-VIOL-001..007 | FE-13, FE-14 |
| NFR-OBS-001 | Observability | TD-08 | FE-18 (logging) |
| NFR-OBS-002 | Observability | APP-IF-001, APP-IF-002 | FE-18 (metrics) |

---

## 14.9 Assumptions

| ID | Statement | Basis | Impact |
|---|---|---|---|
| ASMP-FE-001 | Latency targets (NFR-PERF-001) assume standard SQL Server query performance with appropriate indexes | EF Core + SQL Server current stack | Without BR-09 fix, all catalog latency NFRs are violated |
| ASMP-FE-002 | IMemoryCache (CACHE-001) is sufficient for single-instance deployments | CACHE-001 measured evidence | Redis required when scaling to ≥ 2 instances (NFR-SCAL-003) |
| ASMP-FE-003 | Test coverage targets (NFR-MNT-005) are achievable given the 3 existing test projects | TECH-CUR-018 + MOD-012 (45 components) | MSTest projects (TECH-CUR-019) must be consolidated to xUnit |
| ASMP-FE-004 | Performance targets are per-instance; horizontal scaling is the mechanism for higher aggregate throughput | Clean Architecture + stateless design | Stateless instances (NFR-SCAL-002) is prerequisite |

---

*Document 14 of 20 — Non-Functional Requirements Specification*
*All NFRs trace to foundation node IDs. [MUST FIX] items are production-blocking gaps evidenced in the current system.*
*[GATE] NFRs are release-blocking — system must not be deployed until these are satisfied.*
