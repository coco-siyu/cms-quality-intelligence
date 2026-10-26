from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.domain import (
    ClarificationEvidenceRelation,
    ClarificationOutcome,
    CollectionType,
    NormalizedFieldStatus,
    PublicationState,
    SourceExtractionStatus,
)
from app.models import (
    AIClarificationProposal,
    Measure,
    MeasureVersion,
    SourceDocument,
    SourceExtraction,
    SourceRevision,
    SourceTextSegment,
    SpecificationFieldCandidate,
)
from app.services.ai_clarification import (
    ClarificationError,
    ClarificationOutput,
    EvidenceAssessment,
    EvidenceSnippet,
    ProviderResult,
    clarify_unresolved_field,
)
from app.services.source_normalization import normalize_extraction

PROGRAM = "Medicare Shared Savings Program — APP Plus"


class FakeProvider:
    provider_name = "test-provider"
    model_name = "test-model"

    def __init__(self, *, outcome: str = "proposed", invented_value: bool = False) -> None:
        self.outcome = outcome
        self.invented_value = invented_value
        self.calls = 0

    def propose(
        self,
        *,
        field_name: str,
        identity_context: str,
        evidence: list[EvidenceSnippet],
    ) -> ProviderResult:
        self.calls += 1
        assert field_name == "exclusions"
        assert "CMS122v14" in identity_context
        value = (
            "Invented wording not found in evidence."
            if self.invented_value
            else "Patients receiving hospice care are excluded."
        )
        relations = [
            EvidenceAssessment(
                evidence_id=item.evidence_id,
                relation=("conflicts" if self.outcome == "conflict" else "supports"),
                explanation="The registered CMS excerpt directly addresses exclusions.",
            )
            for item in evidence
        ]
        return ProviderResult(
            output=ClarificationOutput(
                outcome=self.outcome,
                proposed_value=value if self.outcome == "proposed" else None,
                summary="Official excerpts were compared; administrator review is still required.",
                evidence_assessments=relations,
            ),
            response_id="response-test-001",
        )


def _unresolved_field(session: Session):
    version = MeasureVersion(
        version_id="CMS-001-PY2026-ECQM",
        program=PROGRAM,
        performance_year=2026,
        collection_type=CollectionType.ECQM,
        specification_identifier="CMS122v14",
        version_number=1,
        is_program_member=True,
        publication_state=PublicationState.DRAFT,
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    session.add(
        Measure(
            measure_id="001",
            name="Test diabetes measure",
            description="Private AI clarification test record.",
            is_public=False,
            versions=[version],
        )
    )
    primary = SourceDocument(
        source_id="CMS-PRIMARY-SOURCE",
        title="Primary CMS measure source",
        official_url="https://www.cms.gov/test/primary.html",
        mime_type="text/html",
    )
    primary_revision = SourceRevision(
        revision_id="CMS-PRIMARY-SOURCE-R1",
        revision_number=1,
        content_hash="primary-hash",
        retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    extraction = SourceExtraction(
        extraction_id="CMS-PRIMARY-SOURCE-R1-X1",
        sequence=1,
        status=SourceExtractionStatus.EXTRACTED,
        page_count=None,
        extractor_version="stdlib-html-v1",
        forced=False,
        created_by="reviewer",
        segments=[
            SourceTextSegment(
                sequence=1,
                locator="HTML section: Document body",
                text="CMS eCQM ID CMS122v14. Performance Year 2026. eCQM.",
            ),
            SourceTextSegment(
                sequence=2,
                locator="HTML heading: Description",
                text="Description",
            ),
            SourceTextSegment(
                sequence=3,
                locator="HTML section: Description",
                text="A source-backed measure description.",
            ),
        ],
    )
    primary_revision.extractions.append(extraction)
    primary.revisions.append(primary_revision)
    session.add(primary)
    session.flush()
    normalization = normalize_extraction(session, extraction, created_by="reviewer")
    field = next(
        item
        for item in normalization.measure_candidates[0].fields
        if item.field_name == "exclusions"
    )
    assert field.status == NormalizedFieldStatus.UNRESOLVED
    return field


def _add_corroborating_source(session: Session, *, conflicting: bool = False) -> None:
    source = SourceDocument(
        source_id="CMS-CORROBORATING-SOURCE",
        title="Additional official CMS specification",
        official_url="https://www.cms.gov/test/corroborating.html",
        mime_type="text/html",
    )
    revision = SourceRevision(
        revision_id="CMS-CORROBORATING-SOURCE-R1",
        revision_number=1,
        content_hash="corroborating-hash",
        retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    text = (
        "CMS122v14 Exclusions: The document says no exclusions apply."
        if conflicting
        else "CMS122v14 Exclusions: Patients receiving hospice care are excluded."
    )
    revision.extractions.append(
        SourceExtraction(
            extraction_id="CMS-CORROBORATING-SOURCE-R1-X1",
            sequence=1,
            status=SourceExtractionStatus.EXTRACTED,
            page_count=None,
            extractor_version="stdlib-html-v1",
            forced=False,
            created_by="reviewer",
            segments=[
                SourceTextSegment(
                    sequence=1,
                    locator="HTML section: Exclusions",
                    text=text,
                )
            ],
        )
    )
    source.revisions.append(revision)
    session.add(source)
    session.flush()


def test_ai_clarification_is_private_evidenced_and_idempotent(session: Session) -> None:
    field = _unresolved_field(session)
    _add_corroborating_source(session)
    provider = FakeProvider()

    first = clarify_unresolved_field(
        session,
        field,
        provider=provider,
        created_by="reviewer",
        max_excerpts=4,
        max_input_chars=8_000,
    )
    second = clarify_unresolved_field(
        session,
        field,
        provider=provider,
        created_by="reviewer",
        max_excerpts=4,
        max_input_chars=8_000,
    )
    session.commit()

    assert second.clarification_id == first.clarification_id
    assert provider.calls == 1
    assert first.outcome == ClarificationOutcome.PROPOSED
    assert first.proposed_value == "Patients receiving hospice care are excluded."
    assert first.provider_response_id == "response-test-001"
    assert len(first.evidence) == 1
    assert first.evidence[0].relation == ClarificationEvidenceRelation.SUPPORTS
    assert first.evidence[0].source_revision.revision_id == (
        "CMS-CORROBORATING-SOURCE-R1"
    )
    assert session.query(AIClarificationProposal).count() == 1
    assert session.query(SpecificationFieldCandidate).count() == 1
    assert field.status == NormalizedFieldStatus.UNRESOLVED


def test_conflicting_ai_clarification_stays_unresolved_for_human_review(
    session: Session,
) -> None:
    field = _unresolved_field(session)
    _add_corroborating_source(session, conflicting=True)

    proposal = clarify_unresolved_field(
        session,
        field,
        provider=FakeProvider(outcome="conflict"),
        created_by="reviewer",
        max_excerpts=4,
        max_input_chars=8_000,
    )

    assert proposal.outcome == ClarificationOutcome.CONFLICT
    assert proposal.proposed_value is None
    assert proposal.evidence[0].relation == ClarificationEvidenceRelation.CONFLICTS
    assert field.status == NormalizedFieldStatus.UNRESOLVED


def test_ai_clarification_rejects_unsupported_model_wording(session: Session) -> None:
    field = _unresolved_field(session)
    _add_corroborating_source(session)

    with pytest.raises(ClarificationError) as error:
        clarify_unresolved_field(
            session,
            field,
            provider=FakeProvider(invented_value=True),
            created_by="reviewer",
            max_excerpts=4,
            max_input_chars=8_000,
        )

    assert error.value.code == "clarification_evidence_validation_error"
    assert session.query(AIClarificationProposal).count() == 0


def test_ai_clarification_requires_an_additional_registered_source(
    session: Session,
) -> None:
    field = _unresolved_field(session)

    with pytest.raises(ClarificationError) as error:
        clarify_unresolved_field(
            session,
            field,
            provider=FakeProvider(),
            created_by="reviewer",
            max_excerpts=4,
            max_input_chars=8_000,
        )

    assert error.value.code == "clarification_evidence_unavailable"
