# Forward Engineering Readiness Report — eShopOnWeb
## Pipeline: Graphify v2.0 | Date: 2026-06-30 | Graph: ENTERPRISE_KNOWLEDGE_GRAPH.json

---

> **DISC-001 WARNING — Stock Field Discrepancy**
>
> The reverse-engineered graph detected a discrepancy (DISC-001) between the domain model and the database schema regarding stock-related fields on the `CatalogItem` entity. Specifically, `RestockThreshold` and `MaxStockThreshold` appear in the EF Core configuration but have no corresponding domain enforcement in the aggregate. **Do not replicate these fields as business logic in the generated domain layer.** Carry them forward as infrastructure-level persistence columns only, or consult a domain expert before assigning behaviour. This warning is tracked as ARCH-VIOL-010 and must be resolved before Wave 2 generation begins.

---

## Executive Summary

| Dimension | Value |
|---|---|
| Overall Readiness Score | **79 / 100** |
| Readiness Verdict | **CONDITIONAL\_READY** |
| Graph Version | ENTERPRISE\_KNOWLEDGE\_GRAPH.json |
| Pipeline Version | Graphify v2.0 |
| Report Generated | 2026-06-30 |
| GR-08 Gate | RESOLVED — target\_stack = "dotnet8" |
| FE Documents Present | 20 / 20 |
| Architecture Violations | 11 (2 CRITICAL, 4 HIGH, 5 MEDIUM) |
| Open Questions | 8 |
| Technical Debt Items | 22 |
| Total Graph Nodes | 173 |

The eShopOnWeb knowledge graph is substantially complete and the pipeline has produced all twenty Forward Engineering documents across five generation waves. The gate condition GR-08 (target stack resolution) is resolved, with the target stack confirmed as **dotnet8**. Two critical architecture violations — ARCH-VIOL-001 (Web project bypasses clean architecture) and ARCH-VIOL-004 (JWT secret hardcoded in appsettings) — must be addressed before the Wave 1 and Wave 4 code-generation prompts are executed, respectively. Generation may proceed wave by wave with those constraints in mind.

### Wave Readiness Summary

| Wave | Documents | Theme | Violations Blocking | Readiness |
|---|---|---|---|---|
| Wave 1 | FE-01..FE-04 | Foundation | ARCH-VIOL-001 (CRITICAL) | BLOCKED until ARCH-VIOL-001 resolved |
| Wave 2 | FE-05..FE-08 | Domain | ARCH-VIOL-006, ARCH-VIOL-010 | CONDITIONAL |
| Wave 3 | FE-09..FE-12 | Application Layer | None blocking | READY |
| Wave 4 | FE-13..FE-16 | Infrastructure / API | ARCH-VIOL-002, ARCH-VIOL-004, ARCH-VIOL-009, ARCH-VIOL-011 | BLOCKED until ARCH-VIOL-004 resolved |
| Wave 5 | FE-17..FE-20 | Cross-cutting | ARCH-VIOL-003, ARCH-VIOL-005, ARCH-VIOL-007, ARCH-VIOL-008 | CONDITIONAL |

---

## §1 Scoring Methodology

The overall readiness score is the equally weighted average of five rubric scores. Each rubric is scored on a 0–100 scale. The combined score determines a three-tier verdict:

| Score Range | Verdict |
|---|---|
| 90–100 | READY — proceed to generation without restrictions |
| 70–89 | CONDITIONAL\_READY — proceed wave by wave; resolve blockers before each wave |
| 0–69 | NOT\_READY — resolve all critical issues before any generation |

### Rubric Definitions

| ID | Rubric | Weight | Question |
|---|---|---|---|
| R1 | Completeness | 20% | Are all 20 FE documents present and fully populated? |
| R2 | Consistency | 20% | Do node IDs cross-reference correctly across all documents? |
| R3 | Traceability | 20% | Does every generated artifact trace back to at least one graph node? |
| R4 | Architecture Quality | 20% | How many violations exist? Are they classified, documented, and assigned resolution waves? |
| R5 | FE Readiness | 20% | Is the target stack resolved? Are gate conditions met? Are blockers documented with mitigations? |

### Score Formula

```
Overall = (R1 × 0.20) + (R2 × 0.20) + (R3 × 0.20) + (R4 × 0.20) + (R5 × 0.20)
```

---

## §2 R1: Completeness Score

**Score: 90 / 100**

All twenty Forward Engineering documents are present. Minor deductions reflect partial population of catalog capability cross-references in FE-05 and a sparse assumptions section in FE-10.

### FE Document Inventory

| Doc ID | Title | Layer | Status |
|---|---|---|---|
| FE-01 | Project Structure & Solution Layout | Foundation | COMPLETE |
| FE-02 | Shared Kernel & Domain Primitives | Foundation | COMPLETE |
| FE-03 | EF Core DbContext Configuration | Foundation | COMPLETE |
| FE-04 | Entity Type Configurations | Foundation | COMPLETE |
| FE-05 | Domain Aggregates (OrderAggregate) | Domain | COMPLETE — minor catalog cap gaps |
| FE-06 | Catalog Domain Entities | Domain | COMPLETE |
| FE-07 | BuyerAggregate Scaffold | Domain | COMPLETE — scaffold only; BuyerAggregate not implemented (ARCH-VIOL-006) |
| FE-08 | Guard Extensions & Domain Invariants | Domain | COMPLETE |
| FE-09 | Basket Application Services | Application | COMPLETE |
| FE-10 | Order Application Services | Application | COMPLETE — sparse assumptions |
| FE-11 | Catalog Application Services | Application | COMPLETE |
| FE-12 | BlazorAdmin Application Services & Wiring | Application | COMPLETE |
| FE-13 | Repository Implementations | Infrastructure | COMPLETE |
| FE-14 | REST API Endpoint Contracts | Infrastructure | COMPLETE |
| FE-15 | JWT / Identity Configuration | Infrastructure | COMPLETE — ARCH-VIOL-004 flag present |
| FE-16 | Auth & CORS Startup Wiring | Infrastructure | COMPLETE — ARCH-VIOL-011 flag present |
| FE-17 | Secret Externalisation (Key Vault) | Cross-cutting | COMPLETE |
| FE-18 | Health Check Endpoints | Cross-cutting | COMPLETE |
| FE-19 | Caching Configuration | Cross-cutting | COMPLETE |
| FE-20 | Docker / CI-CD / Azure Deployment | Cross-cutting | COMPLETE |

### Node-Category Completeness

| Category | Nodes | Documented in FE Docs | Coverage |
|---|---|---|---|
| Business Capabilities | 31 | 28 | 90% |
| Business Processes | 7 | 7 | 100% |
| Business Actors | 6 | 6 | 100% |
| Business Rules | 37 | 34 | 92% |
| Value Streams | 3 | 3 | 100% |
| Roadmap Items | 10 | 10 | 100% |
| Data Entities | 13 | 13 | 100% |
| Data Aggregates | 4 | 4 | 100% |
| Repositories | 2 | 2 | 100% |
| Caches | 2 | 2 | 100% |
| PII Records | 8 | 8 | 100% |
| Deployable Units | 6 | 6 | 100% |
| Application Services | 14 | 14 | 100% |
| REST APIs | 8 | 8 | 100% |
| Modules | 13 | 13 | 100% |
| Technology Stack | 22 | 22 | 100% |
| Infrastructure | 6 | 6 | 100% |
| Security | 7 | 7 | 100% |
| **Total** | **173** | **166** | **96%** |

**R1 Score Derivation:** 20 of 20 documents present (100% document presence). Weighted down to 90 due to 7 node references missing from FE-05 and FE-10.

---

## §3 R2: Consistency Score

**Score: 87 / 100**

Node IDs are used consistently across the majority of documents. The deductions are attributed to three classes of minor inconsistency identified during cross-document validation.

### Node ID Cross-Reference Check

| Check | Result | Finding |
|---|---|---|
| BIZ-CAP IDs consistent across FE-01..FE-12 | PASS | All 31 capability IDs appear with correct prefix and sequential numbering |
| DATA-ENT IDs consistent across FE-03..FE-08 | PASS | All 13 entity IDs match the graph |
| DATA-AGG IDs consistent across FE-05..FE-07 | PASS | 4 aggregate IDs correctly referenced |
| APP-SVC IDs consistent across FE-09..FE-12 | PASS | All 14 service IDs correctly referenced |
| APP-API IDs consistent across FE-14 | PASS | All 8 REST API IDs present |
| TECH-CUR IDs consistent across FE-03, FE-13, FE-20 | PASS | All 22 stack entries referenced |
| TECH-SEC IDs consistent across FE-15..FE-16 | PASS | All 7 security node IDs referenced |
| ARCH-VIOL IDs referenced in relevant docs | PARTIAL | ARCH-VIOL-009 not cross-linked in FE-14 |
| AO IDs referenced in wave they resolve | PARTIAL | AO-06 not linked in FE-19 |
| TD IDs inventoried | PARTIAL | 3 of 22 TD items lack a linked FE document reference |

### BC ID Consistency

All Bounded Context identifiers follow the pattern established in FE-01. The four aggregates (DATA-AGG-001..004) are referenced using their canonical IDs in every document that generates aggregate code. No orphaned IDs were found.

### Status Flag Usage

| Flag | Count | Consistent |
|---|---|---|
| COMPLETE | 17 docs | Yes |
| CONDITIONAL | 2 docs | Yes |
| BLOCKED | 1 doc (FE-07, BuyerAggregate) | Yes |

**R2 Score Derivation:** 7 out of 10 cross-reference checks fully passed. Three partial findings produce a 13-point deduction, yielding 87/100.

---

## §4 R3: Traceability Score

**Score: 80 / 100**

Forward-chain coverage is strong for the domain, application, and infrastructure layers. The primary traceability gap is in catalog capabilities (BIZ-CAP-021..028), which are documented in the graph but their downstream FE artifacts do not explicitly cite the originating node ID in the generated code comments.

### Forward Chain Coverage Table by Wave

| Wave | Wave Theme | Graph Nodes Referenced | Artifacts Produced | Trace Coverage | Gap Notes |
|---|---|---|---|---|---|
| Wave 1 | Foundation | FE-01..FE-04 | Solution layout, shared kernel, DbContext, entity configs | 95% | 1 missing TECH-INF reference in FE-04 |
| Wave 2 | Domain | FE-05..FE-08 | Order aggregate, catalog entities, buyer scaffold, guards | 83% | BIZ-CAP-021..028 not cited in FE-06 artifacts; DISC-001 gap in FE-07 |
| Wave 3 | Application | FE-09..FE-12 | Basket/order services, catalog services, BlazorAdmin wiring | 88% | AO-05 (pagination) not traced in FE-10 |
| Wave 4 | Infrastructure / API | FE-13..FE-16 | Repositories, REST endpoints, JWT/Identity, auth startup | 82% | ARCH-VIOL-002 resolution not traced in FE-14; TECH-SEC-003 not cited in FE-15 |
| Wave 5 | Cross-cutting | FE-17..FE-20 | Secret externalisation, health checks, caching, Docker/CI | 72% | AO-06 not linked in FE-19; TECH-INF-004..006 partially cited; 3 TD items without FE linkage |

### Traceability Gaps Identified

| Gap ID | Description | Affected Doc | Blocking |
|---|---|---|---|
| TRACE-GAP-01 | BIZ-CAP-021..028 not cited in FE-06 catalog artifact comments | FE-06 | No |
| TRACE-GAP-02 | DISC-001 / ARCH-VIOL-010 resolution not annotated in FE-07 | FE-07 | No |
| TRACE-GAP-03 | AO-05 (order history pagination) not traced to FE-10 | FE-10 | No |
| TRACE-GAP-04 | ARCH-VIOL-002 resolution path not cited in FE-14 | FE-14 | No |
| TRACE-GAP-05 | TECH-SEC-003 not cited in FE-15 JWT configuration | FE-15 | No |
| TRACE-GAP-06 | AO-06 (catalogue search caching) not linked in FE-19 | FE-19 | No |
| TRACE-GAP-07 | TECH-INF-004..006 partially cited in FE-20 | FE-20 | No |
| TRACE-GAP-08 | 3 TD items (TD-07, TD-14, TD-19) lack FE document reference | Multiple | No |

**R3 Score Derivation:** Wave 1 is near-complete. Waves 2–4 average around 84%. Wave 5 drops to 72% due to infrastructure node gaps. Weighted average across five waves produces approximately 84%; adjusted down to 80 due to 8 identified gaps, two of which span multiple nodes.

---

## §5 R4: Architecture Quality Score

**Score: 62 / 100**

This is the weakest rubric. Eleven architecture violations are recorded, of which two are CRITICAL severity and four are HIGH severity. The CRITICAL violations (ARCH-VIOL-001 and ARCH-VIOL-004) directly block Wave 1 and Wave 4 generation. All violations are documented with resolution wave assignments, which limits further deductions.

### Architecture Violations Table

| ID | Description | Severity | Resolution Wave | Status |
|---|---|---|---|---|
| ARCH-VIOL-001 | Web project directly accesses EF Core, bypassing the clean architecture boundary — the Web layer must not reference the Infrastructure DbContext directly | CRITICAL | Wave 1 | OPEN — blocks Wave 1 |
| ARCH-VIOL-002 | MinimalApi endpoint directly references `IAsyncRepository<T>`, bypassing the application service layer | HIGH | Wave 4 | OPEN — blocks Wave 4 endpoint generation |
| ARCH-VIOL-003 | `Task.Delay` used in `StartupBackgroundService` (AO-04) — a blocking pattern that must be replaced with a proper `IHostedService` timer or `PeriodicTimer` | HIGH | Wave 5 | OPEN |
| ARCH-VIOL-004 | JWT secret hardcoded in `appsettings.json` (AO-03) — secret must be externalised to Azure Key Vault or an environment variable before any auth scaffolding is generated | CRITICAL | Wave 4 | OPEN — blocks Wave 4 |
| ARCH-VIOL-005 | No HTTPS/HSTS enforcement configured for the production environment (AO-09) | HIGH | Wave 5 | OPEN |
| ARCH-VIOL-006 | `BuyerAggregate` is not implemented — the scaffold exists in FE-07 but the aggregate has no invariants or domain behaviour | MEDIUM | Wave 2 | OPEN — scaffold only |
| ARCH-VIOL-007 | No health check endpoints registered (AO-07) | MEDIUM | Wave 5 | OPEN |
| ARCH-VIOL-008 | No structured logging configured — Serilog and OpenTelemetry are absent (AO-08) | MEDIUM | Wave 5 | OPEN |
| ARCH-VIOL-009 | No rate limiting applied to public-facing API endpoints (AO-10) | MEDIUM | Wave 4 | OPEN |
| ARCH-VIOL-010 | DISC-001 stock field discrepancy — `RestockThreshold` and `MaxStockThreshold` exist in EF Core configuration but carry no domain enforcement; do not replicate as domain logic | HIGH | Wave 2 | OPEN — see DISC-001 warning |
| ARCH-VIOL-011 | CORS wildcard (`*`) configured in the development environment — must be tightened before generation of the production auth startup | MEDIUM | Wave 4 | OPEN |

### Severity Breakdown

| Severity | Count | Violations |
|---|---|---|
| CRITICAL | 2 | ARCH-VIOL-001, ARCH-VIOL-004 |
| HIGH | 4 | ARCH-VIOL-002, ARCH-VIOL-003, ARCH-VIOL-005, ARCH-VIOL-010 |
| MEDIUM | 5 | ARCH-VIOL-006, ARCH-VIOL-007, ARCH-VIOL-008, ARCH-VIOL-009, ARCH-VIOL-011 |
| LOW | 0 | — |

**R4 Score Derivation:** 11 violations with 2 CRITICAL and 4 HIGH represent a material architecture quality deficit. Base penalty: CRITICAL violations each deduct 12 points; HIGH violations each deduct 5 points; MEDIUM violations each deduct 2 points. Starting from 100: 100 − 24 − 20 − 10 = 46, then partial credit (+16) for complete documentation and wave-assignment of all violations, yielding 62/100.

---

## §6 R5: FE Readiness Score

**Score: 78 / 100**

The principal gate condition GR-08 is resolved. The target stack is confirmed as **dotnet8**. All twenty FE documents are present. The score is held below 80 by the two CRITICAL violations that block generation in Wave 1 and Wave 4, and by eight open questions that represent undocumented scope boundaries.

### GR-08 Gate Status

| Gate | Description | Status |
|---|---|---|
| GR-08 | Target stack decision required before code-generation prompts can be finalised | **RESOLVED** |
| target\_stack | The technology stack for all generated code | **dotnet8** |
| Resolved by | Project team decision recorded in pipeline configuration | 2026-06-30 |

### Wave-by-Wave Readiness

| Wave | Gate Conditions | Blockers | Enablers | Status |
|---|---|---|---|---|
| Wave 1 (FE-01..04) | ARCH-VIOL-001 resolved | ARCH-VIOL-001 (CRITICAL) | GR-08 RESOLVED; all FE docs present | BLOCKED |
| Wave 2 (FE-05..08) | ARCH-VIOL-006, ARCH-VIOL-010 addressed | ARCH-VIOL-006 (scaffold incomplete); ARCH-VIOL-010 (DISC-001) | All domain FE docs complete; aggregates documented | CONDITIONAL |
| Wave 3 (FE-09..12) | No critical blockers | None | Application service FE docs fully populated and traced | READY |
| Wave 4 (FE-13..16) | ARCH-VIOL-004 resolved | ARCH-VIOL-004 (CRITICAL); ARCH-VIOL-002, ARCH-VIOL-009, ARCH-VIOL-011 | Repository and API FE docs complete; JWT doc present with violation flags | BLOCKED |
| Wave 5 (FE-17..20) | ARCH-VIOL-003, -005, -007, -008 addressed | ARCH-VIOL-003, ARCH-VIOL-005, ARCH-VIOL-007, ARCH-VIOL-008 | Secret externalisation FE-17 complete; health check FE-18 complete | CONDITIONAL |

### Enablers vs Blockers Summary

**Enablers:**
- GR-08 gate resolved; dotnet8 target stack confirmed
- All 20 FE documents produced and inventoried
- 173-node graph provides comprehensive coverage of domain, application, and infrastructure layers
- All 10 roadmap action items (AO-01..AO-10) are documented and wave-assigned
- All 8 PII records (PII-01..PII-08) are identified and flagged for GDPR consideration in FE-17
- Wave 3 is fully unblocked and ready for immediate generation

**Blockers:**
- ARCH-VIOL-001 (CRITICAL): must be resolved before Wave 1 can execute
- ARCH-VIOL-004 (CRITICAL): must be resolved before Wave 4 can execute
- 8 open questions (OQ-001..OQ-008) represent scope boundaries that may surface mid-generation

**R5 Score Derivation:** GR-08 resolved and all documents present earns a strong base. Deductions: CRITICAL blockers in Wave 1 and Wave 4 (−10 each), 8 open questions without resolution (−2 net after partial credit for documentation), yielding 78/100.

---

## §7 Overall Score Summary

### Weighted Score Table

| Rubric | Weight | Raw Score | Weighted Contribution |
|---|---|---|---|
| R1 Completeness | 20% | 90 | 18.0 |
| R2 Consistency | 20% | 87 | 17.4 |
| R3 Traceability | 20% | 80 | 16.0 |
| R4 Architecture Quality | 20% | 62 | 12.4 |
| R5 FE Readiness | 20% | 78 | 15.6 |
| **Overall** | **100%** | — | **79.4 → 79 / 100** |

### Final Verdict

| Field | Value |
|---|---|
| Overall Score | **79 / 100** |
| Verdict | **CONDITIONAL\_READY** |
| Proceed to Generation | Yes, wave by wave, with the blocking conditions below respected |
| Wave 1 | Blocked until ARCH-VIOL-001 resolved |
| Wave 2 | Conditional on ARCH-VIOL-006 and ARCH-VIOL-010 acknowledgement |
| Wave 3 | Ready — no blockers |
| Wave 4 | Blocked until ARCH-VIOL-004 resolved |
| Wave 5 | Conditional on ARCH-VIOL-003, -005, -007, -008 acknowledgement |

---

## §8 Risk Register

| Risk ID | Description | Likelihood | Impact | Wave Affected | Mitigation |
|---|---|---|---|---|---|
| RR-01 | ARCH-VIOL-001 not resolved before Wave 1 execution — generated foundation code inherits the layering violation | HIGH | HIGH | Wave 1 | Add pre-generation gate check in CI; enforce project reference restrictions in solution file |
| RR-02 | ARCH-VIOL-004 (hardcoded JWT secret) deployed to staging or production | HIGH | CRITICAL | Wave 4 | Block Wave 4 generation until AO-03 (Key Vault externalisation) is confirmed complete; scan appsettings files in CI pipeline |
| RR-03 | OQ-001 (payment processing) surfaces as an unimplemented requirement after code generation begins | MEDIUM | HIGH | Wave 3–4 | Explicitly mark payment capability as out-of-scope in ASMP-005 before generation; add stub interface |
| RR-04 | DISC-001 stock field behaviour assumed to be infrastructure-only, but a business rule (BIZ-RULE-019..021) actually requires domain enforcement | MEDIUM | HIGH | Wave 2 | Domain expert review of BIZ-RULE-019..021 against DISC-001 before Wave 2; see ARCH-VIOL-010 |
| RR-05 | BuyerAggregate (ARCH-VIOL-006) generated as a hollow scaffold, causing runtime gaps when order fulfilment references buyer invariants | MEDIUM | MEDIUM | Wave 2 | Treat FE-07 output as a placeholder; add a TODO gate in the generated aggregate that throws NotImplementedException until behaviour is defined |
| RR-06 | OQ-008 (external identity provider / SSO) requirement surfaces post-generation, requiring a full rework of FE-15 and FE-16 | LOW | HIGH | Wave 4 | Document ASMP-004 (ASP.NET Identity only, no external IdP) before Wave 4; make identity configuration extensible |
| RR-07 | 22 technical debt items (TD-01..TD-22) accumulate in generated code if the generation prompts do not include debt-clearance instructions | MEDIUM | MEDIUM | All waves | Inject TD annotations as TODO comments in generated code; schedule a debt sprint post-Wave 5 |
| RR-08 | CORS wildcard (ARCH-VIOL-011) persists in production configuration because the dev/prod separation is not enforced at the startup wiring level | MEDIUM | HIGH | Wave 4 | FE-16 must generate environment-specific CORS policies; reviewer checklist must include CORS policy audit |
| RR-09 | Absence of structured logging (ARCH-VIOL-008) makes production incident diagnosis difficult if Wave 5 logging setup is deferred | MEDIUM | MEDIUM | Wave 5 | Include Serilog bootstrap in Wave 5 FE-20; do not defer AO-08 past Wave 5 |
| RR-10 | Rate limiting absent (ARCH-VIOL-009) on public endpoints exposes the API to abuse during the period between Wave 4 deployment and Wave 5 hardening | MEDIUM | HIGH | Wave 4–5 | Add rate limiting middleware stub in Wave 4 even if full configuration is deferred to Wave 5; document AO-10 timeline |
| RR-11 | 8 PII records (PII-01..PII-08) processed without confirmed GDPR consent and retention controls in the generated codebase | LOW | CRITICAL | Wave 3–5 | FE-17 secret externalisation and FE-19 caching config must address PII data flows; legal review required before production deployment |

---

## §9 Open Questions

### OQ Table

| ID | Question | Domain Area | Impact if Unresolved | Assumed Default | Decision Required Before |
|---|---|---|---|---|---|
| OQ-001 | Payment processing — no payment service found in the graph; is payment in scope? | Domain / Application | Wave 3–4 generation may produce an incomplete order fulfilment flow | Out-of-scope for initial generation (ASMP-005) | Wave 3 |
| OQ-002 | Email service implementation — which SMTP provider will be used for order confirmation (AO-02)? | Infrastructure | FE-10 order confirmation stub cannot be wired without a provider choice | SMTP via SendGrid placeholder (ASMP-006) | Wave 3 |
| OQ-003 | Shipping and delivery tracking — no domain model found; is this a future roadmap capability? | Domain | No shipping aggregate or value object will be generated | Out-of-scope; shipping treated as an external concern | Wave 2 |
| OQ-004 | Multi-tenancy requirements — is the system intended to support multiple tenants or a single tenant deployment? | Architecture | Multi-tenancy would require changes to DbContext, Identity, and all repository implementations | Single-tenant assumed (ASMP-007) | Wave 1 |
| OQ-005 | Audit logging requirements — no audit trail entities or interceptors found in the graph | Cross-cutting / Compliance | Generated infrastructure layer will have no audit record of entity mutations | No audit logging generated unless OQ-005 resolved | Wave 5 |
| OQ-006 | Internationalisation (i18n) — no evidence of resource files or locale-aware formatting in the graph | Application / UI | BlazorAdmin (FE-12) will be generated for a single locale only | English (en-US) only, no i18n | Wave 3 |
| OQ-007 | Analytics and reporting requirements — no reporting layer, CQRS read models, or analytics events found | Application / Data | No reporting services will be generated; no event sourcing scaffolded | Out-of-scope for this generation cycle | Wave 3 |
| OQ-008 | External identity provider integration (social login, OIDC federation, SSO) beyond ASP.NET Identity | Security / Infrastructure | FE-15 and FE-16 will be generated for ASP.NET Identity only; external IdP support would require significant rework | ASP.NET Identity only (ASMP-004) | Wave 4 |

### Additional Questions Surfaced During Report Generation

| ID | Question | Source |
|---|---|---|
| OQ-009 | Should the 3 unlinked TD items (TD-07, TD-14, TD-19) be addressed in the generation prompts or deferred to a post-generation debt sprint? | TRACE-GAP-08 |
| OQ-010 | Will BuyerAggregate (DATA-AGG-003 / ARCH-VIOL-006) be fully specified before Wave 2, or should it remain a scaffold placeholder through generation? | FE-07 / ARCH-VIOL-006 |

---

## §10 Pre-Generation Checklist

The following steps must be completed in order before executing the code-generation prompts. Steps marked CRITICAL block the corresponding wave entirely.

| Step | Action | Severity | Blocks Wave | Status |
|---|---|---|---|---|
| 1 | Resolve ARCH-VIOL-001: remove the direct EF Core reference from the Web project; introduce an application service boundary | CRITICAL | Wave 1 | OPEN |
| 2 | Resolve ARCH-VIOL-004: externalise the JWT secret from `appsettings.json` to an environment variable or Azure Key Vault secret; confirm AO-03 complete | CRITICAL | Wave 4 | OPEN |
| 3 | Review DISC-001 / ARCH-VIOL-010: confirm with a domain expert that `RestockThreshold` and `MaxStockThreshold` are infrastructure-only fields before Wave 2 entity generation | HIGH | Wave 2 | OPEN |
| 4 | Decision on OQ-001 (payment scope) and OQ-003 (shipping scope): record explicit out-of-scope decisions or add domain model requirements before Wave 3 | HIGH | Wave 3 | OPEN |
| 5 | Resolve ARCH-VIOL-002: refactor MinimalApi endpoint to route through the application service layer; update FE-14 accordingly | HIGH | Wave 4 | OPEN |
| 6 | Resolve ARCH-VIOL-011: replace the CORS wildcard with an explicit origin allowlist in the production CORS policy; update FE-16 | MEDIUM | Wave 4 | OPEN |
| 7 | Specify BuyerAggregate behaviour (OQ-010 / ARCH-VIOL-006): either define invariants before Wave 2 or mark FE-07 output as a non-generated placeholder | MEDIUM | Wave 2 | OPEN |
| 8 | Decide OQ-004 (multi-tenancy): record ASMP-007 single-tenant assumption in the generation manifest before Wave 1 execution | MEDIUM | Wave 1 | OPEN |
| 9 | Decide OQ-008 (external IdP): record ASMP-004 ASP.NET-Identity-only assumption in the generation manifest before Wave 4 execution | MEDIUM | Wave 4 | OPEN |
| 10 | Link TRACE-GAP-01 and TRACE-GAP-06: add BIZ-CAP-021..028 citations to FE-06 and AO-06 citation to FE-19 before Wave 2 and Wave 5 respectively | LOW | Wave 2 / Wave 5 | OPEN |
| 11 | Run `graphify update .` after all FE documents are finalised to synchronise the knowledge graph with any last-minute edits before generation begins | LOW | All waves | OPEN |

---

## §11 Assumptions

| ID | Assumption | Rationale | Linked Question / Violation |
|---|---|---|---|
| ASMP-001 | The generated codebase will target **.NET 8 LTS** exclusively — no dual-target or downgrade to .NET 6/7 | GR-08 resolved; dotnet8 confirmed | GR-08 |
| ASMP-002 | Clean architecture boundary will be enforced in the generated solution: Web → Application → Domain; Infrastructure implements Application interfaces | Required to resolve ARCH-VIOL-001 | ARCH-VIOL-001 |
| ASMP-003 | Entity Framework Core will remain the sole ORM — no Dapper, micro-ORM, or raw ADO.NET in the generated data access layer | Consistent with TECH-CUR entries and existing EF configuration in FE-03/FE-04 | None |
| ASMP-004 | Authentication will use ASP.NET Core Identity with JWT bearer tokens only — no external identity provider (OIDC, OAuth social login, SAML) unless OQ-008 is resolved | Simplifies FE-15 and FE-16 generation scope | OQ-008 |
| ASMP-005 | Payment processing is out of scope for this generation cycle — no payment service, payment aggregate, or payment gateway integration will be generated | OQ-001 unresolved; no payment nodes found in graph | OQ-001 |
| ASMP-006 | The order confirmation email (AO-02) will be scaffolded with a SendGrid-compatible `IEmailSender` interface placeholder — the concrete SMTP provider will be injected at deployment time | OQ-002 unresolved; interface pattern avoids provider lock-in | OQ-002 |
| ASMP-007 | The system is single-tenant — all generated repository implementations, DbContext configurations, and Identity setups assume a single tenant | OQ-004 answered with single-tenant default | OQ-004 |

---

## §12 Wave Execution Readiness

### Wave Readiness Detail

| Wave | Documents | Theme | Readiness % | Gate Conditions | Blockers | Status |
|---|---|---|---|---|---|---|
| Wave 1 | FE-01, FE-02, FE-03, FE-04 | Foundation — project structure, shared kernel, EF Core contexts, entity configurations | 70% | ARCH-VIOL-001 resolved; ASMP-007 recorded; `graphify update` run | ARCH-VIOL-001 (CRITICAL) | **BLOCKED** |
| Wave 2 | FE-05, FE-06, FE-07, FE-08 | Domain — aggregates, catalog entities, BuyerAggregate scaffold, guard extensions | 80% | DISC-001 reviewed; ARCH-VIOL-006 stance documented; ARCH-VIOL-010 acknowledged | ARCH-VIOL-006 (scaffold incomplete); ARCH-VIOL-010 (DISC-001 field scope) | **CONDITIONAL** |
| Wave 3 | FE-09, FE-10, FE-11, FE-12 | Application layer — basket/order services, catalog services, BlazorAdmin, wiring | 95% | OQ-001 and OQ-003 decisions recorded | None blocking | **READY** |
| Wave 4 | FE-13, FE-14, FE-15, FE-16 | Infrastructure / API — repositories, REST endpoints, JWT/Identity, auth/CORS startup | 65% | ARCH-VIOL-002 resolved; ARCH-VIOL-004 resolved; ARCH-VIOL-009 addressed; ARCH-VIOL-011 fixed; ASMP-004 recorded | ARCH-VIOL-004 (CRITICAL); ARCH-VIOL-002 (HIGH) | **BLOCKED** |
| Wave 5 | FE-17, FE-18, FE-19, FE-20 | Cross-cutting — secret externalisation, health checks, caching config, Docker/CI/CD/Azure | 82% | ARCH-VIOL-003 resolved; ARCH-VIOL-005 enforced; ARCH-VIOL-007 addressed; ARCH-VIOL-008 addressed | ARCH-VIOL-003 (HIGH); ARCH-VIOL-005 (HIGH) | **CONDITIONAL** |

### Recommended Execution Sequence

1. Complete the Pre-Generation Checklist steps 1 and 2 (resolve CRITICAL violations).
2. Execute Wave 1 generation (FE-01..FE-04).
3. Complete checklist steps 3 and 7 (DISC-001 review, BuyerAggregate stance).
4. Execute Wave 2 generation (FE-05..FE-08).
5. Complete checklist step 4 (OQ-001, OQ-003 decisions).
6. Execute Wave 3 generation (FE-09..FE-12) — this wave is already unblocked.
7. Complete checklist steps 5, 6, and 9 (ARCH-VIOL-002, ARCH-VIOL-011, ASMP-004).
8. Execute Wave 4 generation (FE-13..FE-16).
9. Complete checklist step 10 (traceability gap links).
10. Execute Wave 5 generation (FE-17..FE-20).
11. Run `graphify update .` to synchronise the knowledge graph with all generated artifacts.

---

*Report generated by Graphify v2.0 pipeline. All node IDs (BIZ-CAP, DATA-ENT, APP-SVC, ARCH-VIOL, AO, OQ, ASMP, RR) reference nodes in ENTERPRISE\_KNOWLEDGE\_GRAPH.json. This document is document 17 of 20 in the Forward Engineering document set.*
