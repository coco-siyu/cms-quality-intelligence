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
4. Compare the candidate value with the exact source section identified by the source hash and evidence locator.
5. Set the field decision to `approve`, `needs_revision`, or `not_applicable`.
6. Enter reviewer name, review date, and a short note when a decision is not `approve`.
7. Set a specification variant to `approve` only after every required field has an acceptable field-level decision.

The workbook is a review aid, not the authoritative database. Approved decisions must later be imported through a controlled, audited workflow.

## Extraction statuses

| Status | Meaning | Required action |
| --- | --- | --- |
| `candidate_extracted_needs_sme_review` | Text was extracted from a frozen source and assigned to a field. | Compare it with the cited section and confirm its interpretation. |
| `manual_extraction_or_policy_review_required` | The source format or policy question could not be normalized safely. | Review the source manually; do not approve the placeholder text. |
| `not_applicable_candidate_needs_sme_confirmation` | The field appears incompatible with that collection model. | Confirm that the field is truly not applicable; do not assume. |

## Publication rule

A field remains non-public unless all of the following are true:

1. the official source revision is frozen and hashed;
2. the evidence locator points to the correct performance year and collection type;
3. a qualified reviewer records an approval;
4. unresolved conflicts are closed;
5. freshness is checked immediately before publication;
6. publication occurs through a separate authorized transaction.

AI extraction, a successful automated test, or a completed spreadsheet formula is never sufficient evidence for clinical verification.

## Current review state and limitations

- All five detailed PY2026 eCQM pages are frozen and hashed. Their 40 formerly missing-detail items are now source-extracted candidates, not approvals.
- The current queue contains 275 extracted candidates, 70 manual-extraction or policy-review items, and 7 proposed not-applicable fields. All 352 decisions remain pending.
- PY2025 Medicare Part B Claims artifacts are excluded because official APP Plus program sources identify eCQM, MIPS CQM, and Medicare CQM as the applicable clinical collection types.
- The database now preserves collection type explicitly and stages candidate fields separately from published `SpecificationField` records. This structural separation does not replace qualified review.
