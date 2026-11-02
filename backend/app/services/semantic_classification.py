"""Structured contract for evidence-bounded semantic field classification.

Task 26 defines and validates the provider-independent data shape only. It does
not call a model, persist a judgment, approve a change, or mutate the
deterministic comparison that supplied the field difference.
"""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.domain import ChangeEvidenceSide, SemanticClassification


class SemanticClassificationValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SemanticEvidenceExcerpt(BaseModel):
    """One immutable excerpt supplied to the future semantic classifier."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1, max_length=120)
    source_revision_id: str = Field(min_length=1, max_length=180)
    document_title: str = Field(min_length=1, max_length=500)
    official_url: HttpUrl
    locator: str = Field(min_length=1, max_length=500)
    excerpt: str = Field(min_length=1, max_length=3_000)
    side: ChangeEvidenceSide

    @field_validator("official_url")
    @classmethod
    def require_https_source(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("Official evidence URLs must use HTTPS.")
        return value


class SemanticCitation(BaseModel):
    """Reference to an evidence ID from the supplied excerpt set."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1, max_length=120)


class SemanticClassificationOutput(BaseModel):
    """Strict model output for one deterministic field difference."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    classification: SemanticClassification
    reasoning_summary: str = Field(min_length=1, max_length=4_000)
    citations: list[SemanticCitation] = Field(max_length=12)
    uncertainty_summary: str | None = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_resolution_state(self) -> "SemanticClassificationOutput":
        citation_ids = [citation.evidence_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("Each evidence ID may be cited at most once.")

        if self.classification == SemanticClassification.NEEDS_REVIEW:
            if self.uncertainty_summary is None:
                raise ValueError("needs_review requires an uncertainty summary.")
        else:
            if not self.citations:
                raise ValueError("A conclusive classification requires evidence citations.")
            if self.uncertainty_summary is not None:
                raise ValueError(
                    "Unresolved uncertainty requires the needs_review classification."
                )
        return self


def validate_semantic_citations(
    output: SemanticClassificationOutput,
    supplied_evidence: list[SemanticEvidenceExcerpt],
) -> SemanticClassificationOutput:
    """Validate citations against the exact evidence set supplied to a provider.

    Conclusive classifications require cited evidence from both compared year
    sides. A needs-review result may have no citations when the supplied evidence
    is insufficient, but any citations it does include must still be supported.
    """

    evidence_by_id = {item.evidence_id: item for item in supplied_evidence}
    if len(evidence_by_id) != len(supplied_evidence):
        raise SemanticClassificationValidationError(
            "semantic_evidence_duplicate",
            "The supplied evidence set contains duplicate evidence IDs.",
        )

    citation_ids = {citation.evidence_id for citation in output.citations}
    unsupported = citation_ids.difference(evidence_by_id)
    if unsupported:
        raise SemanticClassificationValidationError(
            "semantic_citation_unsupported",
            "The classification cites evidence that was not supplied.",
        )

    if output.classification != SemanticClassification.NEEDS_REVIEW:
        cited_sides = {evidence_by_id[evidence_id].side for evidence_id in citation_ids}
        required_sides = {
            ChangeEvidenceSide.FROM_VERSION,
            ChangeEvidenceSide.TO_VERSION,
        }
        if not required_sides.issubset(cited_sides):
            raise SemanticClassificationValidationError(
                "semantic_citation_coverage_incomplete",
                "A conclusive classification must cite evidence from both year versions.",
            )
    return output
