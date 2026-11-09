# M2 role-specific impact explanation contract

Task 34 defines the provider-independent output shape for a paired Data Analyst
and ACO Quality Manager explanation. Tasks 35 and 36 use that shape for private,
evidence-bounded generation and deterministic safety evaluation. Tasks 37, 51,
and 52 add fail-closed public display, joint human review, and append-only manual
regeneration without changing the output contract.

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
  allowed. Human review must still evaluate prose for unsupported technical content.
- Numerical confidence, severity, production SQL, and regulatory-conclusion
  fields are absent and rejected as unexpected input.

Schema validation cannot determine whether prose is clinically or legally
correct. Generation therefore uses only approved comparisons and official
excerpts, and the Task 36 replay tests the enforceable schema and citation
boundary. Human reviewers must still evaluate factual accuracy, unsupported
claims, and role usefulness before Task 37 publication.

## Versioning and regeneration

- Initial generation is idempotent for one comparison, provider, model, prompt,
  and exact evidence input.
- Manual regeneration is a separate authenticated action. It always creates a
  newly pending private sequence and never changes a prior generated payload or
  review decision.
- Rejected, outdated, approved, published, and withdrawn versions remain in the
  private history. A newly approved version replaces the public projection only
  through the separate publication action.
- Regeneration requires a currently approved comparison with verified evidence.
  It does not clear an outdated marker from an older version or publish content
  automatically.
- The regeneration service writes only the new explanation and its citations.
  Checklist persistence begins in Task 54, so later checklist reconciliation
  can preserve accepted and completed work independently of explanation versions.

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
