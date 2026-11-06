# M2 role-specific impact explanation contract

Task 34 defines the provider-independent output shape for a paired Data Analyst
and ACO Quality Manager explanation. It does not call a model, persist a draft,
approve content, add an endpoint, or change the public AI Impact tab. Those
behaviors remain Tasks 35–37.

## Output sections

`ImpactExplanationOutput` contains four required sections:

1. `plain_language_summary`: one concise, evidence-backed account of the
   approved change. It must be labeled `source_fact`.
2. `data_analyst`: bounded `technical_implications` and
   `validation_considerations` lists for mapping, calculation, dashboard, and
   testing review. Every item is labeled `possible_impact`.
3. `aco_quality_manager`: bounded `operational_implications` and
   `coordination_considerations` lists for reporting workflow, data capture, and
   team coordination review. Every item is labeled `possible_impact`.
4. `uncertainty_caveats`: explicit limitations. A caveat may have no citation
   when it identifies missing evidence; it must not invent an evidence ID.

Each summary or implication is an `ImpactStatement` with its text, statement
type, and one or more exact evidence IDs. This claim-level structure is stricter
than a shared citation list: a future reviewer can see which official excerpts
support each statement.

## Validation rules

- Unexpected fields are rejected throughout the contract.
- Every returned evidence ID must belong to the exact evidence set supplied by
  the server.
- The factual summary must cite evidence from both compared performance-year
  sides. Context-only evidence cannot replace either side.
- Duplicate supplied evidence IDs and duplicate citations within a statement
  or caveat are rejected.
- Role-specific implications must remain qualified as `possible_impact`; they
  cannot be presented as established CMS facts.
- Fenced code and common executable SQL forms are rejected. Discussion of
  mapping, calculation, dashboard, or validation considerations remains
  allowed. Task 36 must still evaluate prose for unsupported technical content.
- Numerical confidence, severity, production SQL, and regulatory-conclusion
  fields are absent and rejected as unexpected input.

Schema validation cannot determine whether prose is clinically or legally
correct. Task 35 must construct inputs only from approved comparisons and
official excerpts, and Task 36 must evaluate unsupported claims and role
usefulness before any publication workflow is added.

## Fictional example

This example is contract documentation only. It is not a CMS finding.

```json
{
  "plain_language_summary": {
    "statement": "The approved measure-set membership is unchanged across both years.",
    "statement_type": "source_fact",
    "citations": [
      {"evidence_id": "CMS-EVIDENCE-2025"},
      {"evidence_id": "CMS-EVIDENCE-2026"}
    ]
  },
  "data_analyst": {
    "technical_implications": [
      {
        "statement": "Existing year-specific roster mappings may remain applicable.",
        "statement_type": "possible_impact",
        "citations": [
          {"evidence_id": "CMS-EVIDENCE-2025"},
          {"evidence_id": "CMS-EVIDENCE-2026"}
        ]
      }
    ],
    "validation_considerations": [
      {
        "statement": "Validate the reporting-year filter before reusing mappings.",
        "statement_type": "possible_impact",
        "citations": [
          {"evidence_id": "CMS-EVIDENCE-2025"},
          {"evidence_id": "CMS-EVIDENCE-2026"}
        ]
      }
    ]
  },
  "aco_quality_manager": {
    "operational_implications": [
      {
        "statement": "The current measure-set review workflow may remain suitable.",
        "statement_type": "possible_impact",
        "citations": [
          {"evidence_id": "CMS-EVIDENCE-2025"},
          {"evidence_id": "CMS-EVIDENCE-2026"}
        ]
      }
    ],
    "coordination_considerations": [
      {
        "statement": "Confirm the roster with reporting and analytics teams.",
        "statement_type": "possible_impact",
        "citations": [
          {"evidence_id": "CMS-EVIDENCE-2025"},
          {"evidence_id": "CMS-EVIDENCE-2026"}
        ]
      }
    ]
  },
  "uncertainty_caveats": [
    {
      "statement": "Roster membership does not establish detailed specification equivalence.",
      "citations": [
        {"evidence_id": "CMS-EVIDENCE-2025"},
        {"evidence_id": "CMS-EVIDENCE-2026"}
      ]
    }
  ]
}
```

## Verification

From `backend/`:

```sh
uv run ruff check app tests
uv run pytest tests/test_impact_explanation_contract.py tests/test_openapi_contract.py
```
