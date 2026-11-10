"""Controlled integration coverage for the official-source publication pipeline.

The CMS-like records in this module are fictional test fixtures. They must never be
treated as verified CMS measure content or loaded into a production database.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_db
from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    CollectionType,
    ComparisonReviewDecision,
    ImpactExplanationReviewDecision,
    IngestionItemStage,
    IngestionRunStatus,
    NormalizedFieldStatus,
    NormalizedStagingStatus,
    PublicVerificationStatus,
)
from app.main import create_app
from app.models import (
    AIClarificationProposal,
    Measure,
    MeasureVersion,
    NormalizedFieldCandidate,
    ProgramMembership,
    SourceDocument,
    SourceRevision,
    SpecificationFieldCandidate,
)
from app.services.ai_clarification import (
    ClarificationOutput,
    EvidenceAssessment,
    EvidenceSnippet,
    ProviderResult,
    clarify_unresolved_field,
)
from app.services.ai_impact_explanation import (
    ImpactComparisonInput,
    ImpactExplanationProvider,
    ImpactProviderResult,
    generate_impact_explanation,
)
from app.services.comparison_publication import (
    publish_approved_comparison,
    record_comparison_review,
)
from app.services.deterministic_comparison import generate_draft_comparison
from app.services.impact_explanation import (
    ACOQualityManagerImpact,
    DataAnalystImpact,
    ImpactCitation,
    ImpactExplanationOutput,
    ImpactStatement,
    ImpactStatementType,
)
from app.services.impact_explanation_review import (
    publish_approved_impact_explanation,
    record_impact_explanation_review,
)
from app.services.ingestion_runs import create_ingestion_run, execute_ingestion_run
from app.services.publication import FieldPublicationError, publish_approved_field
from app.services.reviews import record_candidate_review
from app.services.semantic_classification import SemanticEvidenceExcerpt

PROGRAM = "Medicare Shared Savings Program — APP Plus"
FIXTURES = Path(__file__).parent / "fixtures" / "task53"
CHECKED_AT = datetime(2026, 11, 8, 12, tzinfo=UTC)


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _text_pdf(text: str) -> bytes:
    """Build a minimal, machine-readable PDF from the controlled fixture text."""

    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 36 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def _seed_measure(session: Session, *, years: tuple[int, ...] = (2025, 2026)) -> Measure:
    measure = Measure(
        measure_id="999",
        name="Controlled Integration Measure",
        description="Fictional Task 53 integration record.",
        is_public=False,
    )
    for year in years:
        measure.versions.append(
            MeasureVersion(
                version_id=f"TASK53-999-PY{year}-ECQM",
                program=PROGRAM,
                performance_year=year,
                collection_type=CollectionType.ECQM,
                specification_identifier=f"CMS999v{1 if year == 2025 else 2}",
                version_number=1,
                is_program_member=True,
                last_source_check_at=CHECKED_AT,
            )
        )
        measure.memberships.append(
            ProgramMembership(
                program=PROGRAM,
                performance_year=year,
                is_program_member=True,
                verified_at=CHECKED_AT,
            )
        )
    session.add(measure)
    session.flush()
    return measure


def _source(source_id: str, path: str, mime_type: str) -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        title=f"Controlled Task 53 source {source_id}",
        official_url=f"https://www.cms.gov/test/task53/{path}",
        mime_type=mime_type,
        created_by="task53-test",
    )


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _run(session: Session, handler: Callable[[httpx.Request], httpx.Response]):
    run = create_ingestion_run(session, created_by="task53-test", max_sources=10)
    with _client(handler) as client:
        return execute_ingestion_run(
            session,
            run,
            settings=Settings(),
            checked_by="task53-test",
            client=client,
        )


@contextmanager
def _test_client(session: Session) -> Generator[TestClient]:
    app = create_app()

    def override_database() -> Generator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class ControlledClarificationProvider:
    provider_name = "task53-test-provider"
    model_name = "task53-clarification-model"

    def propose(
        self,
        *,
        field_name: str,
        identity_context: str,
        evidence: list[EvidenceSnippet],
    ) -> ProviderResult:
        assert field_name == "exclusions"
        assert "CMS999v1" in identity_context
        assert evidence
        value = "Controlled exclusion wording for integration testing only."
        return ProviderResult(
            output=ClarificationOutput(
                outcome="proposed",
                proposed_value=value,
                summary=(
                    "A controlled corroborating excerpt was found; human review remains required."
                ),
                evidence_assessments=[
                    EvidenceAssessment(
                        evidence_id=item.evidence_id,
                        relation=("supports" if value in item.excerpt else "context"),
                        explanation=(
                            "The controlled excerpt contains the proposed wording."
                            if value in item.excerpt
                            else "The controlled excerpt supplies identity context only."
                        ),
                    )
                    for item in evidence
                ],
            ),
            response_id="task53-clarification-response",
        )


class ControlledImpactProvider(ImpactExplanationProvider):
    provider_name = "task53-test-provider"
    model_name = "task53-impact-model"

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactProviderResult:
        assert comparison.measure_id == "999"
        evidence_ids = [item.evidence_id for item in evidence]
        implication = ImpactStatement(
            statement="A reviewer may need to inspect the controlled year-specific values.",
            statement_type=ImpactStatementType.POSSIBLE_IMPACT,
            citations=[ImpactCitation(evidence_id=evidence_ids[0])],
        )
        return ImpactProviderResult(
            output=ImpactExplanationOutput(
                plain_language_summary=ImpactStatement(
                    statement="The controlled year values differ.",
                    statement_type=ImpactStatementType.SOURCE_FACT,
                    citations=[ImpactCitation(evidence_id=item) for item in evidence_ids],
                ),
                data_analyst=DataAnalystImpact(
                    technical_implications=[implication],
                    validation_considerations=[implication],
                ),
                aco_quality_manager=ACOQualityManagerImpact(
                    operational_implications=[implication],
                    coordination_considerations=[implication],
                ),
                uncertainty_caveats=[],
            ),
            response_id="task53-impact-response",
        )


def test_controlled_sources_reach_public_change_and_impact_only_after_review(
    session: Session,
) -> None:
    measure = _seed_measure(session)
    session.add_all(
        [
            _source("TASK53-2025", "py2025.html", "text/html"),
            _source("TASK53-2026", "py2026.pdf", "application/pdf"),
            _source("TASK53-CORROBORATING", "corroborating.html", "text/html"),
        ]
    )
    session.commit()
    responses = {
        "/test/task53/py2025.html": ("text/html", _fixture("py2025_measure.html")),
        "/test/task53/py2026.pdf": (
            "application/pdf",
            _text_pdf(_fixture("py2026_measure_pdf.txt").decode().strip()),
        ),
        "/test/task53/corroborating.html": (
            "text/html",
            _fixture("corroborating_exclusions.html"),
        ),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        mime_type, content = responses[request.url.path]
        return httpx.Response(200, headers={"content-type": mime_type}, content=content)

    with _test_client(session) as client:
        assert client.get("/api/measures/999").status_code == 404

        run = _run(session, handler)
        assert run.status == IngestionRunStatus.COMPLETED
        assert all(item.stage == IngestionItemStage.AWAITING_VERIFICATION for item in run.items)

        unresolved = next(
            item
            for item in session.scalars(
                select(NormalizedFieldCandidate).where(
                    NormalizedFieldCandidate.field_name == "exclusions",
                    NormalizedFieldCandidate.status == NormalizedFieldStatus.UNRESOLVED,
                )
            )
            if (
                item.measure_candidate.normalization.source_extraction.source_revision.source_document.source_id
                == "TASK53-2025"
            )
        )
        clarification = clarify_unresolved_field(
            session,
            unresolved,
            provider=ControlledClarificationProvider(),
            created_by="task53-test",
            max_excerpts=8,
            max_input_chars=20_000,
        )
        assert clarification.proposed_value is not None
        assert unresolved.status == NormalizedFieldStatus.UNRESOLVED
        assert session.query(AIClarificationProposal).count() == 1

        candidates = list(session.scalars(select(SpecificationFieldCandidate)))
        description_candidate = next(
            item
            for item in candidates
            if item.measure_version.performance_year == 2025 and item.field_name == "description"
        )
        unauthorized = client.patch(
            f"/api/admin/review-items/{description_candidate.review_item_id}",
            headers={"X-CMSQI-Admin-Action": "review-decision"},
            json={
                "decision": "approve",
                "reviewed_value": description_candidate.candidate_value,
            },
        )
        assert unauthorized.status_code == 401
        assert description_candidate.review_decision == CandidateReviewDecision.PENDING

        for revision in session.scalars(select(SourceRevision)):
            revision.verification_status = PublicVerificationStatus.VERIFIED
        for candidate in candidates:
            if candidate.field_name not in {"description", "numerator_or_outcome"}:
                continue
            record_candidate_review(
                candidate,
                decision=CandidateReviewDecision.APPROVE,
                reviewed_value=candidate.candidate_value,
                reviewer_name="task53-reviewer",
                reviewer_notes="Controlled integration approval.",
            )
            publish_approved_field(session, candidate, publisher_name="task53-reviewer")
        session.commit()

        public_measure = client.get("/api/measures/999")
        assert public_measure.status_code == 200
        assert all(
            field.field.value in {"definition", "numerator"}
            for version in measure.versions
            for field in version.fields
        )
        assert clarification.proposed_value not in public_measure.text

        comparison = generate_draft_comparison(
            session,
            measure_id="999",
            program=PROGRAM,
            from_year=2025,
            to_year=2026,
            collection_type=CollectionType.ECQM,
            fields=(AffectedField.DEFINITION, AffectedField.NUMERATOR),
        )
        params = {
            "program": PROGRAM,
            "collection_type": "ecqm",
            "from_year": 2025,
            "to_year": 2026,
        }
        assert client.get("/api/changes/999", params=params).status_code == 404
        record_comparison_review(
            comparison,
            decision=ComparisonReviewDecision.APPROVE,
            reviewer_name="task53-reviewer",
            reviewer_notes="Controlled evidence reviewed.",
        )
        publish_approved_comparison(session, comparison, publisher_name="task53-reviewer")
        session.commit()
        public_change = client.get("/api/changes/999", params=params)
        assert public_change.status_code == 200
        assert public_change.json()["status"] == "modified"

        draft = generate_impact_explanation(
            session,
            comparison,
            provider=ControlledImpactProvider(),
            created_by="task53-test",
        )
        assert client.get("/api/changes/999/impact-explanation", params=params).status_code == 404
        output = ImpactExplanationOutput.model_validate(draft.output_payload)
        record_impact_explanation_review(
            draft,
            decision=ImpactExplanationReviewDecision.APPROVE,
            output=output,
            reviewer_name="task53-reviewer",
        )
        publish_approved_impact_explanation(session, draft, publisher_name="task53-reviewer")
        session.commit()
        public_impact = client.get("/api/changes/999/impact-explanation", params=params)
        assert public_impact.status_code == 200
        assert public_impact.json()["output"]["plain_language_summary"]["statement"] == (
            "The controlled year values differ."
        )

        revision_count = session.query(SourceRevision).count()
        candidate_count = session.query(SpecificationFieldCandidate).count()
        unchanged_run = _run(session, handler)
        assert unchanged_run.status == IngestionRunStatus.COMPLETED
        assert all(item.stage == IngestionItemStage.UNCHANGED for item in unchanged_run.items)
        assert session.query(SourceRevision).count() == revision_count
        assert session.query(SpecificationFieldCandidate).count() == candidate_count


def test_failed_retrieval_can_be_retried_without_losing_audit_history(
    session: Session,
) -> None:
    session.add(_source("TASK53-RETRY", "retry.html", "text/html"))
    session.commit()

    failed = _run(session, lambda _request: httpx.Response(503, content=b"unavailable"))
    assert failed.status == IngestionRunStatus.COMPLETED_WITH_ERRORS
    assert failed.items[0].stage == IngestionItemStage.FAILED

    def recovered(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=_fixture("py2025_measure.html"),
        )

    recovered_run = _run(session, recovered)
    assert recovered_run.status == IngestionRunStatus.COMPLETED
    assert recovered_run.items[0].stage == IngestionItemStage.AWAITING_VERIFICATION
    assert session.query(SourceRevision).count() == 1
    assert failed.items[0].error is not None
    assert failed.items[0].events[-1].stage == IngestionItemStage.FAILED


def test_new_source_revision_reopens_a_completed_review_and_blocks_publication(
    session: Session,
) -> None:
    _seed_measure(session, years=(2025,))
    session.add(_source("TASK53-STALE", "stale.html", "text/html"))
    session.commit()
    content = _fixture("py2025_measure.html")

    def original(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=content)

    _run(session, original)
    candidate = session.scalar(
        select(SpecificationFieldCandidate).where(
            SpecificationFieldCandidate.field_name == "description"
        )
    )
    assert candidate is not None
    candidate.source_revision.verification_status = PublicVerificationStatus.VERIFIED
    record_candidate_review(
        candidate,
        decision=CandidateReviewDecision.APPROVE,
        reviewed_value=candidate.candidate_value,
        reviewer_name="task53-reviewer",
        reviewer_notes="Review completed before the source changed.",
    )
    session.commit()

    def revised(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=_fixture("py2025_measure_revised.html"),
        )

    second = _run(session, revised)
    session.refresh(candidate)
    assert second.status == IngestionRunStatus.COMPLETED
    assert candidate.measure_version.newer_revision_detected is True
    assert candidate.review_decision == CandidateReviewDecision.NEEDS_REVISION
    assert [event.decision for event in candidate.reviews] == [
        CandidateReviewDecision.APPROVE,
        CandidateReviewDecision.NEEDS_REVISION,
    ]
    assert any(
        field.staging_status == NormalizedStagingStatus.BLOCKED_NEWER_REVISION
        for item in second.items
        if item.source_check and item.source_check.extraction
        for normalization in item.source_check.extraction.normalizations
        for measure_candidate in normalization.measure_candidates
        for field in measure_candidate.fields
        if field.field_name == "description"
    )
    with pytest.raises(FieldPublicationError) as error:
        publish_approved_field(session, candidate, publisher_name="task53-reviewer")
    assert error.value.code == "field_publication_not_approved"
    assert candidate.measure_version.measure.is_public is False
    assert session.query(SourceRevision).count() == 2
