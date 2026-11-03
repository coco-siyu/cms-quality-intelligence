import { ArrowRight, ExternalLink, FileText } from "lucide-react";

import type {
  ChangeField,
  ChangeFieldEvidence,
  FieldAvailability,
  PublicChangeRecord,
} from "../../features/measures/api/types";
import { labelField } from "../../features/measures/api/adapters";
import { StatusMark } from "./shared";

function availabilityLabel(availability: FieldAvailability) {
  if (availability === "available") return "Approved value";
  if (availability === "unavailable") return "Explicitly unavailable";
  return "Unresolved evidence";
}

function fieldValue(value: string | null, availability: FieldAvailability) {
  if (availability === "unavailable") {
    return "This field is explicitly unavailable in the approved public record.";
  }
  if (availability === "unresolved") {
    return "The approved evidence does not resolve this field.";
  }
  return value ?? "No approved public value was supplied.";
}

function EvidenceExcerpt({ evidence }: { evidence: ChangeFieldEvidence }) {
  return (
    <article className="comparison-evidence-excerpt">
      <FileText aria-hidden="true" />
      <div>
        <blockquote>{evidence.excerpt}</blockquote>
        <p>
          <span>{evidence.locator ?? "Locator unavailable"}</span>
          <a href={evidence.official_url} target="_blank" rel="noreferrer">
            {evidence.document_title} <ExternalLink aria-hidden="true" />
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
}: {
  year: number;
  value: string | null;
  availability: FieldAvailability;
  evidence: ChangeFieldEvidence[];
  side: "from" | "to";
}) {
  return (
    <section className={`comparison-value-sheet comparison-value-${side}`}>
      <header>
        <strong>PY{year}</strong>
        <span>{availabilityLabel(availability)}</span>
      </header>
      <p className={availability === "available" ? "" : "unavailable-text"}>
        {fieldValue(value, availability)}
      </p>
      {evidence.length > 0 && (
        <div className="comparison-evidence-stack" aria-label={`PY${year} evidence`}>
          {evidence.map((reference) => (
            <EvidenceExcerpt key={`${reference.evidence_id}-${reference.side}`} evidence={reference} />
          ))}
        </div>
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
        />
        <ArrowRight className="comparison-direction" aria-hidden="true" />
        <ValueSheet
          year={toYear}
          value={field.to_value}
          availability={field.to_availability}
          evidence={toEvidence}
          side="to"
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
