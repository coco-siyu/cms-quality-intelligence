"""Provider-independent contract for evidence-backed impact task proposals."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain import ReviewRole
from app.services.semantic_classification import SemanticEvidenceExcerpt


class ImpactTaskProposalValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_SQL_PATTERNS = (
    re.compile(r"\bSELECT\b.+\bFROM\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+[^\s]+\s+SET\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bCREATE\s+(?:TABLE|VIEW|PROCEDURE)\b", re.IGNORECASE),
)


def _reject_production_sql(value: str) -> str:
    if "```" in value or any(pattern.search(value) for pattern in _SQL_PATTERNS):
        raise ValueError(
            "Task proposals may mention data validation but must not contain production-ready SQL."
        )
    return value


class ImpactTaskCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1, max_length=120)


class ImpactTaskProposal(BaseModel):
    """One optional follow-up action supported by official comparison evidence."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: ReviewRole
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    citations: list[ImpactTaskCitation] = Field(min_length=1, max_length=12)

    _validate_title = field_validator("title")(_reject_production_sql)
    _validate_description = field_validator("description")(_reject_production_sql)

    @model_validator(mode="after")
    def reject_duplicate_citations(self) -> "ImpactTaskProposal":
        citation_ids = [citation.evidence_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("Each task proposal may cite an evidence ID at most once.")
        return self


class ImpactTaskProposalOutput(BaseModel):
    """Strict generated batch kept private until individual admin acceptance."""

    model_config = ConfigDict(extra="forbid")

    proposals: list[ImpactTaskProposal] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def reject_duplicate_proposals(self) -> "ImpactTaskProposalOutput":
        identities = [
            (proposal.role.value, " ".join(proposal.title.lower().split()))
            for proposal in self.proposals
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("Task proposal titles must be unique within each role.")
        return self


def validate_task_proposal_citations(
    output: ImpactTaskProposalOutput,
    supplied_evidence: list[SemanticEvidenceExcerpt],
) -> ImpactTaskProposalOutput:
    evidence_ids = [item.evidence_id for item in supplied_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ImpactTaskProposalValidationError(
            "task_proposal_evidence_duplicate",
            "The supplied evidence set contains duplicate evidence IDs.",
        )

    unsupported = {
        citation.evidence_id for proposal in output.proposals for citation in proposal.citations
    }.difference(evidence_ids)
    if unsupported:
        raise ImpactTaskProposalValidationError(
            "task_proposal_citation_unsupported",
            "A task proposal cites evidence that was not supplied.",
        )
    return output
