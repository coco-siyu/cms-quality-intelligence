"""Provider-independent contract for role-specific impact explanations.

Task 34 defines the validated output shape only. It does not call a model,
persist a draft, approve content, or expose an explanation publicly.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain import ChangeEvidenceSide
from app.services.semantic_classification import SemanticEvidenceExcerpt


class ImpactExplanationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ImpactStatementType(StrEnum):
    SOURCE_FACT = "source_fact"
    POSSIBLE_IMPACT = "possible_impact"


class ImpactCitation(BaseModel):
    """Reference to an immutable evidence excerpt supplied by the server."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1, max_length=120)


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
            "Impact explanations may discuss SQL considerations but must not contain "
            "production-ready SQL."
        )
    return value


class ImpactStatement(BaseModel):
    """One evidence-linked fact or explicitly qualified possible impact."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str = Field(min_length=1, max_length=2_000)
    statement_type: ImpactStatementType
    citations: list[ImpactCitation] = Field(min_length=1, max_length=12)

    _validate_statement = field_validator("statement")(_reject_production_sql)

    @model_validator(mode="after")
    def reject_duplicate_citations(self) -> "ImpactStatement":
        citation_ids = [citation.evidence_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("Each statement may cite an evidence ID at most once.")
        return self


class DataAnalystImpact(BaseModel):
    """Technical considerations for data and reporting implementation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    technical_implications: list[ImpactStatement] = Field(min_length=1, max_length=8)
    validation_considerations: list[ImpactStatement] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def require_possible_impacts(self) -> "DataAnalystImpact":
        statements = self.technical_implications + self.validation_considerations
        if any(item.statement_type != ImpactStatementType.POSSIBLE_IMPACT for item in statements):
            raise ValueError("Data Analyst implications must be labeled as possible impacts.")
        return self


class ACOQualityManagerImpact(BaseModel):
    """Operational considerations for quality and performance teams."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    operational_implications: list[ImpactStatement] = Field(min_length=1, max_length=8)
    coordination_considerations: list[ImpactStatement] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def require_possible_impacts(self) -> "ACOQualityManagerImpact":
        statements = self.operational_implications + self.coordination_considerations
        if any(item.statement_type != ImpactStatementType.POSSIBLE_IMPACT for item in statements):
            raise ValueError(
                "ACO Quality Manager implications must be labeled as possible impacts."
            )
        return self


class ImpactUncertaintyCaveat(BaseModel):
    """A bounded caveat; citations may be empty when evidence is missing."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str = Field(min_length=1, max_length=1_000)
    citations: list[ImpactCitation] = Field(max_length=12)

    _validate_statement = field_validator("statement")(_reject_production_sql)

    @model_validator(mode="after")
    def reject_duplicate_citations(self) -> "ImpactUncertaintyCaveat":
        citation_ids = [citation.evidence_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("Each caveat may cite an evidence ID at most once.")
        return self


class ImpactExplanationOutput(BaseModel):
    """Strict paired output for one approved, evidence-backed comparison."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    plain_language_summary: ImpactStatement
    data_analyst: DataAnalystImpact
    aco_quality_manager: ACOQualityManagerImpact
    uncertainty_caveats: list[ImpactUncertaintyCaveat] = Field(max_length=8)

    @model_validator(mode="after")
    def require_factual_summary(self) -> "ImpactExplanationOutput":
        if self.plain_language_summary.statement_type != ImpactStatementType.SOURCE_FACT:
            raise ValueError("The plain-language summary must be labeled as a source fact.")
        return self


def _all_statements(output: ImpactExplanationOutput) -> list[ImpactStatement]:
    return [
        output.plain_language_summary,
        *output.data_analyst.technical_implications,
        *output.data_analyst.validation_considerations,
        *output.aco_quality_manager.operational_implications,
        *output.aco_quality_manager.coordination_considerations,
    ]


def validate_impact_citations(
    output: ImpactExplanationOutput,
    supplied_evidence: list[SemanticEvidenceExcerpt],
) -> ImpactExplanationOutput:
    """Ensure every returned citation belongs to the exact supplied evidence set.

    The factual summary must cite both compared performance-year sides. Role
    implications may cite either or both sides, but every implication still has
    at least one citation through its schema.
    """

    evidence_by_id = {item.evidence_id: item for item in supplied_evidence}
    if len(evidence_by_id) != len(supplied_evidence):
        raise ImpactExplanationValidationError(
            "impact_evidence_duplicate",
            "The supplied evidence set contains duplicate evidence IDs.",
        )

    citation_ids = {
        citation.evidence_id
        for statement in _all_statements(output)
        for citation in statement.citations
    }
    citation_ids.update(
        citation.evidence_id
        for caveat in output.uncertainty_caveats
        for citation in caveat.citations
    )
    unsupported = citation_ids.difference(evidence_by_id)
    if unsupported:
        raise ImpactExplanationValidationError(
            "impact_citation_unsupported",
            "The explanation cites evidence that was not supplied.",
        )

    summary_sides = {
        evidence_by_id[citation.evidence_id].side
        for citation in output.plain_language_summary.citations
    }
    required_sides = {
        ChangeEvidenceSide.FROM_VERSION,
        ChangeEvidenceSide.TO_VERSION,
    }
    if not required_sides.issubset(summary_sides):
        raise ImpactExplanationValidationError(
            "impact_summary_citation_coverage_incomplete",
            "The factual summary must cite evidence from both year versions.",
        )
    return output
