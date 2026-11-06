import pytest
from pydantic import ValidationError

from app.domain import ChangeEvidenceSide
from app.services.impact_explanation import (
    ACOQualityManagerImpact,
    DataAnalystImpact,
    ImpactCitation,
    ImpactExplanationOutput,
    ImpactExplanationValidationError,
    ImpactStatement,
    ImpactStatementType,
    ImpactUncertaintyCaveat,
    validate_impact_citations,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt


def _evidence(side: ChangeEvidenceSide) -> SemanticEvidenceExcerpt:
    year = 2025 if side == ChangeEvidenceSide.FROM_VERSION else 2026
    return SemanticEvidenceExcerpt(
        evidence_id=f"CMS-EVIDENCE-{year}",
        source_revision_id=f"CMS-SOURCE-PY{year}-R1",
        document_title=f"Fictional official-source fixture for PY{year}",
        official_url=f"https://www.cms.gov/test/py-{year}.html",
        locator=f"Table {year}",
        excerpt=f"Source-backed fixture wording for performance year {year}.",
        side=side,
    )


def _citations(*years: int) -> list[ImpactCitation]:
    return [ImpactCitation(evidence_id=f"CMS-EVIDENCE-{year}") for year in years]


def _possible_impact(statement: str) -> ImpactStatement:
    return ImpactStatement(
        statement=statement,
        statement_type=ImpactStatementType.POSSIBLE_IMPACT,
        citations=_citations(2025, 2026),
    )


def _output() -> ImpactExplanationOutput:
    return ImpactExplanationOutput(
        plain_language_summary=ImpactStatement(
            statement="The approved measure-set membership is unchanged across both years.",
            statement_type=ImpactStatementType.SOURCE_FACT,
            citations=_citations(2025, 2026),
        ),
        data_analyst=DataAnalystImpact(
            technical_implications=[
                _possible_impact("Existing year-specific roster mappings may remain applicable.")
            ],
            validation_considerations=[
                _possible_impact("Validate the reporting-year filter before reusing mappings.")
            ],
        ),
        aco_quality_manager=ACOQualityManagerImpact(
            operational_implications=[
                _possible_impact("The current measure-set review workflow may remain suitable.")
            ],
            coordination_considerations=[
                _possible_impact("Confirm the roster with reporting and analytics teams.")
            ],
        ),
        uncertainty_caveats=[
            ImpactUncertaintyCaveat(
                statement=(
                    "Roster membership does not establish detailed specification equivalence."
                ),
                citations=_citations(2025, 2026),
            )
        ],
    )


def _supplied_evidence() -> list[SemanticEvidenceExcerpt]:
    return [
        _evidence(ChangeEvidenceSide.FROM_VERSION),
        _evidence(ChangeEvidenceSide.TO_VERSION),
    ]


def test_role_specific_output_validates_against_supplied_evidence() -> None:
    output = _output()

    assert validate_impact_citations(output, _supplied_evidence()) is output
    assert output.plain_language_summary.statement_type == ImpactStatementType.SOURCE_FACT
    assert all(
        item.statement_type == ImpactStatementType.POSSIBLE_IMPACT
        for item in output.data_analyst.technical_implications
        + output.data_analyst.validation_considerations
        + output.aco_quality_manager.operational_implications
        + output.aco_quality_manager.coordination_considerations
    )


def test_unsupported_and_duplicate_supplied_evidence_are_rejected() -> None:
    output = _output()
    output.data_analyst.technical_implications[0].citations = _citations(2025, 2030)

    with pytest.raises(ImpactExplanationValidationError) as unsupported:
        validate_impact_citations(output, _supplied_evidence())
    assert unsupported.value.code == "impact_citation_unsupported"

    evidence = _supplied_evidence()
    evidence.append(evidence[0])
    with pytest.raises(ImpactExplanationValidationError) as duplicate:
        validate_impact_citations(_output(), evidence)
    assert duplicate.value.code == "impact_evidence_duplicate"


def test_summary_requires_evidence_from_both_year_sides() -> None:
    output = _output()
    output.plain_language_summary.citations = _citations(2025)

    with pytest.raises(ImpactExplanationValidationError) as error:
        validate_impact_citations(output, _supplied_evidence())

    assert error.value.code == "impact_summary_citation_coverage_incomplete"


def test_summary_and_role_implications_require_explicit_characterization() -> None:
    with pytest.raises(ValidationError):
        ImpactExplanationOutput(
            **{
                **_output().model_dump(),
                "plain_language_summary": {
                    "statement": "This might affect reporting.",
                    "statement_type": "possible_impact",
                    "citations": [{"evidence_id": "CMS-EVIDENCE-2025"}],
                },
            }
        )

    payload = _output().model_dump()
    payload["data_analyst"]["technical_implications"][0]["statement_type"] = "source_fact"
    with pytest.raises(ValidationError):
        ImpactExplanationOutput.model_validate(payload)


@pytest.mark.parametrize(
    "statement",
    [
        "```sql\nSELECT * FROM production_measures;\n```",
        "SELECT measure_id FROM production_measures",
        "UPDATE production_measures SET status = 'verified'",
    ],
)
def test_contract_rejects_production_sql(statement: str) -> None:
    with pytest.raises(ValidationError):
        ImpactStatement(
            statement=statement,
            statement_type=ImpactStatementType.POSSIBLE_IMPACT,
            citations=_citations(2025),
        )


def test_contract_forbids_severity_confidence_and_regulatory_conclusion_fields() -> None:
    payload = _output().model_dump()
    payload["severity"] = "high"
    payload["confidence_score"] = 0.98
    payload["regulatory_conclusion"] = "The organization is compliant."

    with pytest.raises(ValidationError):
        ImpactExplanationOutput.model_validate(payload)


def test_contract_schema_is_strict_and_sections_are_required() -> None:
    schema = ImpactExplanationOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "plain_language_summary",
        "data_analyst",
        "aco_quality_manager",
        "uncertainty_caveats",
    }
    assert schema["$defs"]["ImpactStatement"]["additionalProperties"] is False
    assert schema["$defs"]["ImpactStatementType"]["enum"] == [
        "source_fact",
        "possible_impact",
    ]

    with pytest.raises(ValidationError):
        DataAnalystImpact(technical_implications=[], validation_considerations=[])


def test_uncertainty_can_name_missing_evidence_without_inventing_a_citation() -> None:
    caveat = ImpactUncertaintyCaveat(
        statement="The official source does not establish organization-specific workflow effects.",
        citations=[],
    )

    assert caveat.citations == []
