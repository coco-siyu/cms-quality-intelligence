# Private impact generation and evaluation

Tasks 35 and 36 add a private generation boundary and a repeatable safety
evaluation. They do not add public AI content.

## Generation boundary

`generate_impact_explanation` accepts one persisted comparison only when:

- its human review decision is `approve`;
- its evidence state is currently `verified` and has no freshness or coverage
  issues;
- it contains at least one approved comparison field; and
- every cited evidence ID belongs to the exact server-supplied comparison
  evidence set.

The optional OpenAI adapter uses structured output parsing against
`ImpactExplanationOutput`. The application validates the parsed result a
second time before persistence. A factual summary must cite both year sides;
role implications must remain explicitly hypothetical. Schema failures,
unsupported citations, missing side coverage, refusals, and transport failures
do not create a draft.

Successful results are private rows in `impact_explanation_drafts`. The input
digest covers the approved comparison fields and immutable evidence excerpts,
so the same input is idempotent while a changed source input creates a new
historical draft. Citations are also stored as foreign-key links to the exact
comparison evidence rows. Drafts are available only from:

`GET /api/admin/comparisons/{comparison_id}/impact-explanations`

An authenticated administrator can explicitly request generation with
`X-CMSQI-Admin-Action: generate-impact-explanation` at:

`POST /api/admin/comparisons/{comparison_id}/impact-explanations/generate`

This is intentionally not triggered by a public request or page load, so a
provider call cannot happen accidentally. There is no public impact endpoint,
approval mutation, or publication mutation in Tasks 35 and 36.

## Configuration

Generation is disabled unless both variables are set:

```text
CMSQI_OPENAI_API_KEY
CMSQI_AI_IMPACT_MODEL
```

`CMSQI_AI_IMPACT_TIMEOUT_SECONDS` defaults to 60 seconds. Tests use a fake
provider and never contact OpenAI.

## Evaluation

Run the deterministic fictional replay from `backend/`:

```bash
uv run python -m app.commands.evaluate_impact_explanations
```

Regenerate the checked-in report with:

```bash
uv run python -m app.commands.evaluate_impact_explanations \
  --output ../docs/evaluations/impact-explanation-replay.md
```

The replay covers calculation, membership, wording-only, insufficient-evidence,
unsupported-citation, and role-label cases. It measures whether the application
accepts and rejects the intended fixture outputs. It does not measure a live
model, healthcare accuracy, or whether a suggestion is practically useful.
Those judgments remain part of Task 37 human review.
