import argparse
import csv
import html
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCES_DIR = REPOSITORY_ROOT / "docs/sources"
SEED_PATH = REPOSITORY_ROOT / "backend/app/data/cms_app_plus_2025_2026.seed.json"
DEFAULT_OUTPUT = SOURCES_DIR / "field-review-crosswalk.csv"

FIELD_NAMES = (
    "measure_title",
    "specification_identifier",
    "description",
    "measure_type",
    "scoring_direction",
    "population_or_denominator",
    "numerator_or_outcome",
    "exclusions",
    "denominator_exceptions",
    "data_collection",
    "risk_adjustment",
)

OUTPUT_FIELDS = (
    "review_item_id",
    "variant_id",
    "quality_id",
    "performance_year",
    "collection_type",
    "specification_identifier",
    "field_name",
    "candidate_value",
    "source_id",
    "source_sha256",
    "evidence_locator",
    "extraction_status",
    "review_decision",
    "reviewer_name",
    "reviewed_at",
    "reviewer_notes",
)

CLINICAL_STOPS = (
    r"^\s*INSTRUCTIONS:\s*$",
    r"^\s*DESCRIPTION:\s*$",
    r"^\s*DENOMINATOR:\s*$",
    r"^\s*DENOMINATOR EXCLUSIONS:\s*$",
    r"^\s*NUMERATOR:\s*$",
    r"^\s*Numerator Instructions:\s*$",
    r"^\s*Numerator Options:\s*$",
    r"^\s*RATIONALE:\s*$",
)


@dataclass(frozen=True)
class Candidate:
    value: str
    locator: str
    status: str = "candidate_extracted_needs_sme_review"


def _csv_rows(filename: str) -> list[dict[str, str]]:
    with (SOURCES_DIR / filename).open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file))


def _normalize(value: str, *, limit: int = 1800) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    shortened = value[:limit].rsplit(" ", maxsplit=1)[0]
    return f"{shortened} [excerpt truncated; inspect cited source section]"


def _page_number(pages: list[str], pattern: str) -> int | None:
    for index, page in enumerate(pages, start=1):
        if re.search(pattern, page, flags=re.IGNORECASE | re.MULTILINE):
            return index
    return None


def _section(
    pages: list[str],
    start_pattern: str,
    stop_patterns: tuple[str, ...],
    *,
    label: str,
) -> Candidate | None:
    for start_index, page in enumerate(pages):
        match = re.search(start_pattern, page, flags=re.IGNORECASE | re.MULTILINE)
        if match is None:
            continue

        parts: list[str] = []
        end_index = start_index
        remaining = page[match.end() :]
        for page_index in range(start_index, len(pages)):
            chunk = remaining if page_index == start_index else pages[page_index]
            stop_positions = []
            for pattern in stop_patterns:
                stop_match = re.search(
                    pattern,
                    chunk,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
                if stop_match is not None:
                    stop_positions.append(stop_match.start())
            if stop_positions:
                parts.append(chunk[: min(stop_positions)])
                end_index = page_index
                break
            parts.append(chunk)
            end_index = page_index
            if page_index - start_index >= 2:
                break

        value = _normalize(" ".join(parts))
        if not value:
            return None
        locator = f"PDF page {start_index + 1}"
        if end_index > start_index:
            locator = f"PDF pages {start_index + 1}-{end_index + 1}"
        return Candidate(value=value, locator=f"{locator}; {label}")
    return None


def _literal(value: str, locator: str) -> Candidate:
    return Candidate(value=value, locator=locator)


def _manual(locator: str, reason: str) -> Candidate:
    return Candidate(
        value=reason,
        locator=locator,
        status="manual_extraction_or_policy_review_required",
    )


def _not_applicable(locator: str, reason: str) -> Candidate:
    return Candidate(
        value=reason,
        locator=locator,
        status="not_applicable_candidate_needs_sme_confirmation",
    )


def _pdf_pages(pdf_path: Path) -> list[str]:
    executable = shutil.which("pdftotext")
    if executable is None:
        raise RuntimeError("pdftotext is required to prepare the review crosswalk.")
    result = subprocess.run(  # noqa: S603 - fixed executable and local source path
        [executable, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.split("\f")


def _variant_pages(
    variant: dict[str, str],
    revisions: dict[str, dict[str, str]],
) -> list[str] | None:
    revision = revisions[variant["source_id"]]
    source_path = REPOSITORY_ROOT / revision["cache_path"]
    locator = variant["locator"]
    if locator.startswith("ZIP member: "):
        member_name = locator.removeprefix("ZIP member: ")
        with zipfile.ZipFile(source_path) as archive:
            pdf_bytes = archive.read(member_name)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary_pdf:
            temporary_pdf.write(pdf_bytes)
            temporary_pdf.flush()
            return _pdf_pages(Path(temporary_pdf.name))
    if source_path.suffix.lower() == ".pdf":
        return _pdf_pages(source_path)
    return None


def _ecqm_candidates(
    pages: list[str],
    title: str,
    variant: dict[str, str],
) -> dict[str, Candidate]:
    labels = (
        r"^\s*Description\s+",
        r"^\s*Measure Scoring\s+",
        r"^\s*Measure Type\s+",
        r"^\s*Stratification\s+",
        r"^\s*Risk Adjustment\s+",
        r"^\s*Rationale\s+",
        r"^\s*Clinical\s+",
        r"^\s*Improvement\s+",
        r"^\s*Guidance\s+",
        r"^\s*Initial Population\s+",
        r"^\s*Denominator\s+",
        r"^\s*Numerator\s+",
        r"^\s*Telehealth Eligible\s+",
    )
    result = {
        "measure_title": _literal(title, "PDF page 1; measure title"),
        "specification_identifier": _literal(
            variant["specification_identifier"],
            "PDF page 1; CMS eCQM ID",
        ),
    }
    mapping = {
        "description": r"^\s*Description\s+",
        "measure_type": r"^\s*Measure Type\s+",
        "scoring_direction": r"^\s*Improvement\s+(?:Notation\s+)?",
        "population_or_denominator": r"^\s*Initial Population\s+",
        "numerator_or_outcome": r"^\s*Numerator\s+",
        "exclusions": r"^\s*Denominator\s+Exclusions\s+",
        "denominator_exceptions": r"^\s*Denominator\s+Exceptions\s+",
        "risk_adjustment": r"^\s*Risk Adjustment\s+",
    }
    for field_name, start in mapping.items():
        candidate = _section(pages, start, labels, label=field_name.replace("_", " "))
        if candidate is not None:
            result[field_name] = candidate
    result["data_collection"] = _literal(
        "Electronic clinical quality measure (eCQM)",
        "PDF page 1; General eCQM Information",
    )
    return result


def _clinical_candidates(
    pages: list[str],
    title: str,
    variant: dict[str, str],
) -> dict[str, Candidate]:
    result = {
        "measure_title": _literal(title, "PDF page 1; measure heading"),
        "specification_identifier": _literal(
            variant["specification_identifier"],
            "PDF page 1; Quality ID and collection type",
        ),
        "data_collection": _literal(
            variant["collection_type"],
            "PDF page 1; collection type",
        ),
    }
    mapping = {
        "description": (r"^\s*DESCRIPTION:\s*", CLINICAL_STOPS),
        "measure_type": (r"^\s*MEASURE TYPE:\s*", CLINICAL_STOPS),
        "population_or_denominator": (
            r"^\s*DENOMINATOR:\s*",
            CLINICAL_STOPS + (r"^\s*Denominator Criteria",),
        ),
        "numerator_or_outcome": (
            r"^\s*NUMERATOR:\s*",
            CLINICAL_STOPS,
        ),
        "exclusions": (
            r"^\s*DENOMINATOR EXCLUSIONS:\s*",
            CLINICAL_STOPS + (r"^\s*Reference Coding",),
        ),
    }
    for field_name, (start, stops) in mapping.items():
        candidate = _section(pages, start, stops, label=field_name.replace("_", " "))
        if candidate is not None:
            result[field_name] = candidate

    inverse_page = _page_number(pages, r"INVERSE MEASURE:\s*LOWER SCORE")
    if inverse_page is not None:
        result["scoring_direction"] = _literal(
            "Inverse measure: lower score indicates better quality.",
            f"PDF page {inverse_page}; inverse-measure notice",
        )
    else:
        result["scoring_direction"] = _manual(
            "PDF; scoring guidance",
            "No normalized scoring-direction statement was extracted.",
        )

    exception = _section(
        pages,
        r"Patients with a Documented Reason for not Screening for Depression "
        r"\(Denominator Exceptions\)\s*[–-]\s*",
        (r"^\s*Numerator Instructions:\s*$",),
        label="denominator exceptions",
    )
    result["denominator_exceptions"] = exception or _manual(
        "PDF; denominator-exception sections",
        "No explicit denominator-exception section was normalized.",
    )
    result["risk_adjustment"] = _manual(
        "PDF; risk-adjustment guidance",
        "Risk-adjustment applicability requires collection-specific review.",
    )
    return result


def _admin_candidates(
    pages: list[str],
    title: str,
    variant: dict[str, str],
) -> dict[str, Candidate]:
    section_stops = tuple(rf"^\s*{letter}\.\s+" for letter in "ABCDEFGHIJ")
    result = {
        "measure_title": _literal(title, "PDF section A; Measure Name"),
        "specification_identifier": _literal(
            variant["specification_identifier"],
            "PDF cover and section A",
        ),
        "measure_type": _literal(
            "Administrative claims outcome measure",
            "PDF cover and sections D-G",
        ),
        "scoring_direction": _manual(
            "PDF methodology sections",
            "Scoring direction was not normalized from the measure information form.",
        ),
        "denominator_exceptions": _not_applicable(
            "PDF measure information form",
            "The administrative measure uses population exclusions rather than a "
            "clinical denominator-exception field.",
        ),
    }
    mapping = {
        "description": r"^\s*B\.\s+Measure Description\s*$",
        "numerator_or_outcome": r"^\s*D\.\s+Measure Outcome(?: \(Numerator\))?\s*$",
        "population_or_denominator": r"^\s*E\.\s+Population Measured \(Denominator\)\s*$",
        "exclusions": r"^\s*F\.\s+Exclusions\s*$",
        "data_collection": (
            r"^\s*G\.\s+Data Collection Approach and Measure"
            r"(?: Collection| Calculation)?\s*$"
        ),
    }
    for field_name, start in mapping.items():
        candidate = _section(
            pages,
            start,
            section_stops,
            label=field_name.replace("_", " "),
        )
        if candidate is not None:
            result[field_name] = candidate
    risk = _section(
        pages,
        r"^\s*Risk adjustment(?: and measure construction)?:?\s*$",
        (r"^\s*[A-Z]\.\s+", r"^\s*I\.\s+"),
        label="risk adjustment",
    )
    result["risk_adjustment"] = risk or _manual(
        "PDF section H; methodology",
        "Risk-adjustment detail requires manual review of the methodology section.",
    )
    return result


def _cahps_candidates(
    pages: list[str],
    title: str,
    variant: dict[str, str],
) -> dict[str, Candidate]:
    survey_description = _section(
        pages,
        r"^What is the CAHPS for MIPS Survey\?\s*$",
        (r"^Reporting Criteria",),
        label="survey description and summary measures",
    )
    sample = _section(
        pages,
        r"^Q: How will CMS select a sample of patients",
        (r"^Q:",),
        label="patient sample eligibility",
    )
    collection = _section(
        pages,
        r"^\s*Administering the CAHPS for MIPS Survey\s*$",
        (r"^\s*Frequently Asked Questions\s*$",),
        label="survey administration and data collection",
    )
    return {
        "measure_title": _literal(title, "PDF pages 1-3; survey title"),
        "specification_identifier": _literal(
            variant["specification_identifier"],
            "PDF pages 1-3; CAHPS for MIPS Survey",
        ),
        "description": survey_description
        or _manual("PDF page 3", "Survey description requires manual extraction."),
        "measure_type": _literal(
            "Patient experience survey measure",
            "PDF pages 3-4; reporting criteria",
        ),
        "scoring_direction": _manual(
            "PDF scoring guidance",
            "Survey scoring direction requires review of the applicable CAHPS scoring methodology.",
        ),
        "population_or_denominator": sample
        or _manual("PDF FAQ; sample eligibility", "Survey sample rules require manual extraction."),
        "numerator_or_outcome": _not_applicable(
            "PDF pages 3-4; survey model",
            "CAHPS reports summary survey measures rather than one clinical numerator.",
        ),
        "exclusions": _manual(
            "PDF FAQ; sample eligibility",
            "Sampling exclusions require survey-methodology review.",
        ),
        "denominator_exceptions": _not_applicable(
            "PDF; survey model",
            "A clinical denominator-exception field is not used by this survey specification.",
        ),
        "data_collection": collection
        or _manual(
            "PDF survey administration",
            "Survey collection method requires manual extraction.",
        ),
        "risk_adjustment": _manual(
            "PDF scoring methodology",
            "Risk-adjustment applicability requires CAHPS methodology review.",
        ),
    }


def _html_ecqm_candidates(
    source_path: Path,
    title: str,
    variant: dict[str, str],
) -> dict[str, Candidate]:
    markup = source_path.read_text(encoding="utf-8")
    cells: dict[str, str] = {}
    pattern = re.compile(
        r'<th[^>]*>.*?<span class="td_label">(?P<label>.*?)</span>.*?</th>'
        r"\s*<td[^>]*>(?P<value>.*?)(?=<th|</tr>)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(markup):
        label = _normalize(html.unescape(re.sub(r"<[^>]+>", " ", match["label"])))
        value = _normalize(html.unescape(re.sub(r"<[^>]+>", " ", match["value"])))
        if label and value and label not in cells:
            cells[label] = value

    base_locator = "HTML measure-information table"
    result = {
        "measure_title": _literal(cells.get("eCQM Title", title), f"{base_locator}; eCQM Title"),
        "specification_identifier": _literal(
            variant["specification_identifier"],
            f"{base_locator}; CMS ID and eCQM Version Number",
        ),
        "data_collection": _literal("eCQM", f"{base_locator}; specification format"),
    }
    mappings = {
        "description": ("Description",),
        "measure_type": ("Measure Type",),
        "scoring_direction": ("Improvement Notation", "Measure Scoring"),
        "population_or_denominator": ("Denominator", "Initial Population"),
        "numerator_or_outcome": ("Numerator",),
        "exclusions": ("Denominator Exclusions",),
        "denominator_exceptions": ("Denominator Exceptions",),
        "risk_adjustment": ("Risk Adjustment",),
    }
    for field_name, labels in mappings.items():
        for label in labels:
            if label in cells:
                result[field_name] = _literal(cells[label], f"{base_locator}; {label}")
                break
    return result


def build_rows() -> list[dict[str, str]]:
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    titles = {measure["measure_id"]: measure["name"] for measure in seed["measures"]}
    variants = _csv_rows("collection-variants.csv")
    revisions = {row["source_id"]: row for row in _csv_rows("source-revisions.csv")}
    rows: list[dict[str, str]] = []

    for variant in variants:
        collection_type = variant["collection_type"]
        title = titles[variant["quality_id"]]
        source_path = REPOSITORY_ROOT / revisions[variant["source_id"]]["cache_path"]
        if collection_type == "eCQM" and source_path.suffix.lower() in {".html", ".htm"}:
            candidates = _html_ecqm_candidates(source_path, title, variant)
            pages = None
        else:
            pages = _variant_pages(variant, revisions)
        if pages is None and collection_type != "eCQM":
            raise ValueError(f"Unsupported non-PDF source for {variant['variant_id']}")
        elif collection_type == "eCQM":
            if pages is not None:
                candidates = _ecqm_candidates(pages, title, variant)
        elif collection_type in {"MIPS CQM", "Medicare CQM"}:
            candidates = _clinical_candidates(pages, title, variant)
        elif collection_type == "Administrative Claims":
            candidates = _admin_candidates(pages, title, variant)
        elif collection_type == "CAHPS for MIPS Survey":
            candidates = _cahps_candidates(pages, title, variant)
        else:
            raise ValueError(f"Unsupported collection type: {collection_type}")

        for field_name in FIELD_NAMES:
            candidate = candidates.get(field_name) or _manual(
                variant["locator"],
                "No candidate value was normalized from the frozen source.",
            )
            rows.append(
                {
                    "review_item_id": f"{variant['variant_id']}::{field_name}",
                    "variant_id": variant["variant_id"],
                    "quality_id": variant["quality_id"],
                    "performance_year": variant["performance_year"],
                    "collection_type": collection_type,
                    "specification_identifier": variant["specification_identifier"],
                    "field_name": field_name,
                    "candidate_value": candidate.value,
                    "source_id": variant["source_id"],
                    "source_sha256": revisions[variant["source_id"]]["sha256"],
                    "evidence_locator": candidate.locator,
                    "extraction_status": candidate.status,
                    "review_decision": "pending",
                    "reviewer_name": "",
                    "reviewed_at": "",
                    "reviewer_notes": "",
                }
            )
    return rows


def write_crosswalk(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file, fieldnames=OUTPUT_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a non-public field review crosswalk from frozen CMS sources."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = build_rows()
    write_crosswalk(rows, args.output)
    print(f"Prepared {len(rows)} pending review items at {args.output}")
    print("No database records were changed and no candidate fields were published.")


if __name__ == "__main__":
    main()
