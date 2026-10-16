# CMS Quality Intelligence — Product & Implementation Plan

**Version:** 1.0  
**Date:** October 15, 2026  
**Status:** Product scoping complete (55 decisions); implementation not started  
**Project purpose:** An evidence-grounded, AI-assisted platform for tracking, explaining, and reviewing changes to CMS quality measure requirements.

> This document consolidates the decisions made during product discovery. It is a product and implementation plan, not a statement that CMS documents have all been ingested or that the specified features are already built. The 2026 AI Dev Tools Zoomcamp rubric is a draft and should be rechecked before submission.

## 1. Vision, users, and product boundaries

**Primary users:** (1) Healthcare Data Analysts and (2) ACO Quality & Performance Teams.

**Primary task:** Track changes to CMS quality measures between performance years, starting with 2025 and 2026 MSSP / APP Plus. **Secondary task:** Explore and understand measure definitions and specifications.

**Core user questions**

- What changed between performance years 2025 and 2026?
- Was a measure added, removed, or modified? Which specification fields changed?
- Is a difference substantive or a wording-only revision?
- What official CMS evidence supports this conclusion?
- What are the potential analytics, SQL logic, dashboard, data collection, and ACO operational implications?
- What tasks remain outstanding and what was previously reviewed?

**Initial coverage:** Complete APP Plus measure sets applicable to MSSP for performance years 2025 and 2026, including unchanged measures. Verify year-specific membership from authoritative CMS guidance before claiming completeness. Keep publication date, performance year, effective date, source revision, and regulatory status distinct.

**Not intended:** A booking tool, an EHR/claims integration, production-ready SQL generator, autonomous compliance decision maker, or all-CMS-program policy platform. No patient-level data or PHI is required.

## 2. Product experience

### 2.1 Public homepage

A **combined homepage** includes:

- Summary counts for measures added, removed, modified, and unchanged.
- A **What's New** feed of recently approved changes with links and dates.
- A searchable measure list with keyword search and structured filters.
- A performance-year comparison selector, initially offering 2025 and 2026.
- A separate publication timeline showing when CMS announced or revised materials.

Advanced filters include name/ID/description, reporting year, change status, changed specification field (numerator, denominator, exclusions, eligibility, calculation logic), and review/verification status where publicly appropriate. Numerical AI-generated impact prioritization is deferred.

### 2.2 Dedicated measure pages

Clicking a measure opens its own shareable page. **Previous/Next** moves through the filtered list while preserving dashboard context. Tabs:

1. **Overview** — identity, description, years, numerator, denominator, exclusions, eligibility, calculations, source references, verified fields, freshness information.
2. **Changes** — side-by-side year comparisons, field highlights, add/remove/modify/unchanged states, wording-only vs substantive distinction, citations and excerpts.
3. **AI Impact & Tasks** — qualitative impact analysis and role-specific views; public visitors can see approved explanations but not internal checklists.
4. **History** — source/publication changes and public verification metadata; internal review events are restricted to admin.

**Role toggle on each measure page:** Data Analyst versus ACO Quality Manager. Both role-specific explanations are generated/stored in advance and switching should not trigger another API call.

### 2.3 Public versus admin visibility

**Public, no login:** Browse approved measures, verified specifications, change summaries, CMS excerpts and links, role-specific approved AI explanations, last reviewed date, last source check and whether newer source material exists; export structured CSV/Excel data. No internal notes, private checklists, or review activity timeline.

**Admin, authenticated single account:** Manage CMS sources, trigger ingestion, inspect documents and processing, correct/verify extracted changes, edit/approve AI explanations, manage checklists, view central review dashboard, sign off/reopen reviews, and inspect full audit events.

The admin account should use a proper secure authentication mechanism, not a hardcoded password in source. Authorization must be enforced in backend endpoints.

## 3. Five core features

### 3.1 Measure Explorer

- Complete verified year-specific APP Plus inventory for 2025–2026, including measures unchanged across years.
- Keyword search and structured filters; no conversational search in the MVP.
- Individual measure pages and year selector; support future years without redesign.
- Display sources and verification/freshness metadata.

### 3.2 Version Comparison

- Dashboard-level change overview, then detailed side-by-side specifications.
- Track additions/removals and specification fields: numerators, denominators, exclusions, eligibility and calculation definitions.
- **Hybrid engine:** deterministic normalized-field comparisons, followed by AI semantic analysis to identify substantive vs wording-only differences.
- Missing, unavailable, or uncertain fields must **not** be treated as confirmed removals or changes.
- Preserve source revisions and invalidate affected comparisons for re-verification when upstream evidence changes.
- Show change type, affected area, and qualitative impact explanation; defer numerical severity scores.

### 3.3 AI Change Explanation

- Generate **automatically after verified change approval**; admin edits and approves both role-specific explanations together before publication.
- Explain **what changed** in plain language, then **why it matters** technically and operationally.
- Data Analyst view: possible field mapping, denominator/numerator logic, SQL considerations, dashboard modifications, testing and validation recommendations; **not** production-ready SQL.
- ACO Quality Manager view: reporting process, data collection, team coordination, and operational implications.
- Every claim must be tied to valid CMS source excerpts/links; disclose uncertainty and distinguish hypothesis from fact.
- If source/specification data changes, mark the explanation **outdated**; MVP regeneration is **manual**. Preserve prior explanation versions privately with timestamps; newly approved explanations replace the public display.
- On regeneration, preserve active checklist tasks and completed work; show new suggested tasks separately for admin consideration.

### 3.4 Impact Checklist

- AI proposes actionable review items; admin can accept, edit, add, mark completed, or mark not applicable.
- One shared checklist per relevant review, with filters **All / Data Analyst / ACO Quality Manager**, not duplicate checklists.
- Preserve task updates, timestamps, notes, accepted suggestions and progress.
- Centralized admin Review Dashboard across measures with outstanding tasks, statuses, and completion statistics.
- Completion requires accepted checklist items completed or marked not applicable **and final admin sign-off**.

### 3.5 Review History

- Per-measure timeline with status transitions, edits, checklist actions, notes, and sign-off dates.
- Admin can reopen completed reviews and sign off again; maintain the previous audit history.
- When a relevant new CMS specification is detected, change the prior completed review to **Needs Re-review**, without erasing earlier sign-offs.
- Visitors see only public verification/status metadata and last-reviewed dates, not internal reviews.

## 4. CMS source ingestion and verification

### 4.1 Sources

- **Admin-managed source registry** initially seeded with a vetted list of official CMS MSSP/APP Plus sources.
- Admin can add/remove official CMS URLs. Automatic discovery across CMS websites is deferred.
- MVP supports **PDFs and official CMS webpages (HTML)**. Structured CSV/XLSX support can be added when actual source availability justifies it.
- Store URL, title, publication date, source type, source version/hash, retrieval metadata, associated years/programs, and processing status.

Example starting points (verify actual authoritative document links before loading data):

- CMS MSSP guidance: https://www.cms.gov/medicare/payment/fee-for-service-providers/shared-savings-program-ssp-acos/guidance-regulations
- CMS Measures Inventory: https://cmit.cms.gov/
- CMS CY 2025 and CY 2026 Medicare Physician Fee Schedule final-rule fact sheets and associated measure specifications.

### 4.2 Ingestion trigger and lifecycle

**MVP:** Admin clicks **Check for Updates**. **Later:** Optional scheduled checks using the same pipeline.

Pipeline:

1. Check registered official sources for updates.
2. Skip unchanged documents based on dependable content/version signals; optionally force reprocessing even when unchanged.
3. Fetch changed PDF or HTML sources, preserve original and metadata where appropriate.
4. Extract text and structured measure fields; flag ambiguous or incomplete fields.
5. Compare to stored verified versions using deterministic and AI semantic checks.
6. When uncertain, AI may consult *additional official CMS sources* to propose clarification; human verification remains mandatory.
7. Queue candidates in an **editable admin verification workspace** with source excerpts/links; admin corrects or approves/rejects items.
8. After specification approval, generate role-specific explanation and task proposals for edit-and-approve review.
9. Publish verified fields and approved analysis; withhold unresolved fields rather than presenting them as fact.

**Document Management Workspace:** source registry, previews, extracted content, progress by step (Downloading → Extracting → Comparing → Awaiting Verification), timestamps, persistent errors, and reprocess controls. Temporary failures automatically retry; persistent failures flag for admin action. Full token/cost analytics and step-by-step resumable execution are deferred.

**When sources change:** preserve old source versions. Flag reviews based on older versions as outdated and require re-verification before publication. Revisions that affect completed reviews set status to **Needs Re-review**. Previous signed-off work must remain recoverable.

**Approval:** MVP allows editing and approving individual extracted changes. Bulk/batch verification and approval are post-MVP.

**Partial publication:** Verified fields can be published despite other fields remaining unresolved; internal unresolved flags are retained, and public-facing explanation must avoid relying on them.

## 5. End-to-end workflows

### Workflow A: Administrative ingestion → publication

1. Sign in as admin and manage source registry.
2. Click Check for Updates.
3. Watch document processing status, automatic retry, errors, and extraction results.
4. Examine proposed additions/removals/specification differences with official excerpts.
5. Correct and approve verified fields; unresolved elements remain pending.
6. Review and edit two AI impact explanations (Data Analyst, ACO Quality Manager) and suggested checklist items.
7. Approve the explanation pair and publish.
8. Public dashboard and measure pages reflect approved data with source freshness indicators.

### Workflow B: Public research

1. Visit combined homepage and review summary + What's New.
2. Search/filter APP Plus measures and select performance years.
3. Open a measure page; compare 2025/2026 side by side.
4. Inspect highlighted changes, CMS excerpts and official source links.
5. Toggle Data Analyst / ACO Quality Manager explanation.
6. Move Previous/Next through filtered measures; export CSV/Excel if useful.

### Workflow C: Administrative impact follow-up

1. Open the central Review Dashboard.
2. Choose measure; inspect tasks filtered by role.
3. Accept/edit/add/complete/mark not applicable and leave notes.
4. Final sign-off after all accepted tasks resolved.
5. Reopen as needed; history retains actions.
6. When new CMS source arrives, automatically set Needs Re-review and require reassessment.

## 6. Technical architecture

**Approach:** Small modular monolith; no unnecessary microservices or autonomous production agents.

| Layer | Initial technology | Purpose |
| --- | --- | --- |
| Frontend | React + TypeScript | Dashboards, filters, comparison, review workspace |
| API | FastAPI + Pydantic | Backend endpoint validation, API contract |
| Database | PostgreSQL | Versioned measures, sources, changes, explanations, checklists, audit events |
| AI | OpenAI API (structured output) | Extraction assistance, semantic change classification, cited explanations and impact tasks |
| Processing | Python PDF/HTML parsers | Source retrieval, normalized extraction, pipeline orchestration |
| Containerization | Docker Compose | Local reproducibility |
| Tests | pytest + frontend tests | Deterministic comparisons, contract/API flows, admin/public permissions, AI evaluations |
| CI/CD | GitHub Actions | Tests, security checks, deployment steps |
| Deployment | Managed low-cost services or single cloud server | Public portfolio deployment after local validation |

**Source of truth:** Official CMS documentation; AI interpretations never supersede verified source content. Start with structured/text search rather than introducing a vector DB unless data demands it.

### Suggested data entities

- `sources` and `source_revisions`: document provenance, hashes, published/retrieved timestamps, official URLs and text excerpts.
- `measures` and `measure_versions`: stable measure identity, program association, performance year and normalized specifications.
- `change_candidates` and `approved_changes`: extraction proposals, deterministic field diffs, semantic interpretation, evidence and verification status.
- `explanations` (versioned): two role-specific views, evidence, model/prompt metadata, status and approvals.
- `review_items`: checklist items, role tags, status, source/AI origin, user edits.
- `review_events` and `reviews`: append-only activity trail, comments, sign-offs, reopen/re-review status.
- `ingestion_runs` and `ingestion_steps`: progress, retries, document processing outcome.

Ensure stable measure IDs and program-specific applicability. Do not conflate "not found in extracted source" with "removed from program".

### Minimal API groups

- Public measures, versions, and search/filter (`GET /api/measures`, `GET /api/measures/{id}`, `GET /api/measures/{id}/versions`).
- Public changes and comparison (`GET /api/changes`, `GET /api/changes/{id}`, comparison endpoint).
- Public approved explanations, CMS references, freshness metadata and export.
- Admin authentication and protected source registry, ingestion triggers/status, candidate review/approval.
- Admin explanation editing/approval and manual regeneration.
- Admin checklist review, activity trail, sign-off and reopening.

Write `openapi.yaml` and contract tests early. Restrict admin endpoints server-side; do not rely on merely hiding frontend buttons.

## 7. Phased MVP delivery

**Agreed strategy:** Phased MVP with incremental usable releases, not all functionality simultaneously. Estimates should be revisited after evaluating real CMS source complexity.

### M1 — Working Measure Explorer

- Verify complete 2025 and 2026 APP Plus measure membership from official sources.
- Build schema, seed normalized versions, simple FastAPI endpoints and React explorer.
- Implement combined homepage, counts, measure search/filter, flexible two-year selector, dedicated pages and Previous/Next.
- Show provenance, official source links and freshness fields.
- **Done when:** Visitors can explore the verified dataset without an AI call.

### M2 — Change Intelligence

- Deterministic normalized-field comparison and side-by-side UI.
- Semantic classification to distinguish meaningful from wording-only changes, with evaluation cases.
- Change dashboard, field-specific filters, What's New and publication timeline.
- Evidence excerpts and approved role-specific AI explanation rendering.
- **Done when:** Visitors can investigate an actual, verified measure change with supporting evidence.

### M3 — Automated Ingestion and Verification

- Admin account, source registry, PDF/HTML processing, incremental checks and force reprocess.
- Extraction, source revisions/hashes, stage progress, retries/errors.
- Editable verification queue, partial publication logic, additional-source clarification, stale-review handling.
- Explanation edit/approval, manual regeneration and private version history.
- **Done when:** Admin can ingest an official source revision and verify/publish changes end-to-end.

### M4 — Review Workflow, QA, and Release

- Shared, role-filtered interactive checklist, centralized review dashboard, review timeline, sign-off/reopen/re-review.
- CSV and Excel exports.
- Unit, integration, AI evaluation, security scans, Docker reproducibility and cloud demo.
- Course documentation and small development-only agent extension pack.
- **Done when:** Full workflow runs, passes tests, and can be demonstrated publicly and reproducibly.

**Sequencing note:** M2 can initially display pre-reviewed and pre-generated explanations from verified test fixtures. M3 automates the ingestion and approval needed to produce those records at scale.

## 8. AI quality and safety rules

- Extracted fields include provenance references; uncertain fields cannot silently become verified facts.
- Deterministic field diff is authoritative for normalized value changes. AI classifies semantic significance and gives bounded interpretations, not policy rulings.
- Clearly distinguish “field missing,” “unchanged,” “substantively changed,” and “wording-only changed.”
- Use official CMS excerpts and exact source URLs for grounded explanations.
- Require human review of extracted data and AI explanations before public publication.
- Validate structured outputs against schemas; reject unsupported references.
- Evaluation fixtures should include unchanged measures, added/removed measures, substantive changes, paraphrases, missing fields and conflicting sources.
- Track actual evaluation results instead of asserting unmeasured reliability.
- Reprocessed sources must not erase earlier versions, reviewer notes or checklist history.

## 9. Zoomcamp rubric alignment without feature bloat

The 2026 project rubric is draft: https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md

| Rubric area | Evidence | Rationale |
| --- | --- | --- |
| Problem and product | `README.md`, `product-spec.md` | Clear problem, personas, workflow and scope |
| AI-assisted development | `AGENTS.md`, documented prompts, manual review and verification | Demonstrate how development tools were used |
| Architecture | `docs/architecture.md` | Roles of React, FastAPI, PostgreSQL, AI, Docker |
| Frontend | React application + frontend tests | Real interactive comparison and review screens |
| API contract | `openapi.yaml` + contract tests | Supports explicit frontend/backend boundary |
| Backend | FastAPI routes, services + tests | Implements contract and product logic |
| Database | schema/migrations/seed | Durable versions, history and tasks |
| Docker | `docker-compose.yml` | Local end-to-end reproducibility |
| Integration tests | API/database and ingestion-to-publication scenarios | Trustworthy workflow |
| Deployment | Public working demo | Portfolio showcase |
| CI/CD | GitHub Actions test/check/deploy pipeline | Reliability |
| Agent extension pack | Small CMS Source Verification development toolkit | Separate from production UI, course-specific |
| Security/DevOps | Scans, PR audit, permissions and data policy | Protect admin actions and provenance |
| Reproducibility | Setup, test, and deployment instructions | Clear for peers |

**Agent extension pack (development tooling only):** One read-only MCP capability for consulting the local curated evidence base, reusable validation workflow, specialist instructions, a guardrail for changes to approved source data, and permission notes. Do not force agents into the end-user production request path solely for rubric points.

## 10. Post-MVP roadmap

- Scheduled automated CMS source checks (in addition to admin trigger).
- Batch extraction verification and approval.
- AI-assisted High/Medium/Low impact prioritization *after* constructing a defensible and evaluated rubric.
- Natural-language measure search.
- Formatted PDF impact reports.
- More performance years and historical visualizations.
- Expanded quality programs beyond MSSP/APP Plus.
- Auto-regeneration of explanations with version history and approval.
- More extensive document viewer, structured CSV/Excel ingestion, autonomous discovery with approval.
- Multiple named users, reviewer roles, task assignments, deadlines, and team workflow.
- Detailed cost/token observability and more granular processing resume behavior.

## 11. Decisions log: 55 scoping questions

The table below records every confirmed choice, including MVP-first and future-stage qualifications. Question numbers preserve the original discovery sequence.

| # | Decision | Confirmed scope |
| --- | --- | --- |
| 1 | Target users | A + B: Healthcare Data Analysts and ACO Quality & Performance Teams |
| 2 | Primary task | B: Year-over-year changes first; measure exploration second |
| 3 | Program | A: MSSP/ACO quality measures only, 2025 vs. 2026 |
| 4 | Data acquisition | B: Automated CMS ingestion |
| 5 | Ingestion trigger | B first (admin-triggered); C later (plus scheduled) |
| 6 | Publication verification | B: Human approval before publication |
| 7 | Changes tracked | B: Inventory and specification changes |
| 8 | Comparison interface | C: Dashboard plus side-by-side drill-down |
| 9 | AI content | C: Plain-language plus technical/operational impact |
| 10 | Impact checklist | B: Interactive editable and trackable tasks |
| 11 | Review history | B: Activity timeline |
| 12 | Access | B: Public explorer plus authenticated admin |
| 13 | AI interaction | A: Automatically generated explanation after approval |
| 14 | Source revisions | B: Preserve history and flag affected analysis for re-review |
| 15 | Dashboard structure | C: Summary and measure-level drill-down |
| 16 | Measure navigation | C: Dedicated pages + Previous/Next |
| 17 | Filters | B first (advanced); C AI impact priority later |
| 18 | Updates | B: Dashboard + What's New |
| 19 | Evidence | B: Source excerpts and links |
| 20 | Export | B first: CSV/Excel; PDF post-MVP |
| 21 | Change significance | C: Type, affected area and qualitative impact |
| 22 | Admin verification | B first: Editable workspace; C batch later |
| 23 | Uncertain extraction | B: AI clarification with extra official CMS sources |
| 24 | Unresolved fields | B: Publish only verified fields; withhold unresolved |
| 25 | Source management | B: Document management workspace |
| 26 | Repeat ingestion | C: Incremental processing with force reprocess |
| 27 | New source during review | B: Flag outdated and require re-verification |
| 28 | Processing failures | B: Automatic retry and persistent-error reporting |
| 29 | Ingestion observability | B: Stage progress, timestamps and errors |
| 30 | AI explanation changes | A first: Manual regen; C automatic/versioned later |
| 31 | Checklist after regen | B: Preserve tasks; review new suggestions separately |
| 32 | Review progress | B: Centralized admin dashboard |
| 33 | Public review visibility | B: Verification/publication status only |
| 34 | Search | B first: Keyword + filters; C natural-language later |
| 35 | Landing page | C: Combined summary, feed and searchable list |
| 36 | Time perspectives | C: Performance-year comparison + publication timeline |
| 37 | Historical year UI | B: Flexible year selector, initially 2025/2026 |
| 38 | Source discovery | B: Admin-managed official CMS source registry |
| 39 | File formats | B: PDFs + CMS webpages; structured files later if useful |
| 40 | Comparison engine | C: Deterministic field comparison + AI semantic analysis |
| 41 | Confidence/uncertainty | B: Evidence-based explanation, no uncalibrated score |
| 42 | Technical impact depth | B: Detailed analytics guidance, no generated SQL |
| 43 | Role customization | B: Analyst and Quality Manager views |
| 44 | Role interaction | A: Toggle on each measure page |
| 45 | AI explanation approval | B: Edit before approving both views together |
| 46 | Published explanation revisions | B: Privately preserve prior versions |
| 47 | Checklist organization | C: Shared list filtered by role |
| 48 | Review completion | C: Checklist resolved plus final admin sign-off |
| 49 | Completed reviews | B: Allow reopening with audit history |
| 50 | New specs after completion | B: Auto status Needs Re-review |
| 51 | Freshness | B: Last verified, last source check, new revision indicator |
| 52 | Data coverage | B: Complete 2025–2026 APP Plus set, including unchanged |
| 53 | Auth | A: Single admin login |
| 54 | Deployment | Develop locally with Docker (C), then host publicly via low-cost managed (A) or VM (B); final provider TBD |
| 55 | Release model | C: Phased MVP with incremental feature releases |

## 12. Immediate next actions

1. Convert this plan into `product-spec.md` with explicit acceptance criteria and public/admin user journeys.
2. Validate the complete APP Plus measure inventory for 2025 and 2026 against current official CMS specifications; identify actual sources and their document formats.
3. Design the normalized schema and source provenance model **before** automating extraction.
4. Create low-fidelity wireframes for homepage, dedicated measure page, document verification workspace, and admin review dashboard.
5. Set up repository and `AGENTS.md`; use Codex for implementation, local tests, and incremental diffs.
6. Build M1 first with verified seed records, then M2, M3, and M4.
7. Keep future ideas out of the MVP unless they fix a validated user problem.

**Product principle:** Architecture follows a real healthcare analytics workflow. The Zoomcamp rubric guides engineering evidence, not gratuitous product features.
