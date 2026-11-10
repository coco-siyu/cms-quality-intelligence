"""Private, evidence-bounded generation of role-tagged impact task proposals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from openai import OpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import (
    ImpactExplanationReviewDecision,
    MeasureReviewStatus,
    ReviewEventType,
)
from app.models import (
    ImpactExplanationDraft,
    MeasureComparisonEvidence,
    MeasureReview,
    ReviewEvent,
    ReviewTaskProposal,
    ReviewTaskProposalCitation,
)
from app.services.ai_impact_explanation import (
    ImpactComparisonInput,
    build_impact_generation_input,
)
from app.services.impact_explanation import ImpactExplanationOutput
from app.services.impact_task_proposals import (
    ImpactTaskProposalOutput,
    ImpactTaskProposalValidationError,
    validate_task_proposal_citations,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt

PROMPT_VERSION = "cms-impact-task-proposals-v1"


class ImpactTaskGenerationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ImpactTaskProviderError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImpactTaskProviderResult:
    output: ImpactTaskProposalOutput
    response_id: str | None


class ImpactTaskProposalProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        approved_explanation: ImpactExplanationOutput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactTaskProviderResult: ...


class OpenAIImpactTaskProposalProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.model_name = model
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=1)

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        approved_explanation: ImpactExplanationOutput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactTaskProviderResult:
        payload = {
            "approved_comparison": {
                "measure_id": comparison.measure_id,
                "measure_name": comparison.measure_name,
                "program": comparison.program,
                "collection_type": comparison.collection_type,
                "from_year": comparison.from_year,
                "to_year": comparison.to_year,
                "overall_status": comparison.overall_status,
                "fields": list(comparison.fields),
            },
            "human_approved_impact_explanation": approved_explanation.model_dump(mode="json"),
            "official_evidence": [item.model_dump(mode="json") for item in evidence],
        }
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                store=False,
                max_output_tokens=3_000,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Propose concise optional follow-up tasks for Data Analysts, "
                            "ACO Quality Managers, or both roles. Use only the supplied "
                            "approved comparison, human-approved explanation, and official "
                            "evidence. Every task must cite supplied evidence. Describe tasks "
                            "as possible internal review or validation actions, never as CMS "
                            "requirements. Do not browse, invent facts, use patient-level data, "
                            "make legal conclusions, assign confidence or severity scores, "
                            "generate production SQL, approve tasks, or publish anything."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
                text_format=ImpactTaskProposalOutput,
            )
        except ValueError as error:
            raise ImpactTaskProviderError(
                "task_proposal_provider_parse_error",
                "The provider response did not match the task proposal schema.",
            ) from error
        except Exception as error:  # SDK transport/API errors share no stable base here.
            raise ImpactTaskProviderError(
                "task_proposal_provider_error",
                "The configured task proposal provider request failed.",
            ) from error
        if response.output_parsed is None:
            raise ImpactTaskProviderError(
                "task_proposal_provider_refusal",
                "The provider returned no structured task proposals.",
            )
        return ImpactTaskProviderResult(output=response.output_parsed, response_id=response.id)


def provider_from_settings(settings: Settings) -> OpenAIImpactTaskProposalProvider:
    if not settings.openai_api_key or not settings.ai_impact_model:
        raise ImpactTaskGenerationError(
            "task_proposal_provider_not_configured",
            "Task proposal generation is optional and is not configured. Set both "
            "CMSQI_OPENAI_API_KEY and CMSQI_AI_IMPACT_MODEL to enable it.",
        )
    return OpenAIImpactTaskProposalProvider(
        api_key=settings.openai_api_key,
        model=settings.ai_impact_model,
        timeout_seconds=settings.ai_impact_timeout_seconds,
    )


def _input_digest(
    draft: ImpactExplanationDraft,
    comparison: ImpactComparisonInput,
    approved_explanation: ImpactExplanationOutput,
    evidence: list[SemanticEvidenceExcerpt],
) -> str:
    payload = {
        "draft_id": draft.draft_id,
        "comparison": {
            "measure_id": comparison.measure_id,
            "program": comparison.program,
            "collection_type": comparison.collection_type,
            "from_year": comparison.from_year,
            "to_year": comparison.to_year,
            "overall_status": comparison.overall_status,
            "fields": list(comparison.fields),
        },
        "approved_explanation": approved_explanation.model_dump(mode="json"),
        "evidence": [item.model_dump(mode="json") for item in evidence],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _eligible_input(
    draft: ImpactExplanationDraft,
) -> tuple[
    ImpactComparisonInput,
    ImpactExplanationOutput,
    list[SemanticEvidenceExcerpt],
    dict[str, MeasureComparisonEvidence],
]:
    if draft.id is None:
        raise ImpactTaskGenerationError(
            "task_proposal_draft_not_persisted",
            "Task proposal generation requires a persisted impact explanation draft.",
        )
    if (
        draft.review_decision != ImpactExplanationReviewDecision.APPROVE
        or draft.approved_output_payload is None
    ):
        raise ImpactTaskGenerationError(
            "task_proposal_explanation_not_approved",
            "Approve the complete impact explanation before generating task proposals.",
        )
    if draft.outdated_at is not None:
        raise ImpactTaskGenerationError(
            "task_proposal_explanation_outdated",
            "Regenerate and approve the outdated impact explanation before generating tasks.",
        )
    comparison, evidence, links = build_impact_generation_input(draft.comparison)
    approved_explanation = ImpactExplanationOutput.model_validate(draft.approved_output_payload)
    return comparison, approved_explanation, evidence, links


def _review_for_draft(
    session: Session,
    draft: ImpactExplanationDraft,
    *,
    created_by: str,
) -> tuple[MeasureReview, int]:
    review = session.scalar(
        select(MeasureReview).where(MeasureReview.comparison_id == draft.comparison_id)
    )
    if review is None:
        review = MeasureReview(
            review_id=f"CMS-REVIEW-{uuid4().hex}",
            comparison=draft.comparison,
            status=MeasureReviewStatus.PENDING,
            created_by=created_by,
        )
        session.add(review)
        session.flush()
        review.events.append(
            ReviewEvent(
                event_id=f"CMS-REVIEW-EVENT-{uuid4().hex}",
                sequence=1,
                event_type=ReviewEventType.REVIEW_CREATED,
                actor=created_by,
                payload={"comparison_id": draft.comparison_id},
            )
        )
        session.flush()

    next_sequence = (
        session.scalar(
            select(func.max(ReviewEvent.sequence)).where(ReviewEvent.review_id == review.id)
        )
        or 0
    ) + 1
    return review, next_sequence


def generate_impact_task_proposals(
    session: Session,
    draft: ImpactExplanationDraft,
    *,
    provider: ImpactTaskProposalProvider,
    created_by: str,
) -> list[ReviewTaskProposal]:
    """Generate one idempotent private proposal batch for an approved draft."""

    existing = session.scalars(
        select(ReviewTaskProposal)
        .where(ReviewTaskProposal.impact_explanation_draft_id == draft.id)
        .order_by(ReviewTaskProposal.sequence)
    ).all()
    if existing:
        return list(existing)

    comparison, approved_explanation, evidence, links = _eligible_input(draft)
    digest = _input_digest(draft, comparison, approved_explanation, evidence)
    result = provider.generate(
        comparison=comparison,
        approved_explanation=approved_explanation,
        evidence=evidence,
    )
    try:
        output = validate_task_proposal_citations(result.output, evidence)
    except ImpactTaskProposalValidationError as error:
        raise ImpactTaskGenerationError(error.code, error.message) from error

    review, event_sequence = _review_for_draft(session, draft, created_by=created_by)
    proposals: list[ReviewTaskProposal] = []
    for sequence, generated in enumerate(output.proposals, start=1):
        proposal = ReviewTaskProposal(
            proposal_id=f"CMS-TASK-PROPOSAL-{uuid4().hex}",
            review=review,
            impact_explanation_draft=draft,
            sequence=sequence,
            role=generated.role,
            title=generated.title,
            description=generated.description,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=PROMPT_VERSION,
            input_digest=digest,
            provider_response_id=result.response_id,
            created_by=created_by,
        )
        proposal.citations = [
            ReviewTaskProposalCitation(comparison_evidence=links[citation.evidence_id])
            for citation in generated.citations
        ]
        session.add(proposal)
        review.events.append(
            ReviewEvent(
                event_id=f"CMS-REVIEW-EVENT-{uuid4().hex}",
                sequence=event_sequence,
                event_type=ReviewEventType.PROPOSAL_CREATED,
                subject_type="task_proposal",
                subject_id=proposal.proposal_id,
                actor=created_by,
                payload={
                    "draft_id": draft.draft_id,
                    "role": proposal.role.value,
                },
            )
        )
        event_sequence += 1
        proposals.append(proposal)

    session.flush()
    return proposals
