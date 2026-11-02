"""Private, evidence-bounded semantic classification of deterministic field diffs."""

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
from app.domain import (
    AffectedField,
    ChangeStatus,
    CollectionType,
    ComparisonEvidenceStatus,
    SemanticClassification,
)
from app.models import (
    MeasureComparisonEvidence,
    MeasureComparisonField,
    SemanticClassificationCitation,
    SemanticClassificationProposal,
)
from app.services.comparison_evidence import comparison_evidence_issues
from app.services.semantic_classification import (
    SemanticClassificationOutput,
    SemanticClassificationValidationError,
    SemanticEvidenceExcerpt,
    validate_semantic_citations,
)

PROMPT_VERSION = "cms-semantic-classification-v1"
FALLBACK_PROVIDER_CODES = {
    "semantic_provider_parse_error",
    "semantic_provider_refusal",
}


class SemanticClassificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SemanticProviderError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SemanticFieldDifference:
    measure_id: str
    program: str
    collection_type: CollectionType
    from_year: int
    to_year: int
    field: AffectedField
    deterministic_status: ChangeStatus
    from_value: str
    to_value: str


@dataclass(frozen=True)
class SemanticProviderResult:
    output: SemanticClassificationOutput
    response_id: str | None


class SemanticClassificationProvider(Protocol):
    provider_name: str
    model_name: str

    def classify(
        self,
        *,
        difference: SemanticFieldDifference,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> SemanticProviderResult: ...


class OpenAISemanticClassificationProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.model_name = model
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=1)

    def classify(
        self,
        *,
        difference: SemanticFieldDifference,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> SemanticProviderResult:
        payload = {
            "deterministic_difference": _difference_payload(difference),
            "official_evidence": [item.model_dump(mode="json") for item in evidence],
        }
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                store=False,
                max_output_tokens=1_500,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Classify only the semantic significance of the supplied exact "
                            "field difference using only the supplied official excerpts. "
                            "Return substantive when meaning changed, wording_only when the "
                            "meaning is equivalent, and needs_review when evidence is missing, "
                            "ambiguous, or conflicting. A conclusive result must cite evidence "
                            "IDs from both year sides. Do not browse, infer unsupported policy, "
                            "change the deterministic result, approve, or publish anything."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(payload, sort_keys=True),
                    },
                ],
                text_format=SemanticClassificationOutput,
            )
        except ValueError as error:
            raise SemanticProviderError(
                "semantic_provider_parse_error",
                "The provider response did not match the semantic classification schema.",
            ) from error
        except Exception as error:  # SDK transport/API errors share no stable base here.
            raise SemanticProviderError(
                "semantic_provider_error",
                "The configured semantic classification provider request failed.",
            ) from error
        if response.output_parsed is None:
            raise SemanticProviderError(
                "semantic_provider_refusal",
                "The provider returned no structured semantic classification.",
            )
        return SemanticProviderResult(
            output=response.output_parsed,
            response_id=response.id,
        )


def provider_from_settings(settings: Settings) -> OpenAISemanticClassificationProvider:
    if not settings.openai_api_key or not settings.ai_semantic_model:
        raise SemanticClassificationError(
            "semantic_provider_not_configured",
            "Semantic classification is optional and is not configured. Set both "
            "CMSQI_OPENAI_API_KEY and CMSQI_AI_SEMANTIC_MODEL to enable it.",
        )
    return OpenAISemanticClassificationProvider(
        api_key=settings.openai_api_key,
        model=settings.ai_semantic_model,
        timeout_seconds=settings.ai_semantic_timeout_seconds,
    )


def _difference_payload(difference: SemanticFieldDifference) -> dict[str, object]:
    return {
        "measure_id": difference.measure_id,
        "program": difference.program,
        "collection_type": difference.collection_type.value,
        "from_year": difference.from_year,
        "to_year": difference.to_year,
        "field": difference.field.value,
        "deterministic_status": difference.deterministic_status.value,
        "from_value": difference.from_value,
        "to_value": difference.to_value,
    }


def _classification_input(
    field: MeasureComparisonField,
) -> tuple[
    SemanticFieldDifference,
    list[SemanticEvidenceExcerpt],
    dict[str, MeasureComparisonEvidence],
]:
    comparison = field.comparison
    if field.status != ChangeStatus.MODIFIED or field.from_value is None or field.to_value is None:
        raise SemanticClassificationError(
            "semantic_field_not_modified",
            "Only a deterministic modified field with both approved values can be classified.",
        )
    if (
        comparison.evidence_status != ComparisonEvidenceStatus.VERIFIED
        or comparison_evidence_issues(comparison)
    ):
        raise SemanticClassificationError(
            "semantic_evidence_not_verified",
            "Semantic classification requires a currently verified comparison evidence set.",
        )

    difference = SemanticFieldDifference(
        measure_id=comparison.measure.measure_id,
        program=comparison.program,
        collection_type=comparison.collection_type,
        from_year=comparison.from_year,
        to_year=comparison.to_year,
        field=field.field,
        deterministic_status=field.status,
        from_value=field.from_value,
        to_value=field.to_value,
    )
    links_by_evidence_id: dict[str, MeasureComparisonEvidence] = {}
    evidence: list[SemanticEvidenceExcerpt] = []
    for link in sorted(
        field.evidence_links,
        key=lambda item: (item.side.value, item.evidence_reference.evidence_id),
    ):
        reference = link.evidence_reference
        revision = reference.source_revision
        document = revision.source_document
        if reference.evidence_id in links_by_evidence_id:
            raise SemanticClassificationError(
                "semantic_evidence_duplicate",
                "A field comparison cannot supply the same evidence ID more than once.",
            )
        links_by_evidence_id[reference.evidence_id] = link
        evidence.append(
            SemanticEvidenceExcerpt(
                evidence_id=reference.evidence_id,
                source_revision_id=revision.revision_id,
                document_title=document.title,
                official_url=document.official_url,
                locator=reference.locator or "",
                excerpt=reference.excerpt,
                side=link.side,
            )
        )
    return difference, evidence, links_by_evidence_id


def _input_digest(
    difference: SemanticFieldDifference,
    evidence: list[SemanticEvidenceExcerpt],
) -> str:
    payload = {
        "difference": _difference_payload(difference),
        "evidence": [item.model_dump(mode="json") for item in evidence],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _fallback_output(code: str) -> SemanticClassificationOutput:
    return SemanticClassificationOutput(
        classification=SemanticClassification.NEEDS_REVIEW,
        reasoning_summary=(
            "The automated semantic assessment could not be validated and requires human review."
        ),
        citations=[],
        uncertainty_summary=f"Automated semantic assessment failed validation ({code}).",
    )


def classify_field_difference(
    session: Session,
    field: MeasureComparisonField,
    *,
    provider: SemanticClassificationProvider,
    created_by: str,
) -> SemanticClassificationProposal:
    """Create one idempotent private proposal without changing the comparison."""

    if field.id is None:
        raise SemanticClassificationError(
            "semantic_field_not_persisted",
            "Semantic classification requires a persisted deterministic field difference.",
        )
    difference, evidence, links_by_evidence_id = _classification_input(field)
    digest = _input_digest(difference, evidence)
    existing = session.scalar(
        select(SemanticClassificationProposal).where(
            SemanticClassificationProposal.comparison_field_id == field.id,
            SemanticClassificationProposal.provider == provider.provider_name,
            SemanticClassificationProposal.model == provider.model_name,
            SemanticClassificationProposal.prompt_version == PROMPT_VERSION,
            SemanticClassificationProposal.input_digest == digest,
        )
    )
    if existing is not None:
        return existing

    validation_error_code: str | None = None
    provider_response_id: str | None = None
    try:
        result = provider.classify(difference=difference, evidence=evidence)
        provider_response_id = result.response_id
        output = validate_semantic_citations(result.output, evidence)
    except SemanticClassificationValidationError as error:
        validation_error_code = error.code
        output = _fallback_output(error.code)
    except SemanticProviderError as error:
        if error.code not in FALLBACK_PROVIDER_CODES:
            raise
        validation_error_code = error.code
        output = _fallback_output(error.code)

    proposal = SemanticClassificationProposal(
        proposal_id=f"CMS-SEMANTIC-{uuid4().hex}",
        comparison_field=field,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_digest=digest,
        classification=output.classification,
        reasoning_summary=output.reasoning_summary,
        uncertainty_summary=output.uncertainty_summary,
        validation_error_code=validation_error_code,
        provider_response_id=provider_response_id,
        created_by=created_by,
    )
    for citation in output.citations:
        proposal.citations.append(
            SemanticClassificationCitation(
                comparison_evidence=links_by_evidence_id[citation.evidence_id]
            )
        )
    session.add(proposal)
    session.flush()
    return proposal
