# CMS Quality Intelligence — Product Requirements Document

**Version:** 1.0  
**Date:** October 15, 2026  
**Status:** Scoped; implementation not started  
**Related documents:** [`plan.md`](plan.md) (55 decisions and implementation approach), [`tasks.md`](tasks.md) (independently assignable delivery backlog)  
**Audience:** Product owner, implementers, QA reviewers, and AI development assistants.

## 1. Product summary

CMS Quality Intelligence is an evidence-grounded web application for tracking changes to Centers for Medicare & Medicaid Services (CMS) quality-measure requirements. It helps **Healthcare Data Analysts** and **ACO Quality & Performance Teams** answer: *What changed between performance years, what official evidence establishes the change, what may need to change in analytics or operations, and what has been reviewed?*

The **primary workflow** is measure change tracking. A **secondary workflow** is exploring the underlying measure specifications. Initial scope is **Medicare Shared Savings Program (MSSP) / APP Plus** for **performance years 2025 and 2026**, including unchanged measures and the complete applicable year-specific measure sets, subject to verification against authoritative CMS sources.

The product is **not** a regulatory decision maker, an EHR integration, a patient-level analytics platform, a production SQL generator, or a tool covering every CMS program. No patient-level data or PHI should be collected.

## 2. Goals and success criteria

### Product goals

1. Make verified changes to MSSP / APP Plus measure membership and specifications discoverable.
2. Link every published factual change to official CMS source evidence and preserve document revision provenance.
3. Offer useful **plain-language and role-specific** AI explanations without presenting speculation as CMS policy.
4. Convert potential impacts into editable, trackable internal tasks, with review history and sign-off.
5. Keep the system maintainable and demonstrable as an AI Dev Tools Zoomcamp portfolio project without introducing unrelated modules.

### Release-level acceptance criteria

- All applicable APP Plus measures for **both 2025 and 2026** are accounted for, including unchanged entries. A source-backed coverage checklist demonstrates that completeness; incomplete coverage cannot be described as complete.
- Public visitors can search, filter, compare years, view verified excerpts and approved explanations, navigate between measures, and export permitted structured data.
- Deterministic comparison distinguishes **added / removed / modified / unchanged** from **missing / unresolved**; AI may explain semantic significance but cannot turn unsupported evidence into verified facts.
- Admin can add official source URLs, run incremental PDF/HTML ingestion, inspect failed or ambiguous records, correct and approve data, review and publish explanations, and track review tasks.
- Public endpoints do not expose draft extractions, internal tasks, audit notes, private prior explanation versions, or administrative controls.
- A testable end-to-end path exists from source ingestion through publication and subsequent review; the app runs locally via Docker Compose and has a publicly accessible deployment.

These are target criteria, **not claims that the product currently satisfies them**.

## 3. Users and permissions

| User | Main needs | Allowed actions |
| --- | --- | --- |
| Public Data Analyst | Find specification changes and understand possible data/SQL/dashboard implications | Browse approved records, compare years, toggle analyst explanation, view evidence and freshness, export structured data |
| Public ACO Quality/Performance User | Understand reporting and operational implications | Browse approved records, compare years, toggle quality-manager explanation, view evidence and freshness, export structured data |
| Single authenticated Admin | Maintain trustworthy data and coordinate follow-up | All public actions plus source management, ingestion, verification, explanation editing/approval, checklist review, sign-off, and internal history |

The MVP has **one admin login**. Visitors require no login. Authentication must be secure, with server-side authorization checks on all protected operations; no hardcoded credentials. Public and internal representations must be separated at API level, not hidden only in UI.

## 4. Information architecture and UX

### 4.1 Combined homepage

- Summary counts of **added, removed, modified, unchanged** measure statuses for the selected performance-year pair.
- **What's New** feed of recently approved/published changes with timestamps and direct measure links.
- Searchable measure list; search by measure ID, name, and description.
- Advanced filters: performance year(s), change type, affected specification field (numerator, denominator, exclusions, eligibility, calculation logic), and publicly permissible verification status.
- Flexible **from year / to year** selectors (only 2025 and 2026 available initially).
- Publication timeline showing when CMS announced or revised source documents, distinct from performance years.
- No numerical impact-priority score in MVP.

### 4.2 Dedicated measure page

Each measure has a stable, shareable URL. **Previous / Next** moves through the *current filtered result set* and maintains search and filter context. Tabs:

1. **Overview:** measure identity, description, annual applicability, verified normalized specifications (including numerator/denominator/exclusions/eligibility/calculation definitions where available), citations, and freshness.
2. **Changes:** side-by-side specifications for the two selected years, highlighted field-level differences and meaningful-vs-wording-only findings, CMS excerpts and links; explicit missing/unresolved states.
3. **AI Impact & Tasks:** public sees approved explanation for chosen role; admin can also see/manage internal suggestions and tasks.
4. **History:** public sees source/publication timeline and limited verification metadata; admin sees full review activity timeline.

A page-level toggle switches between **Data Analyst** and **ACO Quality Manager** explanation views. Both are generated/stored ahead of time; switching does not initiate another model call.

### 4.3 Admin workspaces

- **Source & Document Management:** registered URLs, document metadata/preview, extracted text, revision history, stage progress, errors and manual reprocessing.
- **Verification Queue:** AI-extracted candidate records and diffs next to official excerpts, editable corrected fields, unresolved flags, and per-item approve/reject controls.
- **Explanation Review:** paired role-specific drafts, source evidence, edit and joint approval.
- **Centralized Review Dashboard:** all measures, review statuses, accepted task completion, outstanding tasks and links into each measure.

## 5. Functional requirements

The identifiers below define stable requirements; backlog tasks may implement a requirement in multiple sessions.

### FR-01 Measure coverage and browsing

- Store stable measure identity separately from year-specific MSSP/APP Plus program membership and versioned specifications.
- Ingest/verify **complete 2025 and 2026 applicable APP Plus sets** and show unchanged measures.
- Provide keyword search, structured filters, year selectors, stable measure links and filtered Previous/Next navigation.
- A record absent due to extraction failure must not be classified as a program removal.

**Acceptance:** A seeded verified fixture spanning both years can be searched and filtered; unchanged measures appear; direct URLs load; navigation preserves filters; missing fields are visibly unknown rather than removed.

### FR-02 Version comparison

- Deterministically compare normalized fields for measure addition/removal, numerator, denominator, exclusions, eligibility and calculation definitions.
- Invoke a separate AI semantic classification step when useful to distinguish a substantive rule/specification difference from editorial rewrites.
- Associate each proposed finding with source IDs, excerpts, retrieval/publication metadata and verification state.
- Present side-by-side year values and field highlights, including explicit uncertainty/missing-data representation.

**Acceptance:** Tests cover added, removed, unchanged, modified, wording-only, missing-field and conflicting-source cases; no unapproved AI finding is published as confirmed.

### FR-03 Evidence and freshness

- Each published factual field/change has official CMS document title, URL, relevant excerpt and stable source-revision reference.
- Distinguish **performance year**, **CMS publication date**, **effective/applicability date**, **retrieval time**, **last source check** and **admin verification date**.
- Show public freshness indicators (last verified; last source check; newer revision detected) without asserting that “checked” equals “current”.
- Preserve previous revisions, not overwrite them.

**Acceptance:** Users can follow source links from a change; admin can identify the exact revision used; updated source creates a new revision and flags dependent analyses appropriately.

### FR-04 AI explanations and impacts

- Following admin verification of a change, generate a structured explanation pair: (1) plain-English account of **what changed** and (2) **why it matters**, tailored respectively to Data Analyst and ACO Quality Manager.
- Analyst guidance may discuss data mapping, SQL calculation *considerations*, numerator/denominator interpretation, dashboard review, and validation. It must **not** output production-ready SQL as authoritative reporting logic.
- Quality-manager guidance may discuss reporting workflows, data capture, coordination and process implications.
- Cite verified excerpts; label hypothetical organizational impact as possible rather than established fact. Decline or flag claims where evidence is insufficient. No uncalibrated numeric/High-Medium-Low confidence indicators in MVP.
- Admin may edit both drafts and **approve them together**. Public sees latest approved pair only. Earlier approved/draft versions and timestamps remain privately accessible.
- Source changes mark dependent explanations **outdated**. Admin regenerates manually in MVP; approval required before updated output replaces public version.

**Acceptance:** Structured schema validation and evidence-ID validation reject unsupported references; public never sees unapproved text; changing roles does not call model; outdated/previous versions remain auditable.

### FR-05 AI-assisted clarification

- For uncertain extracted fields, AI may consult **additional official CMS sources** and propose a resolution with excerpts and provenance.
- Only admin verification can convert proposed facts to verified facts.
- Allow **partial publication** of verified fields; withhold unresolved fields and prevent dependent explanations from implying certainty.

**Acceptance:** Ambiguous evidence yields a reviewable proposal or unresolved state, not silent acceptance; public fields are never labeled verified merely because AI suggested them.

### FR-06 Impact checklist

- AI proposes action items relevant to changed specifications; admin may accept, edit, add, complete or mark not applicable, with notes.
- Maintain **one shared checklist** with role tags and **All / Data Analyst / ACO Quality Manager** filters.
- Preserve accepted tasks, status, comments and completion on explanation regeneration; put new suggested tasks in a separate pending area until admin accepts them.
- Display per-measure progress and a centralized internal Review Dashboard.

**Acceptance:** Checklist edits persist; filters do not duplicate tasks; regeneration does not overwrite accepted/completed work; only internal admin APIs expose tasks.

### FR-07 Review and audit history

- Track review statuses, task edits, notes, status transitions, final sign-offs and reopen events in an **append-only activity timeline**.
- Sign-off requires **all accepted tasks resolved as completed or not applicable**, followed by explicit admin confirmation.
- Admin may reopen a completed review; prior sign-offs/events remain intact.
- Relevant newer CMS specifications set the review to **Needs Re-review**, preserving previous sign-off and task history.
- Public sees verification/publication status only, not internal notes or activity.

**Acceptance:** Incomplete accepted tasks block sign-off; reopening and newer-source transitions are logged; old sign-off can be retrieved; protected history is excluded from public responses.

### FR-08 Admin source registry and document management

- Start with a curated set of **official CMS** MSSP/APP Plus pages and specification documents; admins can add/remove source URLs subject to official-domain/safe-fetch checks.
- Support **PDF** and **HTML** in the MVP. Structured CSV/XLSX and autonomous discovery are deferred.
- Show source metadata, document preview or extracted content, progress stages (Downloading → Extracting → Comparing → Awaiting Verification), timestamps and persistent errors.

**Acceptance:** Adding a supported official URL is validated; admin can inspect ingestion state and extraction evidence; unauthorized or unsafe URLs cannot be fetched.

### FR-09 Incremental ingestion and error handling

- MVP ingestion is **admin-triggered** through Check for Updates; process new/changed content and skip unchanged versions by robust hash/version checks.
- Admin can **force reprocess** a document after parser changes or corrections without erasing prior verified revisions.
- Retry transient failures automatically with bounded attempts, report persistent failures to admin. No step-level resumable engine or detailed token/cost dashboard required.
- If source changes during an active review, flag it outdated and require re-verification before publication.
- Individual draft changes are editable and approvable; bulk approval is deferred.

**Acceptance:** A no-change ingestion run makes no duplicate versions; force-reprocessing works; transient and persistent failure states are distinguishable; stale reviews cannot publish without re-verification.

### FR-10 Structured export

- Public users can export permitted **CSV and Excel** datasets from the current approved filtered view, including available measure/change metadata and citation links.
- Export must not contain drafts, internal notes, incomplete private fields, credentials, or review tasks.
- Formatted PDF impact reports are not in MVP.

**Acceptance:** Export rows match selected filters and only approved public fields; test with CSV and XLSX readers; verify sensitive fields are absent.

## 6. Core workflows and state transitions

### W1 Admin publication

Sign in → Manage official sources → Check for Updates → Skip unchanged / download changed → Extract → Compare → Resolve ambiguity via official evidence → Edit/verify change candidates → Approve verified fields → Generate AI pair → Edit/approve pair → Publish → Public home/measure pages update.

**Publication invariant:** A published claim depends on approved versioned evidence and an applicable admin verification. Partial publication is allowed only for independently verified fields.

### W2 Public research

Homepage (summary + What's New + search) → Select years and filters → Open measure → Compare fields/excerpts → Toggle role view → Navigate Previous/Next → Export approved data.

### W3 Review and follow-up

Admin Review Dashboard → Select measure → Accept/edit tasks → Update tasks/notes → Resolve every accepted item → Final sign-off → Optional reopen with audit history. If newer source affects the measure, transition to Needs Re-review.

### State sketches

- **Source revision:** discovered → processing → extraction-ready / failed; candidate data then awaiting verification → verified / rejected / unresolved.
- **AI explanation pair:** generation pending → draft → approved/published → outdated (after source change) → manually regenerated draft → approved/published.
- **Measure review:** pending → in review → completed (after sign-off) ↔ reopened; source revision can trigger needs re-review.

State names may change during API design, but guards and transitions above are required. Published revisions must remain traceable even after later updates.

## 7. Data model and external contracts

Suggested entities (not a prematurely fixed SQL schema):

| Entity | Minimum responsibility |
| --- | --- |
| `sources` / `source_revisions` | Official URL, title, MIME type, dates, content hash, retrieved document/text, provenance |
| `measures` / `measure_versions` | Stable identity, program-year membership, normalized specs, field-level evidence and verification |
| `change_candidates` / `approved_changes` | Deterministic diffs, AI semantic notes, uncertainty, approval, source revision references |
| `explanations` | Versioned pair of role-specific content, citations, draft/approval/outdated state, prompt/model metadata |
| `reviews` / `review_items` / `review_events` | Sign-off state, role-tagged tasks, activity timeline, preserved historical actions |
| `ingestion_runs` / `ingestion_events` | Source checks, step progress, retries and errors |

**API contract:** publish an `openapi.yaml` used to guide backend and frontend. Expected API groups: public measures/search, measure versions and changes, approved explanations, public exports/freshness, admin authentication, admin source/ingestion management, verification/approval, explanation approval, checklist/review status and history. Exact endpoint names and pagination strategy can be finalized in the API-contract task.

**Security:** Server-side authorization, secret management, safe URL ingestion (HTTPS/allowlisted CMS domains, prevent SSRF), bounded document sizes, HTML/PDF parsing isolation where practical, output encoding, rate limiting for costly operations, no PHI. Public outputs must use explicit allowlisted response fields.

## 8. AI behavior and evaluation

- AI assists with **extraction**, **semantic comparison**, **additional official-source clarification**, **role-specific explanation**, and **suggested tasks**; it does not make autonomous approval decisions.
- Compare structured fields deterministically before requesting semantic interpretation.
- Use typed/structured model outputs, stable evidence identifiers, schema validation and source-reference checks. Store prompt/model version metadata.
- Do not present uncalibrated confidence scores or generated production SQL.
- Prepare a labeled fixture set covering exact changes, wording-only edits, source conflicts, unsupported assertions, missing fields, citations and regeneration states.
- Target: zero unsupported claims in the evaluated publication path; all published citations resolve to permitted official evidence. Report actual evaluation outcomes rather than assuming targets are met.

## 9. Release plan and dependency strategy

| Milestone | Outcome | Scope |
| --- | --- | --- |
| **M1 — Measure Explorer** | First useful read-only slice | Clean repo and passing test; verified seed records for both years; schema and API; combined homepage; search/filters; dedicated measure pages |
| **M2 — Change Intelligence** | Core value validated | Deterministic + semantic comparison; detailed side-by-side fields; source citations; publication timeline; approved role-specific AI explanations |
| **M3 — Automated Ingestion & Verification** | Maintainable source workflow | Admin-managed source list; PDF/HTML ingestion; incremental run and forced retry; queue/edit/verify; uncertain-source clarification; versioning and stale checks |
| **M4 — Review Workflow & Release** | Complete agreed MVP | Shared task checklist; centralized review dashboard; audit/sign-off/reopen/re-review; CSV/XLSX export; end-to-end tests; deployment and Zoomcamp evidence |

Each milestone should be independently demoable. M1/M2 may use **verified seeded CMS data**, not a fake assertion that automated ingestion exists. M3 must preserve the same public data contract. Build first task in `tasks.md` before other implementation: **Initialize an empty project with a passing test**.

### Required engineering evidence (Zoomcamp draft rubric)

Architecture docs, reproducible frontend/backend runs, OpenAPI contract, database documentation, Docker Compose, unit/integration tests, cloud demo, CI/CD, AI-assisted development notes and manual reviews, security scan findings, operational checks, and a documented **development-only** agent extension pack. The extension pack should not force production microservices or autonomous agents into the application. Recheck the rubric before final submission because 2026 criteria are draft.

## 10. Explicit post-MVP scope

- Scheduled CMS source checks, using the same ingestion pipeline.
- Batch verification/approval and broader automated source discovery.
- Calibrated impact prioritization (High/Medium/Low), natural-language measure search.
- PDF impact reports; richer embedded evidence viewer.
- CSV/XLSX **ingestion** if official structured sources justify it (separate from MVP CSV/XLSX **export**).
- Multi-user accounts, separate reviewers and team collaboration.
- More performance years and additional CMS programs.
- Automated explanation regeneration with version history/approval, richer monitoring, and step-level ingestion recovery.
- Illustrative SQL/pseudocode if rigorously validated and clearly non-authoritative.

## 11. Nonfunctional requirements and safeguards

- **Trustworthiness:** verified evidence and source revisions must be navigable; source check timestamps cannot imply regulatory currency.
- **Data integrity:** never destructively overwrite source revisions, approved explanations, task completion, or signed review history.
- **Reproducibility:** first-time developer can run a smoke test and local system from documented instructions; environment variables use templates, not committed secrets.
- **Security/privacy:** public read-only browsing; single admin authentication; no PHI; restrictive public API serialization and CMS-domain safe-fetch policy.
- **Operational visibility:** ingestion stages, timestamps, retries and actionable errors visible to admin; no advanced metrics platform required.
- **Accessibility/usability:** keyboard-accessible filters and tabs, legible change highlights beyond color alone, responsive comparison where feasible.
- **Performance/cost:** cache pre-approved AI explanations; toggling roles and visiting public pages does not trigger redundant LLM calls.

## 12. Decisions and unresolved implementation details

**Locked through 55 scoping questions:** user groups, primary change-first workflow, 2025–2026 APP Plus coverage, five core features, hybrid comparison, CMS evidence, admin-verification gates, individual measure pages, advanced search, two role views, public/admin split, incremental manual ingestion, editable checklist and review history, CSV/XLSX exports, and phased releases.

**Implementation-level decisions still open (do not treat as new features):** exact CMS document URLs and authoritative measure inventory per performance year; final normalized schema/OpenAPI endpoint naming; secure single-admin auth provider; managed hosting versus single cloud server; precise ingestion retry limits, pagination and UI designs; validated PDF/HTML extraction tooling.

**Source-of-truth order:** (1) authoritative CMS documentation for CMS facts, (2) this `product-spec.md` for intended product behavior, (3) `plan.md` for full decision context, (4) `tasks.md` for execution sequence. When a backlog task conflicts with this PRD, reconcile before implementation.

---

**Product principle:** Build useful, verifiable healthcare quality change intelligence first. Meet AI Dev Tools Zoomcamp expectations with disciplined engineering and a small development-only extension pack, not unnecessary production components.
