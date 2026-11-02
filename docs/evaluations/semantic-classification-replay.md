# Controlled semantic-classification replay

This is a deterministic safety-harness replay, not a live-model benchmark or a healthcare accuracy claim.

- Fixture version: `semantic-eval-v1-controlled-replay`
- Fixture SHA-256: `8f63739ee8bc173fa8c556a6caa90dcd5e591a6f33bd1bc002cdb420248fc60d`
- Provider/model: `controlled-replay` / `semantic-eval-v1-controlled-replay`
- Total cases: 7
- Provider-eligible cases: 5
- Correctly skipped deterministic cases: 2/2
- Raw label accuracy: 3/5 (60.0%)
- Safety-adjusted accuracy after `needs_review` fallback: 4/5 (80.0%)
- Evidence-validation failures: 1
- Provider failures: 0
- `needs_review` fallbacks: 1

| Case | Category | Expected | Raw | Effective | Validation |
| --- | --- | --- | --- | --- | --- |
| substantive_denominator_change | substantive | substantive | substantive | substantive | — |
| wording_only_attribution_paraphrase | paraphrase | wording_only | wording_only | wording_only | — |
| unchanged_exact_definition | unchanged | not_applicable | — | not_applicable | — |
| conflicting_source_context | conflicting | needs_review | needs_review | needs_review | — |
| missing_comparison_year_evidence | missing_evidence | needs_review | substantive | needs_review | semantic_citation_coverage_incomplete |
| missing_field_value | missing_field | not_applicable | — | not_applicable | — |
| substantive_eligibility_misclassified | substantive | substantive | wording_only | wording_only | — |

## Interpretation

The replay outputs are intentionally mixed: they include correct labels, a valid misclassification, and a one-sided citation failure. The report proves that scoring and fail-closed evidence validation work; it does not measure an OpenAI model. Run the explicit live-provider command to produce model-specific results before making any model-performance statement.
