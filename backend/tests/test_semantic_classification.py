import pytest
from pydantic import ValidationError

from app.domain import (
    AffectedField,
    ChangeEvidenceSide,
    ChangeStatus,
    FieldAvailability,
    SemanticClassification,
)
from app.models import SpecificationField
from app.services.deterministic_comparison import compare_specification_field
from app.services.semantic_classification import (
    SemanticCitation,
    SemanticClassificationOutput,
    SemanticClassificationValidationError,
    SemanticEvidenceExcerpt,
    validate_semantic_citations,
)


def _evidence(side: ChangeEvidenceSide) -> SemanticEvidenceExcerpt:
    year = 2025 if side == ChangeEvidenceSide.FROM_VERSION else 2026
    return SemanticEvidenceExcerpt(
        evidence_id=f"CMS-EVIDENCE-{year}",
        source_revision_id=f"CMS-SOURCE-PY{year}-R1",
        document_title=f"Fictional official-source fixture for PY{year}",
        official_url=f"https://www.cms.gov/test/py-{year}.html",
        locator=f"Section {year}",
        excerpt=f"Source-backed fixture wording for performance year {year}.",
        side=side,
    )


def _conclusive_output(
    classification: SemanticClassification,
) -> SemanticClassificationOutput:
    return SemanticClassificationOutput(
        classification=classification,
        reasoning_summary="The cited year-specific excerpts support this limited assessment.",
        citations=[
            SemanticCitation(evidence_id="CMS-EVIDENCE-2025"),
            SemanticCitation(evidence_id="CMS-EVIDENCE-2026"),
        ],
        uncertainty_summary=None,
    )


@pytest.mark.parametrize(
    "classification",
    [SemanticClassification.SUBSTANTIVE, SemanticClassification.WORDING_ONLY],
)
def test_conclusive_classification_requires_supplied_evidence_from_both_sides(
    classification: SemanticClassification,
) -> None:
    output = _conclusive_output(classification)
    supplied = [
        _evidence(ChangeEvidenceSide.FROM_VERSION),
        _evidence(ChangeEvidenceSide.TO_VERSION),
    ]

    assert validate_semantic_citations(output, supplied) is output


def test_unsupported_citation_is_rejected() -> None:
    output = _conclusive_output(SemanticClassification.SUBSTANTIVE)
    output.citations[1] = SemanticCitation(evidence_id="CMS-EVIDENCE-NOT-SUPPLIED")

    with pytest.raises(SemanticClassificationValidationError) as error:
        validate_semantic_citations(
            output,
            [
                _evidence(ChangeEvidenceSide.FROM_VERSION),
                _evidence(ChangeEvidenceSide.TO_VERSION),
            ],
        )

    assert error.value.code == "semantic_citation_unsupported"


def test_conclusive_classification_cannot_cite_only_one_year_side() -> None:
    output = SemanticClassificationOutput(
        classification=SemanticClassification.WORDING_ONLY,
        reasoning_summary="Only one year was cited, so this cannot be conclusive.",
        citations=[SemanticCitation(evidence_id="CMS-EVIDENCE-2025")],
        uncertainty_summary=None,
    )

    with pytest.raises(SemanticClassificationValidationError) as error:
        validate_semantic_citations(
            output,
            [
                _evidence(ChangeEvidenceSide.FROM_VERSION),
                _evidence(ChangeEvidenceSide.TO_VERSION),
            ],
        )

    assert error.value.code == "semantic_citation_coverage_incomplete"


def test_needs_review_requires_explicit_uncertainty_but_not_invented_citations() -> None:
    output = SemanticClassificationOutput(
        classification=SemanticClassification.NEEDS_REVIEW,
        reasoning_summary="The available excerpts do not resolve whether meaning changed.",
        citations=[],
        uncertainty_summary="The comparison lacks enough source context for both years.",
    )

    assert validate_semantic_citations(output, []) is output

    with pytest.raises(ValidationError):
        SemanticClassificationOutput(
            classification=SemanticClassification.NEEDS_REVIEW,
            reasoning_summary="The result remains unresolved.",
            citations=[],
            uncertainty_summary=None,
        )


def test_output_forbids_duplicate_citations_and_unresolved_conclusions() -> None:
    with pytest.raises(ValidationError):
        SemanticClassificationOutput(
            classification=SemanticClassification.SUBSTANTIVE,
            reasoning_summary="Duplicate references are not valid coverage.",
            citations=[
                SemanticCitation(evidence_id="CMS-EVIDENCE-2025"),
                SemanticCitation(evidence_id="CMS-EVIDENCE-2025"),
            ],
            uncertainty_summary=None,
        )

    with pytest.raises(ValidationError):
        SemanticClassificationOutput(
            classification=SemanticClassification.WORDING_ONLY,
            reasoning_summary="A conclusive label cannot retain unresolved uncertainty.",
            citations=[SemanticCitation(evidence_id="CMS-EVIDENCE-2025")],
            uncertainty_summary="Meaning might still have changed.",
        )


def test_output_forbids_unexpected_provider_fields() -> None:
    with pytest.raises(ValidationError):
        SemanticClassificationOutput.model_validate(
            {
                "classification": "needs_review",
                "reasoning_summary": "The evidence is insufficient.",
                "citations": [],
                "uncertainty_summary": "The second year excerpt is missing.",
                "confidence_score": 0.98,
            }
        )


def test_contract_schema_is_strict_and_rejects_blank_evidence() -> None:
    schema = SemanticClassificationOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "classification",
        "reasoning_summary",
        "citations",
        "uncertainty_summary",
    }
    assert schema["$defs"]["SemanticClassification"]["enum"] == [
        "substantive",
        "wording_only",
        "needs_review",
    ]

    with pytest.raises(ValidationError):
        SemanticEvidenceExcerpt(
            evidence_id="CMS-EVIDENCE-BLANK",
            source_revision_id="CMS-SOURCE-R1",
            document_title="Official fixture",
            official_url="https://www.cms.gov/test/source.html",
            locator="   ",
            excerpt="   ",
            side=ChangeEvidenceSide.FROM_VERSION,
        )


def test_semantic_judgment_does_not_mutate_deterministic_difference() -> None:
    deterministic = compare_specification_field(
        AffectedField.DEFINITION,
        SpecificationField(
            field=AffectedField.DEFINITION,
            availability=FieldAvailability.AVAILABLE,
            value="Patients age 18 years and older.",
        ),
        SpecificationField(
            field=AffectedField.DEFINITION,
            availability=FieldAvailability.AVAILABLE,
            value="Patients who are at least 18 years old.",
        ),
    )
    semantic = _conclusive_output(SemanticClassification.WORDING_ONLY)

    validate_semantic_citations(
        semantic,
        [
            _evidence(ChangeEvidenceSide.FROM_VERSION),
            _evidence(ChangeEvidenceSide.TO_VERSION),
        ],
    )

    assert deterministic.status == ChangeStatus.MODIFIED
    assert semantic.classification == SemanticClassification.WORDING_ONLY
