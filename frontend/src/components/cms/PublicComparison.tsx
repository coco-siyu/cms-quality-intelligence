import { ArrowRight, ChevronDown, ExternalLink, FileText } from "lucide-react";

import type {
  ChangeField,
  ChangeFieldEvidence,
  FieldAvailability,
  PublicChangeRecord,
} from "../../features/measures/api/types";
import { labelField } from "../../features/measures/api/adapters";
import { StatusMark } from "./shared";

function availabilityLabel(availability: FieldAvailability) {
  if (availability === "available") return "Approved";
  if (availability === "unavailable") return "Unavailable";
  return "Unresolved";
}

function fieldValue(
  field: ChangeField["field"],
  value: string | null,
  availability: FieldAvailability,
) {
  if (availability === "unavailable") {
    return "This field is explicitly unavailable in the approved public record.";
  }
  if (availability === "unresolved") {
    return "The approved evidence does not resolve this field.";
  }
  if (
    field === "measure_set" &&
    value?.startsWith("Member of the PY") &&
    value.includes("MSSP APP Plus quality measure set")
  ) {
    return "Included in the APP Plus measure set.";
  }
  return value ?? "No approved public value was supplied.";
}

function conciseSourceLabel(evidence: ChangeFieldEvidence) {
  if (/physician fee schedule final rule/i.test(evidence.document_title)) {
    const year = evidence.document_title.match(/(?:CY|Calendar Year(?: \(CY\))?)\s*(20\d{2})/i)?.[1];
    return year ? `${year} Final Rule` : "CMS Final Rule";
  }
  if (/quality performance standard/i.test(evidence.document_title)) {
    const year = evidence.document_title.match(/performance year\s*(20\d{2})/i)?.[1];
    return year ? `PY${year} Measure Table` : "CMS Measure Table";
  }
  return evidence.document_title;
}

function EvidenceExcerpt({ evidence }: { evidence: ChangeFieldEvidence }) {
  return (
    <article className="comparison-evidence-excerpt">
      <FileText aria-hidden="true" />
      <div>
        <blockquote>{evidence.excerpt}</blockquote>
        <p>
          <span>{evidence.locator ?? "Locator unavailable"}</span>
          <a
            href={evidence.official_url}
            target="_blank"
            rel="noreferrer"
            title={evidence.document_title}
          >
            {conciseSourceLabel(evidence)} <ExternalLink aria-hidden="true" />
          </a>
        </p>
      </div>
    </article>
  );
}

function ValueSheet({
  year,
  value,
  availability,
  evidence,
  side,
  field,
}: {
  year: number;
  value: string | null;
  availability: FieldAvailability;
  evidence: ChangeFieldEvidence[];
  side: "from" | "to";
  field: ChangeField["field"];
}) {
  const sourceLabel = `${evidence.length} official ${evidence.length === 1 ? "source" : "sources"}`;

  return (
    <section className={`comparison-value-sheet comparison-value-${side}`}>
      <header>
        <strong>PY{year}</strong>
        <span>{availabilityLabel(availability)}</span>
      </header>
      <p className={availability === "available" ? "" : "unavailable-text"}>
        {fieldValue(field, value, availability)}
      </p>
      {evidence.length > 0 && (
        <details className="comparison-evidence-details">
          <summary>
            <span>{sourceLabel}</span>
            <span className="comparison-evidence-toggle">
              <span className="comparison-evidence-toggle-closed">View evidence</span>
              <span className="comparison-evidence-toggle-open">Hide evidence</span>
              <ChevronDown aria-hidden="true" />
            </span>
          </summary>
          <div className="comparison-evidence-stack" aria-label={`PY${year} evidence`}>
            {evidence.map((reference) => (
              <EvidenceExcerpt
                key={`${reference.evidence_id}-${reference.side}`}
                evidence={reference}
              />
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function ComparisonField({
  field,
  fromYear,
  toYear,
}: {
  field: ChangeField;
  fromYear: number;
  toYear: number;
}) {
  const fromEvidence = field.evidence.filter((reference) => reference.side === "from_version");
  const toEvidence = field.evidence.filter((reference) => reference.side === "to_version");
  const contextEvidence = field.evidence.filter((reference) => reference.side === "context");

  return (
    <article className={`public-comparison-field comparison-status-${field.status}`}>
      <header className="public-comparison-field-label">
        <span>{labelField(field.field)}</span>
        <StatusMark status={field.status} />
      </header>
      <div className="comparison-sheet-pair">
        <ValueSheet
          year={fromYear}
          value={field.from_value}
          availability={field.from_availability}
          evidence={fromEvidence}
          side="from"
          field={field.field}
        />
        <ArrowRight className="comparison-direction" aria-hidden="true" />
        <ValueSheet
          year={toYear}
          value={field.to_value}
          availability={field.to_availability}
          evidence={toEvidence}
          side="to"
          field={field.field}
        />
      </div>
      {contextEvidence.length > 0 && (
        <div className="comparison-context-evidence">
          <span>Additional context</span>
          {contextEvidence.map((reference) => (
            <EvidenceExcerpt key={`${reference.evidence_id}-${reference.side}`} evidence={reference} />
          ))}
        </div>
      )}
    </article>
  );
}

export function PublicComparison({ comparison }: { comparison: PublicChangeRecord }) {
  return (
    <section className="public-comparison" aria-labelledby="public-comparison-title">
      <header className="public-comparison-heading">
        <div>
          <p className="card-kicker">Approved field comparison</p>
          <h2 id="public-comparison-title">
            PY{comparison.from_year} <ArrowRight aria-hidden="true" /> PY{comparison.to_year}
          </h2>
        </div>
        <StatusMark status={comparison.status} badge />
      </header>
      <dl className="comparison-identity-strip">
        <div>
          <dt>Program</dt>
          <dd>{comparison.program}</dd>
        </div>
        <div>
          <dt>Comparison record</dt>
          <dd>{comparison.collection_type.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{comparison.evidence_status}</dd>
        </div>
      </dl>
      <div className="public-comparison-fields">
        {comparison.fields.map((field) => (
          <ComparisonField
            key={field.field}
            field={field}
            fromYear={comparison.from_year}
            toYear={comparison.to_year}
          />
        ))}
      </div>
    </section>
  );
}
