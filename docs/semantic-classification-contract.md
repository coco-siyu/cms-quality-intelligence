# M2 semantic classification contract

Task 26 defines the provider-independent structured output used to assess the
meaning of one deterministic field difference. It does not call an AI provider,
persist an assessment, approve a finding, or change the deterministic comparison.

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
verified. Task 27 must construct provider input server-side from the Task 25
verified comparison evidence; it must never trust excerpts submitted by the
model or a public client.

## Deferred to Tasks 27–28

Task 27 will invoke the configured provider, validate its parsed response, store
model and prompt versions, and fall back to `needs_review` on provider, parsing,
citation, or evidence conflicts. Task 28 will evaluate the behavior against
labeled substantive, paraphrase, unchanged, missing, and conflicting fixtures.
No endpoint or UI is introduced by Task 26.
