# CMS Quality Intelligence — Implementation Backlog

## Checkpoint status (October 21, 2026)

- Tasks 1, 2, 5–12: implemented and verified through Checkpoints A, B, C1,
  and C2.1–C2.5. The official PY2025–PY2026 roster has two-source evidence,
  exact locators, and hashed source revisions.
- Tasks 14–16, 18, 19, and 21: C1 implementation is present against synthetic
  contract fixtures, including public/private isolation and explicit
  unavailable/unresolved states.
- Task 13 is partially complete: a validated, draft seed artifact now
  contains all eight identities and 14 verified program-year memberships. The
  collection-variant schema is implemented, and the guarded PostgreSQL import
  stages 32 private variants and 352 field candidates without publishing them.
  A guarded, idempotent review importer now preserves future decisions in an
  append-only audit trail. Task 49 now supports separately authorized publication
  of an individually approved, excerpt-backed field, but the real queue still has
  no expert decisions and therefore no production field has been approved for
  release. Tasks 17, 20, and 22 also remain open, including
  dynamic year options, server-paginated Previous/Next, and full end-to-end M1
  validation.
- Task 38 is partially complete: environment-managed single-admin credentials,
  signed HttpOnly sessions, backend authorization, and authenticated read-only
  private-review endpoints are implemented and contract-tested. Task 57 also has
  a first read-only queue and per-measure evidence view. Review mutations,
  ingestion controls, publishing, status workflow, and the full centralized
  dashboard remain open.
- Tasks 23–37 and 39–47 remain unimplemented. Tasks 48–49 provide the manual
  review and safe partial-publication slice ahead of automated ingestion. The
  dashboard change ledger, What's New feed, comparison highlighting, and AI
  Impact content remain visibly fictional prototypes and are not production-backed.

This backlog implements the scoped 2025–2026 MSSP / APP Plus MVP in independent, one-session work items. Tasks are ordered for incremental delivery (M1–M4), but each description provides enough context for an assignee to begin without reading preceding tasks. Keep all official CMS facts source-backed, treat unverified extractions as drafts, and do not use patient-level data. **This document is planning only; no implementation code is included.**

## M1 — Foundation and Measure Explorer

## 1. Initialize an empty project with a passing test
Goal: Establish a clean repository whose initial automated test passes.
Description: Create an empty CMS Quality Intelligence project with minimal Python testing configuration, a placeholder smoke test, and instructions to run it locally. Verify the test command exits successfully in a fresh environment; do not implement application functionality yet.

## 2. Write the concise product specification
Goal: Define the product, users, workflows, and MVP boundaries in `product-spec.md`.
Description: Describe the change-first workflow for Healthcare Data Analysts and ACO Quality Teams, limiting coverage to 2025–2026 MSSP / APP Plus. Distinguish public browsing from admin review and list measurable acceptance criteria for Measure Explorer, comparisons, AI explanation, checklists, and history.

## 3. Document architecture and boundaries
Goal: Record a small, maintainable full-stack architecture.
Description: Write `docs/architecture.md` describing React/TypeScript, FastAPI/Pydantic, PostgreSQL, an OpenAI-backed analysis service, and Docker Compose. Explain why source-backed deterministic comparison is authoritative for field differences and why microservices, vector search, and autonomous production agents are excluded from MVP.

## 4. Create project-level AI development instructions
Goal: Make AI-assisted work predictable and reviewable.
Description: Add `AGENTS.md` specifying code structure, test expectations, small change sets, secrets handling, no-PHI policy, and the rule that CMS facts require source evidence and admin verification. Include expectations for documenting prompts, reviewing diffs, and validating AI-produced changes.

## 5. Establish the backend application skeleton
Goal: Run an empty FastAPI service with an automated health test.
Description: Set up a minimal `backend/` package with a `/health` endpoint, dependency manifest, and pytest configuration. Verify a request returns a successful response without needing PostgreSQL or an OpenAI key.

## 6. Establish the frontend application skeleton
Goal: Run a minimal React + TypeScript interface with a passing test.
Description: Create `frontend/` with a simple CMS Quality Intelligence landing shell and a frontend test runner. Verify the app builds and its basic render test passes without calling a backend API.

## 7. Define the first OpenAPI contract
Goal: Specify the read-only Measure Explorer interface before integration.
Description: Add `openapi.yaml` covering public measure search, measure details, available performance years, and year-specific specifications with typed examples. Include filtering and pagination parameters and document what missing or unverified fields look like in responses.

## 8. Design the relational schema and migrations
Goal: Model trustworthy, versioned CMS records and source provenance.
Description: Define PostgreSQL migrations for measures, measure versions, program/year participation, source documents, source revisions, and field-level evidence references. Separate performance year from publication/effective dates and ensure records can represent absent, unknown, and verified fields distinctly.

## 9. Set up local PostgreSQL with Docker Compose
Goal: Start the database reproducibly on a development machine.
Description: Configure a local PostgreSQL service with persistent volume, environment-based credentials, and a health check. Document start, stop, and migration commands without checking any passwords or private environment files into Git.

## 10. Inventory authoritative 2025 APP Plus sources
Goal: Establish the verified source-of-truth list for the 2025 measure set.
Description: Identify official CMS documents that define MSSP APP Plus membership and relevant measure specifications for performance year 2025. Record direct URLs, titles, publication/revision dates, applicable program/year, and any ambiguity in a source inventory file; do not guess missing measures.

## 11. Inventory authoritative 2026 APP Plus sources
Goal: Establish the verified source-of-truth list for the 2026 measure set.
Description: Identify official CMS documents that define MSSP APP Plus membership and relevant measure specifications for performance year 2026. Record direct URLs, titles, dates, and applicability, distinguishing finalized requirements from proposals and noting unresolved discrepancies.

## 12. Validate complete 2025–2026 measure membership
Goal: Produce an auditable roster of every APP Plus measure for both years.
Description: Reconcile the two official source inventories into measure IDs and year-specific membership, including unchanged and removed measures. Add a checklist or validation report showing how completeness was established and flag any unresolved source conflicts rather than silently filling gaps.

## 13. Prepare verified measure seed records
Goal: Load consistent normalized measure facts into the application.
Description: Create a structured seed dataset for the verified 2025 and 2026 APP Plus inventory with names, IDs, core specifications, year-specific applicability, and source links. Keep uncertain fields explicitly unresolved and ensure repeat seeding does not create duplicates.

## 14. Implement public measure-list API
Goal: Make verified measures searchable through FastAPI.
Description: Implement `GET /api/measures` with keyword matching for ID, name, and description plus program/year filters and pagination. Return only verified public fields and add tests for empty results, repeated requests, and unsupported filter values.

## 15. Implement measure detail and version API
Goal: Expose one measure's verified profile and available years.
Description: Add read-only API endpoints for a stable measure ID and its 2025/2026 specification records, including evidence metadata and unavailable-field states. Test that a measure absent from one year is represented as nonparticipation only when authoritative membership data supports it.

## 16. Build the shared frontend API client
Goal: Centralize typed frontend/backend communication.
Description: Create a reusable client layer for measure listing, detail, and year-version retrieval based on `openapi.yaml`. Include user-friendly handling for loading, network failures, and empty results, with mocked request tests.

## 17. Build the combined homepage layout
Goal: Give public visitors an entry point into CMS changes and measures.
Description: Implement a responsive homepage shell with locations for summary counts, What's New, year selection, and a searchable measure list. Use actual public API data where available and clearly label sections not yet populated rather than showing invented metrics.

## 18. Add keyword search and structured measure filters
Goal: Let visitors find measures without conversational search.
Description: Build search by measure ID/name/description and filters for performance year, membership/change status, and affected specification area when data is available. Keep filters in URL query parameters or equivalent navigable state, and test that clearing filters restores the full verified roster.

## 19. Build dedicated measure overview pages
Goal: Centralize one measure's specification and provenance.
Description: Create a shareable route for each measure with an Overview tab showing available years, definitions, numerator, denominator, exclusions, and source references. Show clear unavailable/unverified states without implying missing data means a CMS requirement was removed.

## 20. Add flexible year selection and Previous/Next navigation
Goal: Support efficient sequential review of filtered measures.
Description: Allow selecting two available performance years, initially 2025 and 2026, without hardcoding the comparison UI to those years. Add Previous/Next navigation on dedicated measure pages that retains the originating measure filters and list order.

## 21. Display verification and source-freshness metadata
Goal: Let visitors distinguish reviewed content from newly detected source updates.
Description: Show last verified date, last source check, and newer-source indicator on public measure pages when such data exists. Explain that a recent check is not proof the CMS specification itself is still current; test empty or unknown freshness states.

## 22. Validate the M1 public explorer workflow
Goal: Demonstrate a reliable, AI-free first release.
Description: Add a test covering seeded data through API retrieval to a rendered measure page, plus checks for source provenance and year selection. Document how a reviewer can run the test and manually inspect the complete 2025–2026 inventory.

## M2 — Change Intelligence

## 23. Define the change record schema and contract
Goal: Standardize change types and comparisons across backend and UI.
Description: Specify `added`, `removed`, `modified`, `unchanged`, `wording-only`, and `unknown` states with affected field and linked evidence references. Update schema/API contracts so missing values cannot be misclassified as policy removals.

## 24. Implement deterministic specification-field comparison
Goal: Identify exact differences in normalized measure specifications.
Description: Compare verified versions by program, measure ID, performance year, and fields including numerator, denominator, exclusions, eligibility, and calculation logic. Add fixtures for added, removed, unchanged, changed, null, and unknown fields and assert deterministic results.

## 25. Add evidence excerpts to change records
Goal: Connect each asserted difference to official CMS material.
Description: Store short source excerpts with document/version IDs, section or page locators when available, and official URLs for each comparison result. Test that a public change does not claim verified evidence when its source reference is absent or unresolved.

## 26. Define structured AI semantic-classification output
Goal: Limit AI to evaluating the meaning of detected text differences.
Description: Define a Pydantic schema for substantive-versus-wording-only assessment, evidence references, reasoning summary, and unresolved uncertainty. Require citations from supplied official excerpts and keep AI judgments separate from deterministic field differences.

## 27. Implement AI semantic classification for field diffs
Goal: Help analysts distinguish policy-relevant changes from rephrasing.
Description: Pass the deterministic difference and verified CMS excerpts to the model, validate its structured response, and record the model/prompt version. Fall back to `needs review` on parsing errors, unsupported citations, or conflicting evidence instead of auto-approving a conclusion.

## 28. Build semantic-change evaluation fixtures
Goal: Quantify whether classification respects evidence and uncertainty.
Description: Assemble a small labeled set with paraphrases, substantive edits, unchanged records, conflicting sources, and missing fields. Create a repeatable evaluation command and report actual accuracy and evidence-validation failures without inventing performance claims.

## 29. Implement public changes and comparison APIs
Goal: Serve verified year-over-year change results to the frontend.
Description: Define and implement endpoints for change listing and a measure's side-by-side comparison with changed-field annotations and excerpts. Return approved/public records only and test filtering by change type, field, and year pair.

## 30. Build the Change Overview dashboard
Goal: Summarize APP Plus changes before users drill down.
Description: Display counts of added, removed, modified, and unchanged measures along with a searchable change list. Link each item to its dedicated measure page and ensure counts are derived from verified data rather than mock labels.

## 31. Build side-by-side specification comparison
Goal: Show precise 2025-versus-2026 differences on measure pages.
Description: Implement a Changes tab with aligned fields, highlighted differences, wording-only labels, and explicit unknown states. Include source excerpts and official links without assuming both years have values for every field.

## 32. Build the What's New feed
Goal: Surface recently published, verified changes.
Description: Add a chronological feed of newly approved changes with CMS publication dates and internal approval dates clearly distinguished. Link each feed item to its measure page and exclude pending or rejected items.

## 33. Build the CMS publication timeline
Goal: Separate when CMS announced a change from the year it applies.
Description: Render a simple source publication/revision timeline using documented dates and links. Test that performance years, publication dates, and effective dates are not conflated in labels or sorting.

## 34. Define role-specific AI impact output contracts
Goal: Make AI explanations consistent for two user roles.
Description: Define structured sections for plain-language change summary, Data Analyst technical implications, ACO Quality Manager operational implications, citations, and uncertainty caveats. Exclude production SQL generation, severity scoring, and unsupported regulatory conclusions.

## 35. Implement grounded explanation generation
Goal: Produce two evidence-backed perspectives on an approved change.
Description: Generate and validate Data Analyst and ACO Quality Manager explanations using only approved change records and official source excerpts. Store the generated pair as an admin-reviewable draft rather than publishing it automatically without approval.

## 36. Evaluate AI impact explanations
Goal: Verify citations, scope, and practical usefulness before publication.
Description: Create representative test cases for calculation changes, additions/removals, wording-only edits, and insufficient evidence. Check schema validity, source-reference accuracy, unsupported claims, and role relevance, and record actual outcomes.

## 37. Display approved role-specific explanations
Goal: Let public users switch analytical perspectives without new model calls.
Description: Implement the per-measure Data Analyst / ACO Quality Manager toggle and render only an approved explanation pair. Test that switching uses stored content and that pending, rejected, or outdated explanations are not silently presented as newly verified.

## M3 — Automated Ingestion and Verification

## 38. Implement single-admin authentication and authorization
Goal: Protect all modification and verification endpoints.
Description: Configure one secure admin login using environment-managed credentials or a trusted auth provider, leaving public read endpoints unauthenticated. Test that unauthenticated visitors cannot trigger ingestion, edit CMS records, approve explanations, or view private reviews.

## 39. Build the admin-managed CMS source registry
Goal: Let an admin maintain the list of approved official source URLs.
Description: Implement create, list, update, and deactivate operations for CMS source entries, with validation of allowed official CMS domains and relevant metadata. Reject unsafe or nonofficial URLs and test protections against using the ingestion service to fetch arbitrary internal addresses.

## 40. Implement CMS HTML fetch and text extraction
Goal: Turn official CMS webpages into traceable text sources.
Description: Fetch a registered public CMS webpage, preserve retrieval metadata and content hash, and extract relevant readable text with section references where possible. Handle access failures and unexpected page formats without corrupting stored verified records.

## 41. Implement CMS PDF fetch and text extraction
Goal: Turn official CMS PDFs into traceable text sources.
Description: Download a registered CMS PDF, record content hash and source metadata, and extract text with page references when available. Route unreadable/scanned or malformed PDFs to an explicit error/manual-review state instead of fabricating content.

## 42. Persist source revisions and unchanged-file detection
Goal: Avoid repeated extraction for sources whose content has not changed.
Description: Store separate immutable source revisions using reliable content hashes and retrieval timestamps. On repeat admin checks, skip identical content but allow a forced reprocessing run without deleting historical revisions.

## 43. Implement normalized extraction candidates
Goal: Convert CMS document text into reviewable measure fields.
Description: Use structured extraction to propose measure IDs, year applicability, numerator/denominator, exclusions, and other required fields with exact evidence pointers. Validate against typed schemas and retain incomplete/uncertain values as candidates rather than verified records.

## 44. Implement optional AI-assisted source clarification
Goal: Help admins resolve ambiguous extracted measure fields.
Description: For unresolved candidates, retrieve corroborating excerpts from additional approved official CMS sources and request a bounded AI clarification proposal. Store proposed evidence and disagreements for human review; do not permit the proposal to approve or publish itself.

## 45. Implement the admin-triggered ingestion run
Goal: Process newly detected CMS sources through a defined pipeline.
Description: Add a protected Check for Updates action that creates a run and moves each document through Downloading, Extracting, Comparing, and Awaiting Verification. Keep processing bounded for a solo-admin MVP and persist run outcomes so an interrupted request cannot silently imply completion.

## 46. Add ingestion progress and error states to admin UI
Goal: Explain what each document is doing and why it failed.
Description: Display the current stage, timestamps, completion state, and persistent errors for every ingestion run in a document workspace. Test that users can distinguish a still-running job from a failed or completed one.

## 47. Add bounded retries and force-reprocess controls
Goal: Recover transient source failures without unnecessary work.
Description: Retry temporary network or processing errors a limited number of times and report failures requiring admin attention. Provide a protected force-reprocess control for an existing source revision while preserving its previous verified output and review history.

## 48. Build the editable change verification queue
Goal: Let the admin correct AI-extracted records before publication.
Description: Present one candidate at a time with old/new values, official excerpts, uncertainty flags, and Approve/Reject/Edit actions. Record edits and reviewer identity/timestamps; do not add bulk approval in MVP.

Implementation status (complete for MVP, 2026-10-22): The protected admin workspace now
presents individual source-backed field candidates with their official source,
separately stored official excerpt when one was captured, evidence locator,
extraction state, and current decision. Reviewers can approve an edited value,
request revision, or mark a field not applicable. Each action
records authenticated reviewer identity and time in append-only history without
publishing. The dialog now pairs the same field and collection type across
PY2025 and PY2026, distinguishes exact wording matches, differences, and missing
counterparts without inferring policy meaning, and translates extraction codes
into explicit SME, manual-review, or applicability signals. Source excerpts are
persisted separately from normalized candidate values; candidates without a
captured excerpt explicitly require manual use of the exact locator and source
link. `needs_revision` is the MVP rejection path, and no bulk approval exists.

## 49. Implement verified-field partial publication rules
Goal: Publish trustworthy information without hiding the whole measure.
Description: Permit approval of individual evidenced fields while unresolved fields remain withheld and flagged internally. Test that public API responses and generated AI explanations never represent unresolved or missing values as confirmed CMS requirements.

Implementation status (complete for MVP, 2026-10-26): Approval and publication
are separate authenticated actions. The publication transaction accepts only a
reviewer-approved candidate with a frozen verified source, literal excerpt,
locator, verified program-year membership, a supported public-field mapping, and
no newer-source flag. It materializes one `SpecificationField` and
`EvidenceReference`, records publisher/time, and leaves every sibling candidate
private. Repeated publication is idempotent; published reviews are locked against
in-place changes. Current safe mappings cover definition, numerator, denominator,
and exclusions. Other candidate categories remain private until the public
contract has a semantically exact mapping. A publication-safe explanation-context
builder excludes drafts, null/unresolved values, and fields without published
evidence; no AI explanation generation is implemented yet.

## 50. Mark reviews and explanations stale on source changes
Goal: Prevent older verification decisions from appearing current after revisions.
Description: When a new relevant CMS source revision is detected, flag affected pending reviews as outdated and require re-verification before publication. Change completed reviews to Needs Re-review when applicable, preserving prior approvals, sign-offs, and source history.

## 51. Build the AI explanation edit-and-approve workflow
Goal: Publish only a jointly approved pair of role-specific explanations.
Description: Let the admin edit Data Analyst and ACO Quality Manager explanation drafts and approve or reject both together. Preserve prior approved versions privately and ensure the public app always shows the latest valid approved pair.

## 52. Implement manual explanation regeneration
Goal: Refresh stale explanations without overwriting human work.
Description: Flag explanations outdated after approved source/field edits and expose a protected Regenerate action. Create a new draft instead of overwriting the previous version, leaving existing accepted checklist tasks intact and showing new suggestions separately.

## 53. Test ingestion-to-publication integration
Goal: Verify the complete official-source change pipeline.
Description: Use controlled CMS-like PDF/HTML fixtures to test detection, extraction, clarification, verification, approval, and public visibility end to end. Include unchanged-source, uncertain-field, retry, unauthorized-admin-action, and newer-source-during-review scenarios.

## M4 — Review Workflow, Export, Hardening, and Delivery

## 54. Define checklist and review audit schemas
Goal: Model editable tasks and durable review history.
Description: Add persistence for role-tagged checklist items, accepted suggestions, task states, reviews, sign-offs, and append-only review events. Design changes so regeneration and reopening cannot erase previous completion or reviewer actions.

## 55. Generate role-tagged impact task proposals
Goal: Suggest actionable technical and operational follow-up tasks.
Description: Generate structured suggestions from approved CMS changes with Data Analyst and/or ACO Quality Manager tags and supporting evidence. Keep proposed tasks separate from accepted checklist items so an admin controls what enters the active workflow.

## 56. Build the interactive impact checklist
Goal: Let the admin manage one shared checklist per review.
Description: Support accepting suggested items, adding/editing tasks, marking completed or not applicable, and filtering by All / Data Analyst / ACO Quality Manager. Persist edits and events while retaining previous tasks when AI suggestions are regenerated.

## 57. Build the centralized admin review dashboard
Goal: Make outstanding measure reviews and tasks visible in one place.
Description: Show per-measure review status, remaining accepted tasks, checklist progress, and links to the corresponding measure's admin view. Include filters for Pending, In Review, Completed, and Needs Re-review and keep internal notes private.

## 58. Implement final sign-off and review reopening
Goal: Distinguish task completion from formal review completion.
Description: Require all accepted checklist items to be completed or marked not applicable before the admin can sign off. Allow later reopening and re-sign-off while appending timestamped events and preserving older sign-offs.

## 59. Build the private review activity timeline
Goal: Preserve an auditable record of what was reviewed and changed.
Description: Render append-only task edits, notes, approval changes, sign-offs, and reopen events on each admin measure page. Verify public visitors only see the permitted verification status and last-reviewed information, not internal timeline content.

## 60. Implement CSV export of verified change data
Goal: Let analysts download structured, source-backed comparisons.
Description: Export the currently filtered public measure/change dataset with stable IDs, comparison years, change types, affected fields, and evidence URLs. Exclude unverified fields and private review notes, and test CSV escaping and exported row counts.

## 61. Implement Excel export of verified change data
Goal: Provide spreadsheet-friendly output for quality teams.
Description: Generate an XLSX workbook containing public measure/change data and a clear data dictionary or source sheet. Use the same verified/public selection rules as CSV and verify it opens with expected columns and no formula injection from source text.

## 62. Add API contract and frontend behavior tests
Goal: Catch incompatibilities between React and FastAPI.
Description: Validate API responses against `openapi.yaml` and test homepage filters, measure navigation, comparison, role toggles, and failure/empty states using mocked backend responses. Make the combined test command reproducible locally.

## 63. Add security and data-handling checks
Goal: Prevent exposure of credentials or internal review data.
Description: Test backend authorization, official-source URL restrictions, safe document retrieval, output encoding, and private/public record separation; run a dependency and secret scan. Document findings and fixes in `security/` with a no-PHI and AI tool/data policy.

## 64. Compose the full local application
Goal: Bring frontend, backend, and database up with one command.
Description: Extend Docker Compose so a new contributor can start React, FastAPI, and PostgreSQL with documented environment variables and migrations. Add a local smoke check covering frontend availability, API health, and database connectivity.

## 65. Build continuous integration checks
Goal: Reject changes that break the application or its safety boundaries.
Description: Configure GitHub Actions to run backend unit/integration tests, frontend tests/build, API contract checks, and baseline security scans on pull requests. Keep cloud secrets out of PR workflows and document how to reproduce failures locally.

## 66. Deploy and verify the public demo
Goal: Publish a reliable portfolio-accessible application.
Description: Select low-cost managed hosting or a single cloud VM based on actual operating costs, then deploy public React/FastAPI services and a persistent database. Verify HTTPS, public read access, protected admin operations, source links, and database persistence after restart; record the live URL and deployment steps.

## 67. Document the AI-assisted development workflow
Goal: Show how AI tools were used and checked for the Zoomcamp rubric.
Description: Record representative planning prompts, task delegation, code-review notes, human corrections, test evidence, and decisions in `docs/ai-development.md`. Make it clear which parts were AI-assisted and how source accuracy and implementation quality were independently verified.

## 68. Add a development-only CMS verification specialist
Goal: Provide an agent instruction set that supports source review without altering production behavior.
Description: Add a narrowly scoped specialist or custom-agent definition for checking a proposed CMS change against the local approved evidence base. Specify boundaries, required citations, and escalation when the evidence is insufficient; keep it out of the end-user runtime.

## 69. Add a minimal read-only CMS evidence MCP capability
Goal: Let a development agent query curated evidence safely.
Description: Create a small MCP tool interface for searching locally stored source excerpts by measure and year, returning stable evidence references. Restrict access to read-only curated data, test denial of mutations, and document setup and allowed inputs in `docs/agent-extension-pack.md`.

## 70. Add a reusable verification workflow and guardrail
Goal: Make agent-assisted measure review reproducible and controlled.
Description: Document a reusable validation workflow and add a hook or guardrail that blocks unapproved changes to verified source records. Test one allowed read and one blocked write and record permissions and human-approval expectations in `docs/permissions.md`.

## 71. Capture PR audit and operational diagnosis evidence
Goal: Satisfy course security and DevOps evidence with real output.
Description: Run an open-source PR/code audit, deterministic security checks, and an operational health or failure-diagnosis check against this repository. Save actual tool versions, commands, findings, triage decisions, and remediation notes under `security/` and `ops/` rather than fabricating clean reports.

## 72. Create a final reproducibility and submission guide
Goal: Enable a new reviewer to run and assess the finished MVP.
Description: Update `README.md` with problem statement, architecture, setup, migrations, test commands, environment-variable template, deployment/demo URL, and known limitations. Add a concise rubric-evidence index and verify the instructions from a clean checkout before calling the release complete.

## Post-MVP — Explicitly Deferred (Do Not Block Initial Release)

## 73. Add scheduled CMS source checks
Goal: Run the existing admin-triggered ingestion pipeline on a recurring schedule.
Description: Add a configurable schedule that invokes the same verified source registry, incremental hash checks, and error reporting used by manual ingestion. Make sure scheduled runs cannot bypass the established admin approval and publication requirements.

## 74. Add batch extraction verification
Goal: Speed review of multiple low-risk candidates without sacrificing traceability.
Description: Let admins select multiple extraction candidates and approve or reject them after seeing aggregate evidence and unresolved-field warnings. Preserve individual audit events and require explicit confirmation for the batch.

## 75. Add calibrated AI impact prioritization
Goal: Rank changes by meaningful reporting impact instead of subjective labels.
Description: Define a defensible High/Medium/Low rubric with labeled examples and evaluation before showing severity to users. Keep scores distinct from extraction confidence and allow reviewers to override ratings with explanations.

## 76. Add natural-language measure search
Goal: Support conversational discovery of verified CMS measures and changes.
Description: Translate user questions into constrained search over approved measure records and official excerpts. Return grounded results with links, and test that unsupported questions do not produce invented measure facts.

## 77. Add formatted PDF impact reports
Goal: Produce shareable, presentation-ready summaries of verified changes.
Description: Generate a PDF containing selected approved comparisons, role-specific explanations, sources, and appropriately scoped review status. Exclude private notes unless a privileged export is explicitly requested and authorized.

## 78. Add multi-user review roles and collaboration
Goal: Support multiple named reviewers and accountable approvals.
Description: Introduce named accounts, reviewer/admin permissions, and per-user audit attribution while retaining current single-admin flows. Require a separate permissions and data-migration review before enabling shared editing.

## 79. Expand performance years and CMS programs
Goal: Extend the versioned comparison engine beyond the original APP Plus scope.
Description: Add additional performance-year inventories or a new CMS quality program only after validating authoritative source material and program-specific identifiers. Reuse the existing comparisons and interface without confusing measures shared across programs.

## 80. Add richer ingestion and explanation automation
Goal: Improve operational coverage after the core pipeline is dependable.
Description: Evaluate automatic source discovery, CSV/XLSX source ingestion, batch processing, fine-grained resumability, AI token/cost telemetry, and automatic explanation regeneration as separate optional extensions. Implement only features supported by observed ingestion failures or user needs, preserving approval and audit controls.
