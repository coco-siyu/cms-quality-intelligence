import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import (
    ChangeStatus,
    ComparisonEvidenceStatus,
    SemanticClassification,
)
from app.models import (
    MeasureComparison,
    MeasureComparisonField,
    SemanticClassificationProposal,
)
from app.services.ai_semantic_classification import (
    SemanticClassificationError,
    SemanticClassificationProvider,
    SemanticFieldDifference,
    SemanticProviderError,
    SemanticProviderResult,
    classify_field_difference,
    provider_from_settings,
)
from app.services.semantic_classification import (
    SemanticCitation,
    SemanticClassificationOutput,
    SemanticEvidenceExcerpt,
)


class FakeSemanticProvider(SemanticClassificationProvider):
    provider_name = "test-provider"
    model_name = "test-semantic-model"

    def __init__(self, mode: str = "wording_only") -> None:
        self.mode = mode
        self.calls = 0

    def classify(
        self,
        *,
        difference: SemanticFieldDifference,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> SemanticProviderResult:
        self.calls += 1
        assert difference.measure_id == "DEMO-001"
        assert difference.deterministic_status == ChangeStatus.MODIFIED
        assert difference.from_value == "Fictional definition for 2025."
        assert difference.to_value == "Fictional definition for 2026."
        assert len(evidence) == 2

        if self.mode == "parse_error":
            raise SemanticProviderError(
                "semantic_provider_parse_error",
                "Synthetic structured-output parsing failure.",
            )
        if self.mode == "transport_error":
            raise SemanticProviderError(
                "semantic_provider_error",
                "Synthetic transport failure.",
            )

        citations = [SemanticCitation(evidence_id=item.evidence_id) for item in evidence]
        classification = SemanticClassification.WORDING_ONLY
        uncertainty_summary = None
        if self.mode == "substantive":
            classification = SemanticClassification.SUBSTANTIVE
        elif self.mode == "conflict":
            classification = SemanticClassification.NEEDS_REVIEW
            uncertainty_summary = "The official excerpts require human conflict review."
        elif self.mode == "unsupported_citation":
            citations[-1] = SemanticCitation(evidence_id="CMS-EVIDENCE-NOT-SUPPLIED")
        elif self.mode == "one_sided":
            citations = citations[:1]

        return SemanticProviderResult(
            output=SemanticClassificationOutput(
                classification=classification,
                reasoning_summary="The supplied official excerpts were compared.",
                citations=citations,
                uncertainty_summary=uncertainty_summary,
            ),
            response_id="response-semantic-test-001",
        )


def _comparison_field(session: Session) -> MeasureComparisonField:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    assert comparison.evidence_status == ComparisonEvidenceStatus.VERIFIED
    return comparison.affected_fields[0]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("wording_only", SemanticClassification.WORDING_ONLY),
        ("substantive", SemanticClassification.SUBSTANTIVE),
    ],
)
def test_classification_persists_private_cited_proposal_without_mutating_diff(
    seeded_session: Session,
    mode: str,
    expected: SemanticClassification,
) -> None:
    field = _comparison_field(seeded_session)
    provider = FakeSemanticProvider(mode)

    first = classify_field_difference(
        seeded_session,
        field,
        provider=provider,
        created_by="admin",
    )
    repeated = classify_field_difference(
        seeded_session,
        field,
        provider=provider,
        created_by="admin",
    )
    seeded_session.commit()

    assert repeated.id == first.id
    assert provider.calls == 1
    assert first.classification == expected
    assert first.prompt_version == "cms-semantic-classification-v1"
    assert first.provider_response_id == "response-semantic-test-001"
    assert first.validation_error_code is None
    assert len(first.input_digest) == 64
    assert {
        citation.comparison_evidence.evidence_reference.evidence_id
        for citation in first.citations
    } == {"DEMO-EVIDENCE-DEMO-001-2025", "DEMO-EVIDENCE-DEMO-001-2026"}
    assert field.status == ChangeStatus.MODIFIED
    assert field.comparison.status == ChangeStatus.MODIFIED
    assert seeded_session.query(SemanticClassificationProposal).count() == 1


def test_conflicting_evidence_stays_needs_review(
    seeded_session: Session,
) -> None:
    field = _comparison_field(seeded_session)

    proposal = classify_field_difference(
        seeded_session,
        field,
        provider=FakeSemanticProvider("conflict"),
        created_by="admin",
    )

    assert proposal.classification == SemanticClassification.NEEDS_REVIEW
    assert proposal.uncertainty_summary == (
        "The official excerpts require human conflict review."
    )
    assert proposal.validation_error_code is None
    assert len(proposal.citations) == 2
    assert field.status == ChangeStatus.MODIFIED


@pytest.mark.parametrize(
    ("mode", "error_code"),
    [
        ("unsupported_citation", "semantic_citation_unsupported"),
        ("one_sided", "semantic_citation_coverage_incomplete"),
        ("parse_error", "semantic_provider_parse_error"),
    ],
)
def test_invalid_provider_result_falls_back_to_needs_review(
    seeded_session: Session,
    mode: str,
    error_code: str,
) -> None:
    field = _comparison_field(seeded_session)

    proposal = classify_field_difference(
        seeded_session,
        field,
        provider=FakeSemanticProvider(mode),
        created_by="admin",
    )

    assert proposal.classification == SemanticClassification.NEEDS_REVIEW
    assert proposal.validation_error_code == error_code
    assert error_code in (proposal.uncertainty_summary or "")
    assert proposal.citations == []
    assert field.status == ChangeStatus.MODIFIED


def test_transport_failure_is_retryable_and_not_persisted(
    seeded_session: Session,
) -> None:
    field = _comparison_field(seeded_session)

    with pytest.raises(SemanticProviderError) as error:
        classify_field_difference(
            seeded_session,
            field,
            provider=FakeSemanticProvider("transport_error"),
            created_by="admin",
        )

    assert error.value.code == "semantic_provider_error"
    assert seeded_session.query(SemanticClassificationProposal).count() == 0


def test_classification_requires_verified_evidence_and_modified_values(
    seeded_session: Session,
) -> None:
    field = _comparison_field(seeded_session)
    provider = FakeSemanticProvider()
    field.comparison.evidence_status = ComparisonEvidenceStatus.INCOMPLETE

    with pytest.raises(SemanticClassificationError) as evidence_error:
        classify_field_difference(
            seeded_session,
            field,
            provider=provider,
            created_by="admin",
        )

    assert evidence_error.value.code == "semantic_evidence_not_verified"
    assert provider.calls == 0

    field.comparison.evidence_status = ComparisonEvidenceStatus.VERIFIED
    field.status = ChangeStatus.UNCHANGED
    with pytest.raises(SemanticClassificationError) as field_error:
        classify_field_difference(
            seeded_session,
            field,
            provider=provider,
            created_by="admin",
        )

    assert field_error.value.code == "semantic_field_not_modified"
    assert provider.calls == 0


def test_semantic_provider_configuration_is_optional() -> None:
    with pytest.raises(SemanticClassificationError) as error:
        provider_from_settings(Settings(openai_api_key=None, ai_semantic_model=None))

    assert error.value.code == "semantic_provider_not_configured"

    provider = provider_from_settings(
        Settings(
            openai_api_key="test-key-not-used",
            ai_semantic_model="test-model",
            ai_semantic_timeout_seconds=12,
        )
    )
    assert provider.provider_name == "openai"
    assert provider.model_name == "test-model"
