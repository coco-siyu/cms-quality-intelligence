"""Private, evidence-bounded generation of role-specific impact drafts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import ComparisonEvidenceStatus, ComparisonReviewDecision
from app.models import (
    ImpactExplanationCitation,
    ImpactExplanationDraft,
    MeasureComparison,
    MeasureComparisonEvidence,
)
from app.services.comparison_evidence import comparison_evidence_issues
from app.services.impact_explanation import (
    ImpactExplanationOutput,
    ImpactExplanationValidationError,
    validate_impact_citations,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt

PROMPT_VERSION = "cms-impact-explanation-v1"


class ImpactGenerationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ImpactProviderError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImpactComparisonInput:
    measure_id: str
    measure_name: str
    program: str
    collection_type: str
    from_year: int
    to_year: int
    overall_status: str
    fields: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class ImpactProviderResult:
    output: ImpactExplanationOutput
    response_id: str | None


class ImpactExplanationProvider(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactProviderResult: ...


class OpenAIImpactExplanationProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.model_name = model
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=1)

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactProviderResult:
        payload = {
            "approved_comparison": _comparison_payload(comparison),
            "official_evidence": [item.model_dump(mode="json") for item in evidence],
        }
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                store=False,
                max_output_tokens=3_500,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Explain only the supplied approved comparison using only the "
                            "supplied official excerpts. The plain-language summary is a "
                            "source fact and must cite both year sides. Data Analyst and ACO "
                            "Quality Manager statements are possible impacts, not verified "
                            "facts, and each must cite supplied evidence. State uncertainty "
                            "when evidence is incomplete. Do not browse, invent requirements, "
                            "make legal or regulatory conclusions, assign severity or "
                            "confidence scores, generate production SQL, approve, or publish."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, sort_keys=True)},
                ],
                text_format=ImpactExplanationOutput,
            )
        except ValueError as error:
            raise ImpactProviderError(
                "impact_provider_parse_error",
                "The provider response did not match the impact explanation schema.",
            ) from error
        except Exception as error:  # SDK transport/API errors share no stable base here.
            raise ImpactProviderError(
                "impact_provider_error",
                "The configured impact explanation provider request failed.",
            ) from error
        if response.output_parsed is None:
            raise ImpactProviderError(
                "impact_provider_refusal",
                "The provider returned no structured impact explanation.",
            )
        return ImpactProviderResult(output=response.output_parsed, response_id=response.id)


def provider_from_settings(settings: Settings) -> OpenAIImpactExplanationProvider:
    if not settings.openai_api_key or not settings.ai_impact_model:
        raise ImpactGenerationError(
            "impact_provider_not_configured",
            "Impact generation is optional and is not configured. Set both "
            "CMSQI_OPENAI_API_KEY and CMSQI_AI_IMPACT_MODEL to enable it.",
        )
    return OpenAIImpactExplanationProvider(
        api_key=settings.openai_api_key,
        model=settings.ai_impact_model,
        timeout_seconds=settings.ai_impact_timeout_seconds,
    )


def _comparison_payload(comparison: ImpactComparisonInput) -> dict[str, object]:
    return {
        "measure_id": comparison.measure_id,
        "measure_name": comparison.measure_name,
        "program": comparison.program,
        "collection_type": comparison.collection_type,
        "from_year": comparison.from_year,
        "to_year": comparison.to_year,
        "overall_status": comparison.overall_status,
        "fields": list(comparison.fields),
    }


def build_impact_generation_input(
    comparison: MeasureComparison,
) -> tuple[
    ImpactComparisonInput,
    list[SemanticEvidenceExcerpt],
    dict[str, MeasureComparisonEvidence],
]:
    if comparison.review_decision != ComparisonReviewDecision.APPROVE:
        raise ImpactGenerationError(
            "impact_comparison_not_approved",
            "Impact generation requires an approved comparison.",
        )
    if (
        comparison.evidence_status != ComparisonEvidenceStatus.VERIFIED
        or comparison_evidence_issues(comparison)
    ):
        raise ImpactGenerationError(
            "impact_evidence_not_verified",
            "Impact generation requires a currently verified comparison evidence set.",
        )
    if not comparison.affected_fields:
        raise ImpactGenerationError(
            "impact_comparison_has_no_fields",
            "Impact generation requires at least one approved comparison field.",
        )

    fields = tuple(
        {
            "field": field.field.value,
            "status": field.status.value,
            "from_availability": field.from_availability.value,
            "to_availability": field.to_availability.value,
            "from_value": field.from_value,
            "to_value": field.to_value,
        }
        for field in sorted(comparison.affected_fields, key=lambda item: item.field.value)
    )
    approved = ImpactComparisonInput(
        measure_id=comparison.measure.measure_id,
        measure_name=comparison.measure.name,
        program=comparison.program,
        collection_type=comparison.collection_type.value,
        from_year=comparison.from_year,
        to_year=comparison.to_year,
        overall_status=comparison.status.value,
        fields=fields,
    )

    links_by_evidence_id: dict[str, MeasureComparisonEvidence] = {}
    excerpts: list[SemanticEvidenceExcerpt] = []
    links = sorted(
        (link for field in comparison.affected_fields for link in field.evidence_links),
        key=lambda item: (item.side.value, item.evidence_reference.evidence_id),
    )
    for link in links:
        reference = link.evidence_reference
        if reference.evidence_id in links_by_evidence_id:
            raise ImpactGenerationError(
                "impact_evidence_duplicate",
                "A comparison cannot supply the same evidence ID more than once.",
            )
        links_by_evidence_id[reference.evidence_id] = link
        revision = reference.source_revision
        excerpts.append(
            SemanticEvidenceExcerpt(
                evidence_id=reference.evidence_id,
                source_revision_id=revision.revision_id,
                document_title=revision.source_document.title,
                official_url=revision.source_document.official_url,
                locator=reference.locator or "",
                excerpt=reference.excerpt,
                side=link.side,
            )
        )
    return approved, excerpts, links_by_evidence_id


def compute_impact_input_digest(
    comparison: ImpactComparisonInput,
    evidence: list[SemanticEvidenceExcerpt],
) -> str:
    payload = {
        "comparison": _comparison_payload(comparison),
        "evidence": [item.model_dump(mode="json") for item in evidence],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _citation_ids(output: ImpactExplanationOutput) -> set[str]:
    statements = [
        output.plain_language_summary,
        *output.data_analyst.technical_implications,
        *output.data_analyst.validation_considerations,
        *output.aco_quality_manager.operational_implications,
        *output.aco_quality_manager.coordination_considerations,
    ]
    result = {citation.evidence_id for statement in statements for citation in statement.citations}
    result.update(
        citation.evidence_id
        for caveat in output.uncertainty_caveats
        for citation in caveat.citations
    )
    return result


def generate_impact_explanation(
    session: Session,
    comparison: MeasureComparison,
    *,
    provider: ImpactExplanationProvider,
    created_by: str,
) -> ImpactExplanationDraft:
    """Create one idempotent private draft without approving or publishing it."""

    if comparison.id is None:
        raise ImpactGenerationError(
            "impact_comparison_not_persisted",
            "Impact generation requires a persisted comparison.",
        )
    approved, evidence, links_by_evidence_id = build_impact_generation_input(comparison)
    digest = compute_impact_input_digest(approved, evidence)
    existing = session.scalar(
        select(ImpactExplanationDraft).where(
            ImpactExplanationDraft.comparison_id == comparison.id,
            ImpactExplanationDraft.provider == provider.provider_name,
            ImpactExplanationDraft.model == provider.model_name,
            ImpactExplanationDraft.prompt_version == PROMPT_VERSION,
            ImpactExplanationDraft.input_digest == digest,
        )
    )
    if existing is not None:
        return existing

    result = provider.generate(comparison=approved, evidence=evidence)
    try:
        output = validate_impact_citations(result.output, evidence)
    except ImpactExplanationValidationError as error:
        raise ImpactGenerationError(error.code, error.message) from error

    draft = ImpactExplanationDraft(
        draft_id=f"CMS-IMPACT-{uuid4().hex}",
        comparison=comparison,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_digest=digest,
        output_payload=output.model_dump(mode="json"),
        provider_response_id=result.response_id,
        created_by=created_by,
    )
    draft.citations = [
        ImpactExplanationCitation(comparison_evidence=links_by_evidence_id[evidence_id])
        for evidence_id in sorted(_citation_ids(output))
    ]
    session.add(draft)
    session.flush()
    return draft
