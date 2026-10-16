# PY2025–PY2026 CMS MSSP / APP Plus source reconciliation

- Prepared: 2026-10-16
- Checkpoint: C2.1 research and inventory preparation only
- Publication state: candidate / non-public

## Scope and result

This review establishes a source-backed candidate inventory for the MSSP APP Plus measure membership applicable to PY2025 and PY2026. It does not verify specification fields, import records, publish data, or implement comparison APIs.

The candidate reconciliation is:

- PY2025: Quality IDs **001, 112, 134, 236, 321, and 479**.
- PY2026: the same six Quality IDs plus **113 and 484**.
- Candidate additions: **113 and 484**.
- Candidate removals: **none supported**.
- Candidate unchanged membership: **001, 112, 134, 236, 321, and 479**.

The “none supported” result is based on positive year-specific evidence, not on absence. CMS identifies all six PY2025 measures again for PY2026 and identifies two additional measures phased in for PY2026.

## Evidence hierarchy

1. **Policy and complete phase-in list.** The [CY2025 PFS final-rule fact sheet](https://www.cms.gov/newsroom/fact-sheets/calendar-year-cy-2025-medicare-physician-fee-schedule-final-rule-cms-1807-f-medicare-shared-savings) states that APP Plus begins in PY2025, that all measures are required annually, and provides the complete phase-in table. It specifies six measures for PY2025 and eight for PY2026.
2. **Year-specific roster evidence.** The [PY2025 quality performance standard](https://www.cms.gov/files/document/performance-year-2025-40th-percentile-mips-quality-performance-category-score.pdf) lists four clinical measures, CAHPS, and one administrative-claims measure. The [PY2026 quality performance standard](https://www.cms.gov/files/document/medicare-shared-savings-program-quality-performance-standard-performance-year-2026-40th-percentile.pdf) lists five clinical measures, CAHPS, and two administrative-claims measures.
3. **Methodology corroboration.** [Version 13](https://www.cms.gov/files/document/medicare-shared-savings-program-shared-savings-and-losses-and-assignment-methodology-specifications.pdf-4) corroborates the PY2025 composition and Quality ID 479. [Version 14](https://www.cms.gov/files/document/medicare-shared-savings-program-shared-savings-losses-assignment-methodology-specifications-version.pdf-0) corroborates the PY2026 composition and Quality IDs 479 and 484.
4. **Year- and collection-type specifications.** The [CMS Program Guidance & Specifications page](https://www.cms.gov/medicare/payment/fee-for-service-providers/shared-savings-program-ssp-acos/guidance-regulations) links the QPP and eCQI specification packages required for later field-level verification. A specification package can corroborate a version or field, but its presence alone does not establish APP Plus membership.

## Candidate membership matrix

| Quality ID | Candidate title | PY2025 | PY2026 | Candidate change | Collection type in scope |
| --- | --- | :---: | :---: | --- | --- |
| 001 | Diabetes: Glycemic Status Assessment Greater Than 9% | Yes | Yes | Unchanged | eCQM / MIPS CQM / Medicare CQM |
| 112 | Breast Cancer Screening | Yes | Yes | Unchanged | eCQM / MIPS CQM / Medicare CQM |
| 113 | Colorectal Cancer Screening | No | Yes | Added | eCQM / MIPS CQM / Medicare CQM |
| 134 | Preventive Care and Screening: Screening for Depression and Follow-Up Plan | Yes | Yes | Unchanged | eCQM / MIPS CQM / Medicare CQM |
| 236 | Controlling High Blood Pressure | Yes | Yes | Unchanged | eCQM / MIPS CQM / Medicare CQM |
| 321 | CAHPS for MIPS | Yes | Yes | Unchanged | CAHPS for MIPS Survey |
| 479 | Hospital-Wide, 30-day, All-Cause Unplanned Readmission (HWR) Rate for MIPS Eligible Clinician Groups | Yes | Yes | Unchanged | Administrative Claims |
| 484 | Clinician and Clinician Group Risk-standardized Hospital Admission Rates for Patients with Multiple Chronic Conditions | No | Yes | Added | Administrative Claims |

The CSV inventory is the machine-readable companion to this table. “No” for IDs 113 and 484 in PY2025 is supported by CMS’s complete phase-in table and the complete PY2025 roster; it is not inferred solely because a measure is absent from a document.

## Revisions and source status

- The PY2025 quality performance standard is a **March 2026 terminology update**. It is current supporting evidence for PY2025, not evidence that the measure membership took effect in 2026.
- Methodology Version 13 applies to PY2025; Version 14 applies to PY2026. They are parallel year-specific authorities, not a reason to overwrite Version 13 with Version 14.
- Methodology Version 14 cites an alternate CMS URL for the PY2026 quality performance standard. The current CMS guidance page uses a different URL. Until both files are downloaded and hashes match, the second URL is recorded as an unconfirmed alias.
- The CMS guidance page is mutable and reported “Page Last Modified: 07/16/2026 12:17 PM” when retrieved. Its linked URLs must be rechecked when records are verified.
- ZIP package publication dates are not exposed reliably by the CMS landing page. Upload identifiers are retained, but no publication date is guessed.
- **Superseded revisions identified in C2.1: none.** No historical revision is designated superseded merely because a later-year document exists. A revision can be marked superseded only after a reviewer confirms that CMS replaced it for the same performance year and document lineage.

## Missing or ambiguous evidence

1. **File hashes and archived originals are not yet captured.** C2.1 records URLs only. All PDFs and ZIP files need deterministic download, SHA-256 hashing, MIME validation, and immutable archival before database import.
2. **Bundle-internal versions are not yet reconciled.** Exact MIPS CQM, Medicare CQM, and eCQM version identifiers for each clinical measure must be extracted from the year-specific artifacts.
3. **The PY2025 eCQM landing target is ambiguous.** The link currently exposed by the CMS guidance page resolves to a generic eCQI view. The reviewer must resolve and preserve the exact PY2025 individual artifacts.
4. **Quality ID 001 has a title correction.** The final-rule fact sheet notes the former “Diabetes Hemoglobin A1c (HbA1c) Poor Control” title and a planned technical correction. Identity should remain anchored to Quality ID 001; titles must be stored per revision rather than used as identifiers.
5. **Collection types are not interchangeable versions.** A measure can have eCQM, MIPS CQM, and Medicare CQM specifications in the same year. Membership is one program-year fact; specification variants and their fields must remain distinguishable.
6. **CAHPS requires a separate evidence model.** Quality ID 321 is a survey measure and should not be forced into clinical numerator/denominator extraction assumptions.
7. **Administrative claims measures require specialized review.** Quality IDs 479 and 484 use CMS-calculated claims methodologies. Their evidence locators and fields will differ from clinical measure packages.
8. **No removal event is independently stated.** The reconciliation supports zero removals because both complete year rosters were positively established. The system still must never create a removal solely from an absent row in an incomplete source.

## Recommended verification rules

A candidate may advance to `verified` and then `published` only when all applicable rules pass:

1. **Two-source membership rule:** require the complete final-rule phase-in table plus the year-specific quality performance standard for program-year membership. A reviewer records locators for both.
2. **Positive removal rule:** a removal requires a complete authoritative roster for both years or explicit CMS removal language. Absence from a partial package, search result, or mutable web page is insufficient.
3. **Stable identity rule:** use the zero-padded CMS Quality ID as the cross-year identity. Store title changes as versioned values; do not create a new measure because a title changed.
4. **Year-and-variant rule:** verify each specification against its performance year and collection type. Do not copy fields between eCQM, MIPS CQM, Medicare CQM, survey, or administrative-claims variants without explicit evidence.
5. **Immutable revision rule:** create a new `SourceRevision` for every distinct content hash. Never overwrite or renumber a prior revision.
6. **Hash and MIME rule:** calculate SHA-256 from downloaded bytes, validate file type, record the retrieval timestamp in UTC, and retain the original official URL.
7. **Locator rule:** every published field requires a source revision, a stable locator such as page/table/file path, and a short reviewer-approved excerpt.
8. **Conflict rule:** if two official sources disagree, retain both revisions, mark the candidate `partially_verified` or `unresolved`, document the conflict, and keep it non-public.
9. **Freshness rule:** recheck the CMS guidance page and known official URLs immediately before publication. A newer hash sets `newer_revision_detected` until reviewed.
10. **Human approval rule:** AI-assisted extraction may prepare candidates, but a named human review action is required before `verified_at` or `publication_state=published` is set.

## Proposed PostgreSQL import workflow

This workflow is proposed for a later checkpoint; C2.1 does not execute it.

1. **Freeze a retrieval manifest.** Download official files, store original bytes outside public serving paths, calculate SHA-256, and record HTTP metadata and UTC retrieval time.
2. **Register document lineages.** Upsert `SourceDocument` by stable `source_id` and official URL. Preserve alternate URLs as separately reviewed aliases until content identity is established.
3. **Append revisions.** Insert `SourceRevision` rows by document lineage and content hash. Never update an existing row’s bytes-derived identity.
4. **Stage candidates.** Insert or update `Measure` identities by CMS Quality ID with `is_public=false`. Create draft `ProgramMembership` rows only from the reviewed membership matrix.
5. **Create year-specific versions.** Insert draft `MeasureVersion` rows for each program year and required specification variant. The present schema has one version stream per measure/program/year, so collection-type representation must be approved before importing multiple variants.
6. **Extract fields to staging.** Populate `SpecificationField` values as `available`, `unavailable`, or `unresolved`; never fabricate a value to satisfy a UI field.
7. **Attach evidence.** Create `EvidenceReference` rows pointing to immutable revisions and reviewer-confirmed locators/excerpts.
8. **Run reconciliation checks.** Assert PY2025 count 6, PY2026 count 8, additions `{113, 484}`, unchanged `{001, 112, 134, 236, 321, 479}`, and no unsupported removal rows.
9. **Review conflicts and variants.** A human reviewer resolves titles, version IDs, collection types, and any source conflict. Unresolved rows stay draft and non-public.
10. **Publish transactionally.** Only after approval, set verification timestamps/statuses and publication states in one transaction. Public API queries continue to return only published records.
11. **Preserve audit history.** Record the import batch, reviewer, source hashes, validation results, and any supersession relationship without deleting historical revisions.

## Schema decision required before import

The existing database protects source and revision history well, but `MeasureVersion` does not currently have a collection-type column. Because one Quality ID can have eCQM, MIPS CQM, and Medicare CQM variants in the same performance year, one of these options must be approved before field-level import:

- add an explicit collection-type/variant dimension to `MeasureVersion` and its uniqueness constraint; or
- designate one canonical display variant and store other variants in a separate related table.

No schema change is made in C2.1. The first option is recommended because it preserves source fidelity and avoids conflating specifications.

## Review questions before C2.2

1. Approve Quality ID as the stable measure identity and the eight-row reconciliation above.
2. Approve adding a collection-type/variant dimension before importing clinical specification fields.
3. Decide whether CMS-hosted QPP S3 and the CMS-linked eCQI Resource Center are accepted as first-party specification authorities alongside `cms.gov`.
4. Confirm whether archived source bytes belong in object storage with hashes in PostgreSQL, or in another immutable document store.
5. Assign the human reviewer responsible for changing candidates from `partially_verified` to `verified`.
