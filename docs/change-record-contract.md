# M2 change record contract

This document defines the evidence and state rules for CMS Quality Intelligence
year-pair comparisons. It is the contract for M2 Tasks 23–25: Task 23 established
the representation, Task 24 implemented deterministic comparison, and Task 25
added structural evidence validation and the public projection gate. The
separate Task 26 AI output boundary is documented in
`docs/semantic-classification-contract.md`.

## Record shape

A change record belongs to one stable measure, program, collection variant,
baseline performance year, and comparison performance year. Its overall status
is one of:

- `added`: official, reviewed evidence confirms program membership or a field on
  the comparison side and confirms it did not apply on the baseline side.
- `removed`: official, reviewed evidence confirms it applied on the baseline
  side and explicitly did not apply on the comparison side.
- `modified`: both approved values are available and differ. This is the
  authoritative deterministic result until an approved semantic review says the
  difference is wording-only.
- `wording_only`: both approved values differ textually, but a reviewed semantic
  finding concludes that the supported meaning did not change. Automated text
  inequality alone cannot produce this state.
- `unchanged`: both approved values are available and match after the documented
  deterministic normalization used by Task 24.
- `unknown`: the available official evidence cannot support another state.

Each field comparison stores its field name, status, both explicit availability
states, both approved values when available, and evidence links labeled
`from_version`, `to_version`, or `context`.

## Missing-data safety rules

1. Absence from a document, extraction, candidate list, or database query is not
   evidence of removal.
2. If either side is `unresolved`, the field status must be `unknown`. This is
   enforced by the database schema.
3. `unavailable` means an approved source-backed determination that the field or
   membership does not apply. It is not a synonym for missing data.
4. `added` and `removed` require evidence for the applicable and non-applicable
   sides. A missing year version cannot satisfy that requirement by itself.
5. Only approved records and approved source revisions may cross the public API
   boundary. Draft comparisons and unreviewed semantic findings remain private.
6. A source update creates new review work; it must not silently rewrite an
   already published historical finding.

## Overall-status precedence

Task 24 must derive the overall status from approved field and membership
results, rather than accepting UI input. The intended precedence is:

1. `unknown` when any required result is unresolved;
2. explicit membership `added` or `removed`;
3. any substantive `modified` field;
4. any `wording_only` field;
5. `unchanged` only when every required result is resolved and unchanged.

Mixed cases must remain inspectable at field level. The overall status must not
hide an unresolved required field.

## API contract

`openapi.yaml` defines reusable `PublicChangeRecord`, `ChangeField`, and
`ChangeFieldEvidence` schemas. No new public endpoint is introduced by Task 23;
Task 29 will attach these schemas to the change-list and detail operations after
comparison generation and publication controls exist.

The code representation uses `wording_only` for URL and JSON stability while
the interface may display “Wording only.”

## Task 24 requirements

The deterministic comparator should:

- compare only versions for the same program and normalized measure identity;
- carry explicit `FieldAvailability` values into each result;
- return `unknown` before comparing text when either side is unresolved;
- never infer program removal from a missing version or roster row;
- attach both sides' approved evidence references without copying or altering
  the source excerpts; and
- write a draft comparison first, leaving publication to a separate reviewed
  action.

## Deterministic comparison behavior

Task 24 compares only published, reviewer-approved, current versions for the
same measure identity, program, and collection variant. Stored normalized text
is compared exactly: whitespace, punctuation, and capitalization differences
remain `modified`. The deterministic layer never emits `wording_only`; that
requires the separate reviewed semantic workflow in Tasks 26–28.

Missing field rows are treated as `unresolved`, not `unavailable`. A field is
`added` or `removed` only when one version explicitly records `unavailable` and
the other records an approved available value. Program membership uses the
versions' reviewed membership flags plus explicit measure-set availability, so
year-specific roster wording does not create a false modification.

`generate_draft_comparison` selects the latest eligible version for each year,
persists all requested field results and their before/after evidence links, and
is idempotent for an identical draft. It refuses to overwrite a different draft
or any published comparison.

## Evidence coverage and public projection

Every field comparison, including an `unknown` result, requires at least one
`from_version` and one `to_version` evidence reference. This prevents unresolved
or absent material from being presented as verified coverage. Each linked
reference must:

- contain a nonblank literal excerpt and a section or page locator;
- belong to the same normalized field, measure, program, collection variant,
  and expected performance-year side as the comparison;
- point to a published, reviewer-verified immutable source revision;
- come from a published, reviewed, current measure version; and
- resolve to an active source document with an HTTPS official URL.

The structural result is stored as `pending`, `verified`, or `incomplete` on the
comparison. Existing comparisons migrate as `incomplete` and must be
revalidated; the migration does not retroactively endorse historical data.
Structural verification does not publish a draft or replace human review.

`build_public_change_record` is the sole Task 25 projection of comparison
evidence. It returns no record unless the comparison is published, its stored
coverage state is `verified`, and a fresh validation still finds no issues. A
successful projection includes the evidence ID, source revision ID, source
document title, official URL, locator, literal excerpt, and year side for every
field. Task 29 will expose this projection through public change endpoints.
