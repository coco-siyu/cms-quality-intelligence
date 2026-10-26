"""Bounded, evidence-only AI clarification for unresolved normalized fields."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import uuid4

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.domain import (
    ClarificationEvidenceRelation,
    ClarificationOutcome,
    NormalizedFieldStatus,
    SourceExtractionStatus,
)
from app.models import (
    AIClarificationEvidence,
    AIClarificationProposal,
    MeasureVersion,
    NormalizedFieldCandidate,
    NormalizedMeasureCandidate,
    SourceDocument,
    SourceExtraction,
    SourceNormalization,
    SourceRevision,
    SourceTextSegment,
)

PROMPT_VERSION = "cms-clarification-v1"

FIELD_TERMS: dict[str, tuple[str, ...]] = {
    "measure_title": ("measure title", "title"),
    "specification_identifier": ("cms ecqm id", "specification identifier"),
    "description": ("description",),
    "measure_type": ("measure type",),
    "scoring_direction": ("improvement notation", "scoring direction"),
    "population_or_denominator": ("initial population", "denominator"),
    "numerator_or_outcome": ("numerator", "outcome"),
    "exclusions": ("denominator exclusions", "exclusions"),
    "denominator_exceptions": ("denominator exceptions",),
    "data_collection": ("data collection", "collection type"),
    "risk_adjustment": ("risk adjustment",),
}


class ClarificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    relation: Literal["supports", "conflicts", "context"]
    explanation: str = Field(min_length=1, max_length=2_000)


class ClarificationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["proposed", "unresolved", "conflict"]
    proposed_value: str | None
    summary: str = Field(min_length=1, max_length=4_000)
    evidence_assessments: list[EvidenceAssessment]


@dataclass(frozen=True)
class EvidenceSnippet:
    evidence_id: str
    segment: SourceTextSegment
    revision: SourceRevision
    source_id: str
    source_title: str
    official_url: str
    locator: str
    excerpt: str
    score: int


@dataclass(frozen=True)
class ProviderResult:
    output: ClarificationOutput
    response_id: str | None


class ClarificationProvider(Protocol):
    provider_name: str
    model_name: str

    def propose(
        self,
        *,
        field_name: str,
        identity_context: str,
        evidence: list[EvidenceSnippet],
    ) -> ProviderResult: ...


class OpenAIClarificationProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        self.model_name = model
        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=1)

    def propose(
        self,
        *,
        field_name: str,
        identity_context: str,
        evidence: list[EvidenceSnippet],
    ) -> ProviderResult:
        evidence_payload = [
            {
                "evidence_id": item.evidence_id,
                "source_id": item.source_id,
                "source_title": item.source_title,
                "official_url": item.official_url,
                "locator": item.locator,
                "excerpt": item.excerpt,
            }
            for item in evidence
        ]
        try:
            response = self._client.responses.parse(
                model=self.model_name,
                store=False,
                max_output_tokens=1_500,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You clarify one unresolved CMS measure field using only the "
                            "provided official CMS excerpts. Assess every evidence_id exactly "
                            "once. Use proposed only when proposed_value is a literal contiguous "
                            "quotation from supporting evidence. Use conflict when official "
                            "excerpts disagree. Otherwise use unresolved. Do not infer policy, "
                            "invent identifiers, browse, approve, or publish anything."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "field_name": field_name,
                                "identity_context": identity_context,
                                "official_evidence": evidence_payload,
                            },
                            sort_keys=True,
                        ),
                    },
                ],
                text_format=ClarificationOutput,
            )
        except Exception as error:  # OpenAI SDK exposes several transport/API subclasses.
            raise ClarificationError(
                "clarification_provider_error",
                "The configured clarification provider did not return a usable response.",
            ) from error
        if response.output_parsed is None:
            raise ClarificationError(
                "clarification_provider_refusal",
                "The clarification provider returned no structured proposal.",
            )
        return ProviderResult(output=response.output_parsed, response_id=response.id)


def provider_from_settings(settings: Settings) -> OpenAIClarificationProvider:
    if not settings.openai_api_key or not settings.ai_clarification_model:
        raise ClarificationError(
            "clarification_provider_not_configured",
            "AI clarification is optional and is not configured. Set both "
            "CMSQI_OPENAI_API_KEY and CMSQI_AI_CLARIFICATION_MODEL to enable it.",
        )
    return OpenAIClarificationProvider(
        api_key=settings.openai_api_key,
        model=settings.ai_clarification_model,
        timeout_seconds=settings.ai_clarification_timeout_seconds,
    )


def _latest_extraction(revision: SourceRevision) -> SourceExtraction | None:
    successful = [
        extraction
        for extraction in revision.extractions
        if extraction.status == SourceExtractionStatus.EXTRACTED
    ]
    return max(successful, key=lambda item: item.sequence, default=None)


def _identity_terms(field: NormalizedFieldCandidate) -> tuple[list[str], str]:
    candidate = field.measure_candidate
    version = candidate.matched_measure_version
    measure_id = candidate.measure_id_candidate
    specification_id = candidate.specification_identifier_candidate
    year = candidate.performance_year_candidate
    collection = candidate.collection_type_candidate
    if version is not None:
        measure_id = version.measure.measure_id
        specification_id = version.specification_identifier or specification_id
        year = version.performance_year
        collection = version.collection_type.value

    terms = [term for term in (specification_id, measure_id) if term]
    context = json.dumps(
        {
            "measure_id": measure_id,
            "specification_identifier": specification_id,
            "performance_year": year,
            "collection_type": collection,
        },
        sort_keys=True,
    )
    return terms, context


def _contains_term(text: str, term: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, re.I))


def retrieve_corroborating_evidence(
    session: Session,
    field: NormalizedFieldCandidate,
    *,
    max_excerpts: int,
    max_input_chars: int,
) -> tuple[list[EvidenceSnippet], str]:
    identity_terms, identity_context = _identity_terms(field)
    if not identity_terms:
        raise ClarificationError(
            "clarification_identity_unresolved",
            "No stable measure or specification identifier is available for evidence retrieval.",
        )

    original_document_id = (
        field.measure_candidate.normalization.source_extraction.source_revision.source_document_id
    )
    documents = list(
        session.scalars(
            select(SourceDocument)
            .where(SourceDocument.is_active.is_(True), SourceDocument.id != original_document_id)
            .options(
                selectinload(SourceDocument.revisions)
                .selectinload(SourceRevision.extractions)
                .selectinload(SourceExtraction.segments)
            )
        ).unique()
    )

    ranked: list[EvidenceSnippet] = []
    field_terms = FIELD_TERMS.get(field.field_name, (field.field_name.replace("_", " "),))
    for document in documents:
        revision = max(document.revisions, key=lambda item: item.revision_number, default=None)
        if revision is None:
            continue
        extraction = _latest_extraction(revision)
        if extraction is None:
            continue
        for segment in extraction.segments:
            searchable = f"{document.title} {segment.text}"
            identity_hits = sum(_contains_term(searchable, term) for term in identity_terms)
            if identity_hits == 0:
                continue
            field_hits = sum(term.casefold() in searchable.casefold() for term in field_terms)
            score = identity_hits * 10 + field_hits * 3
            excerpt = re.sub(r"\s+", " ", segment.text).strip()[:3_000]
            if not excerpt:
                continue
            evidence_id = "CMS-AI-EVID-" + hashlib.sha256(
                f"{revision.revision_id}|{segment.id}|{field.field_name}".encode()
            ).hexdigest()[:24]
            ranked.append(
                EvidenceSnippet(
                    evidence_id=evidence_id,
                    segment=segment,
                    revision=revision,
                    source_id=document.source_id,
                    source_title=document.title,
                    official_url=document.official_url,
                    locator=segment.locator,
                    excerpt=excerpt,
                    score=score,
                )
            )

    selected: list[EvidenceSnippet] = []
    total_chars = 0
    for item in sorted(ranked, key=lambda value: (-value.score, value.source_id, value.locator)):
        if len(selected) >= max_excerpts:
            break
        if total_chars + len(item.excerpt) > max_input_chars:
            continue
        selected.append(item)
        total_chars += len(item.excerpt)
    if not selected:
        raise ClarificationError(
            "clarification_evidence_unavailable",
            "No corroborating excerpt was found in an additional registered CMS source.",
        )
    return selected, identity_context


def _validate_output(
    output: ClarificationOutput, evidence: list[EvidenceSnippet]
) -> dict[str, EvidenceAssessment]:
    expected = {item.evidence_id: item for item in evidence}
    assessments = {item.evidence_id: item for item in output.evidence_assessments}
    if len(assessments) != len(output.evidence_assessments) or set(assessments) != set(expected):
        raise ClarificationError(
            "clarification_evidence_validation_error",
            "The model response did not assess the supplied evidence IDs exactly once.",
        )
    has_conflict = any(item.relation == "conflicts" for item in assessments.values())
    if has_conflict and output.outcome != "conflict":
        raise ClarificationError(
            "clarification_evidence_validation_error",
            "Conflicting source evidence must remain a conflict for human review.",
        )
    if output.outcome == "proposed":
        if not output.proposed_value:
            raise ClarificationError(
                "clarification_evidence_validation_error",
                "A proposed clarification requires a proposed value.",
            )
        supporting_excerpts = [
            expected[key].excerpt
            for key, assessment in assessments.items()
            if assessment.relation == "supports"
        ]
        normalized_value = re.sub(r"\s+", " ", output.proposed_value).strip().casefold()
        if not normalized_value or not any(
            normalized_value in re.sub(r"\s+", " ", excerpt).casefold()
            for excerpt in supporting_excerpts
        ):
            raise ClarificationError(
                "clarification_evidence_validation_error",
                "The proposed value was not a literal quotation from supporting evidence.",
            )
    elif output.proposed_value is not None:
        raise ClarificationError(
            "clarification_evidence_validation_error",
            "Unresolved or conflicting evidence cannot include a proposed value.",
        )
    return assessments


def clarify_unresolved_field(
    session: Session,
    field: NormalizedFieldCandidate,
    *,
    provider: ClarificationProvider,
    created_by: str,
    max_excerpts: int,
    max_input_chars: int,
) -> AIClarificationProposal:
    if field.status != NormalizedFieldStatus.UNRESOLVED:
        raise ClarificationError(
            "clarification_field_not_unresolved",
            "Only unresolved normalized fields can request AI clarification.",
        )
    evidence, identity_context = retrieve_corroborating_evidence(
        session,
        field,
        max_excerpts=max_excerpts,
        max_input_chars=max_input_chars,
    )
    digest_payload = {
        "field_candidate_id": field.field_candidate_id,
        "field_name": field.field_name,
        "identity_context": identity_context,
        "evidence": [
            {"id": item.evidence_id, "locator": item.locator, "excerpt": item.excerpt}
            for item in evidence
        ],
    }
    input_digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode()
    ).hexdigest()
    existing = session.scalar(
        select(AIClarificationProposal).where(
            AIClarificationProposal.normalized_field_candidate_id == field.id,
            AIClarificationProposal.provider == provider.provider_name,
            AIClarificationProposal.model == provider.model_name,
            AIClarificationProposal.prompt_version == PROMPT_VERSION,
            AIClarificationProposal.input_digest == input_digest,
        )
    )
    if existing is not None:
        return existing

    result = provider.propose(
        field_name=field.field_name,
        identity_context=identity_context,
        evidence=evidence,
    )
    assessments = _validate_output(result.output, evidence)
    proposal = AIClarificationProposal(
        clarification_id=f"CMS-CLARIFY-{uuid4().hex}",
        normalized_field_candidate=field,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        input_digest=input_digest,
        outcome=ClarificationOutcome(result.output.outcome),
        proposed_value=result.output.proposed_value,
        summary=result.output.summary,
        provider_response_id=result.response_id,
        created_by=created_by,
    )
    for item in evidence:
        assessment = assessments[item.evidence_id]
        proposal.evidence.append(
            AIClarificationEvidence(
                evidence_key=item.evidence_id,
                source_text_segment=item.segment,
                source_revision=item.revision,
                locator=item.locator,
                excerpt=item.excerpt,
                relation=ClarificationEvidenceRelation(assessment.relation),
                explanation=assessment.explanation,
            )
        )
    session.add(proposal)
    session.flush()
    return proposal


def get_normalized_field(
    session: Session, field_candidate_id: str
) -> NormalizedFieldCandidate | None:
    return session.scalar(
        select(NormalizedFieldCandidate)
        .where(NormalizedFieldCandidate.field_candidate_id == field_candidate_id)
        .options(
            selectinload(NormalizedFieldCandidate.measure_candidate)
            .selectinload(NormalizedMeasureCandidate.normalization)
            .selectinload(SourceNormalization.source_extraction)
            .selectinload(SourceExtraction.source_revision),
            selectinload(NormalizedFieldCandidate.measure_candidate)
            .selectinload(NormalizedMeasureCandidate.matched_measure_version)
            .selectinload(MeasureVersion.measure),
            selectinload(NormalizedFieldCandidate.clarifications).selectinload(
                AIClarificationProposal.evidence
            ),
        )
    )
