# PY2025–PY2026 CMS MSSP / APP Plus source reconciliation

- Prepared: 2026-10-16; updated through C2.5 on 2026-10-19
- Checkpoint: C2.1–C2.5 research, source verification, and private review staging
- Publication state: candidate / non-public

## Scope and result

This review establishes a source-backed candidate inventory for the MSSP APP Plus measure membership applicable to PY2025 and PY2026. C2.4 also establishes private database staging for collection-specific variants and unapproved field candidates. It does not clinically verify specification fields, publish data, or implement comparison APIs.

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
- Methodology Version 14 cites an alternate CMS URL for the PY2026 quality performance standard. The current CMS guidance page uses a different URL. Both URLs were downloaded in C2.2 and produced identical bytes, so the second URL is recorded as a confirmed alias rather than a separate revision.
- The CMS guidance page is mutable and reported “Page Last Modified: 07/16/2026 12:17 PM” when retrieved. Its linked URLs must be rechecked when records are verified.
- ZIP package publication dates are not exposed reliably by the CMS landing page. Upload identifiers are retained, but no publication date is guessed.
- **Superseded revisions identified in C2.1: none.** No historical revision is designated superseded merely because a later-year document exists. A revision can be marked superseded only after a reviewer confirms that CMS replaced it for the same performance year and document lineage.

## Missing or ambiguous evidence

1. **Detailed specification fields are not yet verified.** Source-backed candidates are now staged for every variant, but numerator, denominator, exclusions, eligibility, and calculation logic still require field-by-field expert review.
2. **MIPS CQM and Medicare CQM release numbers need field-level review.** Exact archive members are recorded, and the package hashes establish revision identity, but release-history semantics have not been normalized into database version numbers.
3. **The PY2025 eCQM landing target remains ambiguous, but the artifacts are located.** The link currently exposed by the CMS guidance page resolves to a generic eCQI view. The year-specific APP Quality Requirements bundle contains the four PY2025 eCQM PDFs and confirms CMS122v13, CMS125v13, CMS2v14, and CMS165v13.
4. **Quality ID 001 has a title correction.** The final-rule fact sheet notes the former “Diabetes Hemoglobin A1c (HbA1c) Poor Control” title and a planned technical correction. Identity should remain anchored to Quality ID 001; titles must be stored per revision rather than used as identifiers.
5. **Collection types are not interchangeable versions.** A measure can have eCQM, MIPS CQM, and Medicare CQM specifications in the same year. Membership is one program-year fact; specification variants and their fields must remain distinguishable.
6. **CAHPS requires a separate evidence model.** Quality ID 321 is a survey measure and should not be forced into clinical numerator/denominator extraction assumptions.
7. **Administrative claims measures require specialized review.** Quality IDs 479 and 484 use CMS-calculated claims methodologies. Their evidence locators and fields will differ from clinical measure packages.
8. **No removal event is independently stated.** The reconciliation supports zero removals because both complete year rosters were positively established. The system still must never create a removal solely from an absent row in an incomplete source.
9. **PY2025 Medicare Part B Claims files are supporting artifacts, not APP Plus variants.** The PY2025 APP Quality Requirements bundle contains Medicare Part B Claims specifications for Quality IDs 001, 112, 134, and 236. The final-rule APP Plus phase-in table, PY2025 quality-performance-standard roster, CMS program guidance, and Methodology Version 13 identify eCQM, MIPS CQM, and Medicare CQM as the reportable clinical collection types. The Part B Claims files are therefore recorded as excluded from the APP Plus variant inventory rather than treated as an unresolved or verified fourth collection type.

## C2.2 verification outcome

C2.2 retrieved all 19 inventoried URLs on 2026-10-16 into the ignored local `var/cms-sources/` cache. [`source-revisions.csv`](source-revisions.csv) records the final URL, MIME type, byte length, retrieval timestamp, and SHA-256 hash for every source.

The two official PY2026 quality-standard URLs produced the same 266,777-byte PDF and the same SHA-256 hash (`85bc2c6b60fd68f8da7e8a61f38d2289bf25cb83356b2ba96c1183f55a60fcde`). The alternate URL is therefore confirmed as an alias of the same source revision rather than a second revision.

[`evidence-locators.csv`](evidence-locators.csv) records two independent complete-roster evidence sets for each performance year: the final-rule phase-in table and the applicable year-specific quality-standard Table 1. The project-owner review of the C2.1 roster permits the membership facts to be marked verified while all records remain draft and non-public.

[`collection-variants.csv`](collection-variants.csv) locates 32 policy-supported specification variants:

- PY2025: four eCQMs, four MIPS CQMs, four Medicare CQMs, CAHPS, and the HWR administrative-claims specification.
- PY2026: five eCQMs, five MIPS CQMs, five Medicare CQMs, CAHPS, HWR, and MCC.

The prepared seed artifact at `backend/app/data/cms_app_plus_2025_2026.seed.json` contains all eight identities and their 14 verified program-year memberships. It explicitly sets `is_public=false` and `publication_state=draft`. The guarded importer was validated against the local PostgreSQL database: the first run prepared eight identities and 14 roster versions, and the second run created no duplicates. All imported C2.2 measures remained private and all memberships and versions remained draft.

## C2.3–C2.5 field review and staging outcome

The review preparation covers all 32 located performance-year and collection-type variants. It creates 11 review items per variant, for 352 field-level items total:

- 275 candidate values extracted from the frozen source snapshot;
- 70 items requiring manual extraction or policy review;
- 7 collection-model fields proposed as not applicable, pending subject-matter confirmation.

Five official PY2026 eCQM human-readable specification pages were added to the frozen manifest, bringing it from 19 to 24 source revisions. Those pages close the prior source-detail gap for 40 PY2026 eCQM fields; the extracted values remain candidates.

C2.4 adds `collection_type` and `specification_identifier` to `MeasureVersion` and introduces a separate `SpecificationFieldCandidate` table. The guarded seed imports the 32 variants and 352 review items into private staging. Every item remains `pending`, every variant remains draft, and every measure remains non-public. The public repositories and API contract are unchanged.

The C2.4 migration and guarded seed were validated against the local PostgreSQL development database on 2026-10-18. The first C2.4 seed run added 32 private variants and 352 pending candidates to the existing roster; the second added zero records. Aggregate checks found 14 program-roster versions, 32 collection variants, 352 pending candidates, zero public CMS measures, and zero published CMS versions.

C2.5 adds an append-only review-event table and a guarded CSV importer. It validates reviewer identity, review date, decision vocabulary, candidate text, source ID, source hash, and evidence locator before writing. Repeated imports of the same decision create no duplicate event. Current candidate state may reflect the latest imported decision, but no import creates `SpecificationField` rows or changes publication state. Because the workbook remains unreviewed, the audit table starts empty and all 352 candidate decisions remain pending.

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

## PostgreSQL import workflow

C2.2 implements the frozen roster and roster-only seed. C2.4 extends steps 2–5 to collection-specific private variants and stages the review queue described in step 6. C2.5 validates future reviewer decisions and preserves them as private audit events. The remaining expert review, evidence-promotion, and publication steps are required before detailed specification fields can become public.

1. **Freeze a retrieval manifest.** Download official files, store original bytes outside public serving paths, calculate SHA-256, and record HTTP metadata and UTC retrieval time.
2. **Register document lineages.** Upsert `SourceDocument` by stable `source_id` and official URL. Preserve alternate URLs as separately reviewed aliases until content identity is established.
3. **Append revisions.** Insert `SourceRevision` rows by document lineage and content hash. Never update an existing row’s bytes-derived identity.
4. **Stage candidates.** Insert or update `Measure` identities by CMS Quality ID with `is_public=false`. Create draft `ProgramMembership` rows only from the reviewed membership matrix.
5. **Create year-specific variants.** Insert draft `MeasureVersion` rows for each program year and collection type. Keep the separate `program_roster` version for membership evidence.
6. **Extract fields to private staging.** Populate `SpecificationFieldCandidate` with the frozen value, extraction status, source revision, and locator. Keep the review decision `pending`; never fabricate a value to satisfy a UI field.
7. **Promote reviewed evidence.** After qualified approval, create or update public-model `SpecificationField` and `EvidenceReference` rows from the reviewed value and immutable source revision. Candidate rows do not become public merely because they exist.
8. **Run reconciliation checks.** Assert PY2025 count 6, PY2026 count 8, additions `{113, 484}`, unchanged `{001, 112, 134, 236, 321, 479}`, and no unsupported removal rows.
9. **Review conflicts and variants.** A human reviewer resolves titles, version IDs, collection types, and any source conflict. Unresolved rows stay draft and non-public.
10. **Publish transactionally.** Only after approval, set verification timestamps/statuses and publication states in one transaction. Public API queries continue to return only published records.
11. **Preserve audit history.** Record the import batch, reviewer, source hashes, validation results, and any supersession relationship without deleting historical revisions.

## Implemented schema decision

C2.4 implements the approved explicit variant dimension. `MeasureVersion` now identifies `collection_type` and an optional `specification_identifier`, and its uniqueness rule includes collection type. A separate private candidate table records field-level review state and source provenance. This allows eCQM, MIPS CQM, Medicare CQM, survey, and administrative-claims variants to coexist for one measure and year without treating unapproved text as a published specification.

## Review questions before the next data checkpoint

1. Confirm whether archived source bytes belong in object storage with hashes in PostgreSQL, or in another immutable document store.
2. Assign a qualified CMS quality-measure reviewer for the 352 pending field decisions.
3. Define the separate audited promotion transaction that converts approved candidate values into `SpecificationField` and `EvidenceReference` rows without overwriting review history.
4. Recheck all mutable official URLs immediately before any publication decision.
