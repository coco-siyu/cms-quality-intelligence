# CMS measure field review guide

## Purpose

The field review crosswalk turns the frozen CMS source snapshot into a structured review queue. It does not certify clinical correctness and does not publish data.

The project owner can review provenance, completeness, and workflow controls without being a healthcare subject-matter expert. A reviewer familiar with CMS quality reporting should approve clinical and program interpretations.

## Review responsibilities

### Project owner

Confirm that:

- every candidate value has a source ID, SHA-256 hash, and evidence locator;
- missing source detail and source conflicts remain visible;
- reviewer identity, date, decision, and notes are captured;
- pending, revision-requested, or unapproved not-applicable values cannot enter a public dataset;
- no patient-level data appears in the artifact.ok

The project owner should not approve a numerator, denominator, exclusion, scoring direction, or risk-adjustment rule based only on an extraction.

### CMS quality-measure reviewer

Confirm that:

- the candidate value matches the cited performance year and collection type;
- the extraction preserves the meaning of the source section;
- exclusions and exceptions are not combined incorrectly;
- survey and administrative-claims measures are not forced into a clinical CQM model;
- titles, version identifiers, submission methods, and scoring direction are current for the cited revision;
- conflicts are resolved with an explicit source-backed note.

Useful reviewer backgrounds include CMS quality reporting, MSSP/APP administration, healthcare quality informatics, measure implementation, or compliance review. Clinical fields may also need a clinician or measure-steward review when interpretation affects clinical meaning.

## Workbook workflow

1. Open `cms-field-review-crosswalk.xlsx` and start with **Review Queue**.
2. Filter by performance year and collection type.
3. Open each related row in **Field Evidence**.
4. Compare the normalized candidate value with **Source excerpt** when present, then confirm it against the exact source section identified by the source hash and evidence locator.
5. Set the field decision to `approve`, `needs_revision`, or `not_applicable`.
6. Enter reviewer name, review date, and a short note when a decision is not `approve`.
7. Set a specification variant to `approve` only after every required field has an acceptable field-level decision.

The workbook is a review aid, not the authoritative database. Approved decisions must later be imported through a controlled, audited workflow.

## Importing completed decisions

When review is complete, export the workbook's **Field Evidence** sheet as a CSV file. Keep the evidence columns unchanged. The importer accepts the workbook's human-readable headings and ignores the introductory rows above the table.

Use `YYYY-MM-DD` in **Reviewed date**, or an ISO 8601 timestamp with a UTC offset. Every non-pending row requires a reviewer name and reviewed date. `needs_revision` and `not_applicable` also require reviewer notes.

First run validation only:

```sh
cd backend
uv run python -m app.commands.import_review_decisions \
  --input /path/to/reviewed-field-evidence.csv
```

After the validation report is clean, a technical operator can import the decisions into a local development database:

```sh
CMSQI_ALLOW_REVIEW_IMPORT=true uv run python -m app.commands.import_review_decisions \
  --input /path/to/reviewed-field-evidence.csv --apply
```

The import is idempotent. Each new decision creates an append-only audit event, while the candidate row keeps the latest private review state. The command never creates a public specification field, marks a measure public, or publishes a version.

## Extraction statuses

| Status | Meaning | Required action |
| --- | --- | --- |
| `candidate_extracted_needs_sme_review` | Text was extracted from a frozen source and assigned to a field. | Compare it with the cited section and confirm its interpretation. |
| `manual_extraction_or_policy_review_required` | The source format or policy question could not be normalized safely. | Review the source manually; do not approve the placeholder text. |
| `not_applicable_candidate_needs_sme_confirmation` | The field appears incompatible with that collection model. | Confirm that the field is truly not applicable; do not assume. |

A blank **Source excerpt** does not mean the candidate is unsupported or not
applicable. It means the frozen extraction did not capture a distinct verbatim
passage for that row. Review the linked official source at the evidence locator
before deciding. Manual-review guidance and proposed not-applicable reasons are
never copied into the excerpt column as if they were CMS wording.

## Publication rule

A field remains non-public unless all of the following are true:

1. the official source revision is frozen and hashed;
2. the evidence locator points to the correct performance year and collection type;
3. a qualified reviewer records an approval;
4. unresolved conflicts are closed;
5. freshness is checked immediately before publication;
6. publication occurs through a separate authorized transaction.

AI extraction, a successful automated test, or a completed spreadsheet formula is never sufficient evidence for clinical verification.

After a database review decision is saved, the admin interface reports the
field's publication eligibility. **Publish verified field** remains disabled when
the candidate is pending, lacks a captured literal excerpt, has stale/unverified
evidence, lacks verified program membership, conflicts with an existing public
field, or does not map exactly to the public contract. Publishing one eligible
field does not publish other candidates in the same version.

The current exact mappings are:

| Review candidate | Public field |
| --- | --- |
| `description` | `definition` |
| `population_or_denominator` | `denominator` |
| `numerator_or_outcome` | `numerator` |
| `exclusions` | `exclusions` |

Identity and additional implementation fields remain private until their public
semantics are defined explicitly. Do not force `data_collection`, measure type,
scoring direction, denominator exceptions, or risk adjustment into a loosely
related public field.

## Current review state and limitations

- All five detailed PY2026 eCQM pages are frozen and hashed. Their 40 formerly missing-detail items are now source-extracted candidates, not approvals.
- The current queue contains 275 extracted candidates, 70 manual-extraction or policy-review items, and 7 proposed not-applicable fields. All 352 decisions remain pending.
- The queue stores 182 literal excerpts separately from candidate values. The other 170 rows require locator-based source review and remain explicit blanks in the excerpt field.
- PY2025 Medicare Part B Claims artifacts are excluded because official APP Plus program sources identify eCQM, MIPS CQM, and Medicare CQM as the applicable clinical collection types.
- The database now preserves collection type explicitly and stages candidate fields separately from published `SpecificationField` records. This structural separation does not replace qualified review.
- C2.5 can validate and import future reviewer decisions into private, append-only audit history. Task 49 adds a separate authenticated transaction for publishing one eligible field after that review; imports still never publish automatically.
- The private admin dialog presents year-over-year candidate values and official excerpts independently. It does not infer clinical meaning from wording differences.
