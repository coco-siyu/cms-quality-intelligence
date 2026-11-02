# M2 semantic classification contract

Task 26 defines the provider-independent structured output used to assess the
meaning of one deterministic field difference. Task 27 uses that contract in a
private provider workflow. Neither task approves a finding or changes the
deterministic comparison.

## Classification states

- `substantive`: the supplied year-specific excerpts support a meaningful
  difference in the field.
- `wording_only`: the text differs, but the supplied excerpts support the same
  meaning.
- `needs_review`: the supplied evidence is missing, conflicting, ambiguous, or
  otherwise insufficient for either conclusion.

These states are separate from `ChangeStatus`. A deterministic `modified`
result remains `modified` even when an unreviewed semantic output proposes
`wording_only`. A later human-reviewed workflow must decide whether any semantic
proposal changes the approved presentation.

## Structured output

`SemanticClassificationOutput` contains:

- one classification state;
- a bounded reasoning summary;
- zero or more citations by supplied evidence ID; and
- an uncertainty summary only when the result is `needs_review`.

Unexpected fields, blank summaries, duplicate citations, numeric confidence
scores, and conclusive results with unresolved uncertainty are rejected. The
reasoning summary is a concise evidence-based conclusion, not a request for or
record of private chain-of-thought.

Example conclusive output:

```json
{
  "classification": "wording_only",
  "reasoning_summary": "The two cited excerpts describe the same age threshold.",
  "citations": [
    {"evidence_id": "CMS-EVIDENCE-2025"},
    {"evidence_id": "CMS-EVIDENCE-2026"}
  ],
  "uncertainty_summary": null
}
```

Example unresolved output:

```json
{
  "classification": "needs_review",
  "reasoning_summary": "The available excerpts do not establish both year meanings.",
  "citations": [],
  "uncertainty_summary": "The comparison-year excerpt is missing."
}
```

## Citation validation

The server supplies `SemanticEvidenceExcerpt` objects containing immutable
evidence and source-revision IDs, document title, official URL, locator, literal
excerpt, and comparison side. A provider returns only evidence IDs; it cannot add
new source material.

Validation requires that:

1. every citation refers to an excerpt in the exact supplied set;
2. a conclusive result cites at least one `from_version` and one `to_version`
   excerpt;
3. context-only evidence cannot replace either year side;
4. duplicate supplied evidence IDs or duplicate citations are rejected; and
5. `needs_review` may omit citations when evidence is unavailable, but any
   citation it does return must still be supplied.

The Pydantic evidence shape is not itself proof that a source is official or
verified. Task 27 constructs provider input server-side from the Task 25
verified comparison evidence; it never trusts excerpts submitted by the model
or a public client.

## Task 27 private provider workflow

`classify_field_difference` accepts only a persisted deterministic `modified`
field with approved values on both sides and a currently verified Task 25
evidence set. It sends the exact values and immutable excerpts to the configured
structured-output provider, then revalidates citations on the server.

Each result is stored privately with provider, model, prompt version, input
digest, provider response ID, classification, uncertainty, and links to the
exact comparison-evidence rows it cited. Identical inputs are idempotent.
Parsing failures, refusals, unsupported citations, and one-sided citation
coverage become persisted `needs_review` proposals. Transport failures remain
retryable and create no misleading assessment. A provider-declared evidence
conflict also remains `needs_review`.

No public endpoint, UI, approval, or publication path is added by Tasks 26–28.

## Task 28 evaluation harness

The checked-in `semantic_classification_eval_v1.json` suite contains seven
explicitly fictional cases: substantive edits, a paraphrase, an exact unchanged
value, conflicting context, missing comparison-year evidence, a missing field
value, and a deliberately misclassified substantive edit. It contains no CMS
claim and no patient-level data.

Run the offline controlled replay from `backend/`:

```sh
uv run python -m app.commands.evaluate_semantic_classification
```

The controlled replay is deterministic and makes no network or model call. Its
outputs are intentionally mixed so tests can prove that the evaluator exposes a
valid-but-wrong label and converts an evidence-invalid conclusive result to
`needs_review`. The checked-in report is
`docs/evaluations/semantic-classification-replay.md`. It is a safety-harness
result, not a model benchmark or healthcare accuracy statement.

An operator may explicitly evaluate the configured OpenAI provider and write a
separate report:

```sh
uv run python -m app.commands.evaluate_semantic_classification \
  --provider openai \
  --confirm-live-model-call \
  --output ../docs/evaluations/semantic-classification-live.md
```

The confirmation flag is mandatory because a live run sends the fictional
fixtures to the configured provider and may incur cost. A live report applies
only to its recorded fixture hash and provider/model configuration; it must not
be generalized into a clinical or policy-reliability claim.
