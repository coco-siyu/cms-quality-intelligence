# CMS source inventory

This directory contains the Checkpoint C2.1 research artifacts for the Medicare Shared Savings Program (MSSP) Alternative Payment Model Performance Pathway (APP) Plus measure sets for performance years (PYs) 2025 and 2026.

These files are **review material, not production data**. Every measure row remains a candidate until a reviewer verifies the source files, locators, titles, collection types, and applicable year. Nothing in this directory authorizes publishing records through the public API.

## Artifacts

- [`source-inventory.csv`](source-inventory.csv) records official CMS and CMS-linked source documents, URLs, applicability, revision information, retrieval dates, and review status.
- [`source-revisions.csv`](source-revisions.csv) records the retrieved bytes, final URLs, MIME types, sizes, and SHA-256 hashes for the C2.2 source snapshot. The source bytes are retained only in the ignored local `var/cms-sources/` cache.
- [`measure-membership-candidates.csv`](measure-membership-candidates.csv) records the proposed PY2025 and PY2026 membership reconciliation.
- [`evidence-locators.csv`](evidence-locators.csv) records the exact tables and pages used to verify the complete year-specific rosters.
- [`collection-variants.csv`](collection-variants.csv) distinguishes program membership from the year-specific eCQM, MIPS CQM, Medicare CQM, survey, and administrative-claims specifications.
- [`field-review-crosswalk.csv`](field-review-crosswalk.csv) contains the source-backed candidate fields and unresolved review items. Every decision remains pending.
- [`cms-field-review-crosswalk.xlsx`](cms-field-review-crosswalk.xlsx) presents the same candidates as a filtered reviewer queue with field-level decisions, source hashes, and evidence locators.
- [`reviewer-guide.md`](reviewer-guide.md) separates project-owner checks from CMS quality-measure subject-matter review and defines the publication gate.
- [`reconciliation-report.md`](reconciliation-report.md) explains the evidence hierarchy, findings, unresolved questions, verification rules, and proposed PostgreSQL import workflow.

## Current candidate conclusion

| Reconciliation result | Quality IDs | Count |
| --- | --- | ---: |
| PY2025 candidate set | 001, 112, 134, 236, 321, 479 | 6 |
| PY2026 candidate set | 001, 112, 113, 134, 236, 321, 479, 484 | 8 |
| Unchanged membership candidates | 001, 112, 134, 236, 321, 479 | 6 |
| Added membership candidates | 113, 484 | 2 |
| Removed membership candidates | None supported | 0 |

“None supported” is not an inference from absence. It means the reviewed CMS sources positively list all six PY2025 candidates in PY2026 and add two more.

## Review boundary

The inventory was prepared on 2026-10-16. C2.2 retrieved and hashed all 19 inventoried sources on the same date. The mutable CMS guidance page and linked bundles must still be checked again immediately before publication. Downloaded artifacts are cached locally by source ID and must never be used to overwrite a previously registered revision when CMS publishes new bytes.

The field-review artifacts are private preparation material. Extracted values are not verified clinical facts until a qualified reviewer records a source-backed approval. They are not imported into public API records.
