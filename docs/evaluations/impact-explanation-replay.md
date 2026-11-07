# Controlled impact-explanation replay

This deterministic safety replay uses explicitly fictional content. It tests the schema and citation boundary; it is not a live-model benchmark, clinical claim, or proof that an implication is operationally useful.

- Fixture version: `fictional-impact-eval-v1`
- Fixture SHA-256: `b66bb34bfe18fa905149a296d6cc902fcab5dc80f48293177a6b11c118aa672d`
- Cases passing expected safeguards: 7/7
- Schema rejections: 1
- Evidence rejections: 2

| Case | Category | Expected | Actual | Expected error | Actual error | Pass |
| --- | --- | --- | --- | --- | --- | --- |
| calculation-change | calculation_change | accepted | accepted | — | — | yes |
| membership-change | membership_change | accepted | accepted | — | — | yes |
| membership-removal | membership_change | accepted | accepted | — | — | yes |
| wording-only | wording_only | accepted | accepted | — | — | yes |
| insufficient-evidence | insufficient_evidence | rejected | rejected | impact_summary_citation_coverage_incomplete | impact_summary_citation_coverage_incomplete | yes |
| unsupported-citation | unsupported_citation | rejected | rejected | impact_citation_unsupported | impact_citation_unsupported | yes |
| role-relevance-label | role_relevance | rejected | rejected | impact_schema_invalid | impact_schema_invalid | yes |

## Interpretation

The accepted calculation, membership, and wording fixtures demonstrate valid paired role output. The rejected fixtures demonstrate fail-closed handling for one-sided summaries, unknown evidence IDs, and role statements mislabeled as source facts. Human review remains necessary for factual accuracy, role relevance, and usefulness before any later publication step.
