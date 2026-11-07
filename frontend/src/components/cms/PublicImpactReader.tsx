import { useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";

import type {
  ChangeFieldEvidence,
  ImpactStatement,
  PublicImpactExplanation,
} from "../../features/measures/api/types";
import { formatApiDate } from "../../features/measures/api/adapters";
import { Button } from "../ui/button";

type ImpactRole = "analyst" | "manager";

function CitationLinks({
  statement,
  evidence,
}: {
  statement: Pick<ImpactStatement, "citations">;
  evidence: Map<string, ChangeFieldEvidence>;
}) {
  return (
    <span className="impact-citations" aria-label="Statement sources">
      {statement.citations.map((citation) => {
        const source = evidence.get(citation.evidence_id);
        return source ? (
          <a
            key={citation.evidence_id}
            href={source.official_url}
            target="_blank"
            rel="noreferrer"
            title={`${source.document_title} — ${source.locator ?? "source excerpt"}`}
          >
            {citation.evidence_id} <ExternalLink size={10} />
          </a>
        ) : null;
      })}
    </span>
  );
}

function StatementList({
  title,
  statements,
  evidence,
}: {
  title: string;
  statements: ImpactStatement[];
  evidence: Map<string, ChangeFieldEvidence>;
}) {
  return (
    <section className="impact-reading-section">
      <p className="quiet-label">{title}</p>
      <ol>
        {statements.map((statement, index) => (
          <li key={`${title}-${index}`}>
            <span>{statement.statement}</span>
            <CitationLinks statement={statement} evidence={evidence} />
          </li>
        ))}
      </ol>
    </section>
  );
}

export function PublicImpactReader({ explanation }: { explanation: PublicImpactExplanation }) {
  const [role, setRole] = useState<ImpactRole>("analyst");
  const evidence = new Map(explanation.evidence.map((item) => [item.evidence_id, item]));
  const roleContent =
    role === "analyst"
      ? {
          label: "Data Analyst",
          introduction: "Technical and validation considerations",
          sections: [
            ["Technical implications", explanation.output.data_analyst.technical_implications],
            ["Validation considerations", explanation.output.data_analyst.validation_considerations],
          ] as const,
        }
      : {
          label: "ACO Quality Manager",
          introduction: "Operational and coordination considerations",
          sections: [
            ["Operational implications", explanation.output.aco_quality_manager.operational_implications],
            ["Coordination considerations", explanation.output.aco_quality_manager.coordination_considerations],
          ] as const,
        };

  return (
    <section className="impact-section public-impact-reader">
      <header className="impact-reader-header">
        <div>
          <p className="card-kicker">Human-reviewed interpretation</p>
          <h2>Potential impact, by role</h2>
        </div>
        <div className="impact-approval-mark">
          <ShieldCheck size={16} />
          <span>Approved {formatApiDate(explanation.approved_at)}</span>
        </div>
      </header>

      <div className="impact-summary-sheet">
        <p className="quiet-label">What changed</p>
        <p className="impact-summary-copy">{explanation.output.plain_language_summary.statement}</p>
        <CitationLinks statement={explanation.output.plain_language_summary} evidence={evidence} />
      </div>

      <div className="impact-reader-grid">
        <aside className="impact-role-index">
          <p className="quiet-label">Perspective</p>
          <div className="role-switch impact-role-switch" role="group" aria-label="Explanation role">
            <Button
              variant="ghost"
              aria-pressed={role === "analyst"}
              onClick={() => setRole("analyst")}
            >
              Data Analyst
            </Button>
            <Button
              variant="ghost"
              aria-pressed={role === "manager"}
              onClick={() => setRole("manager")}
            >
              ACO Quality Manager
            </Button>
          </div>
          <p className="impact-boundary-note">Possible implications—not CMS policy.</p>
        </aside>

        <article className="impact-reading-pane" aria-live="polite">
          <div className="impact-reading-heading">
            <p className="quiet-label">Selected perspective</p>
            <h3>{roleContent.label}</h3>
            <p>{roleContent.introduction}</p>
          </div>
          {roleContent.sections.map(([title, statements]) => (
            <StatementList key={title} title={title} statements={[...statements]} evidence={evidence} />
          ))}
        </article>
      </div>

      {explanation.output.uncertainty_caveats.length > 0 && (
        <section className="impact-caveats" aria-label="Uncertainty notes">
          <p className="quiet-label">Uncertainty notes</p>
          {explanation.output.uncertainty_caveats.map((caveat, index) => (
            <p key={index}>
              {caveat.statement} <CitationLinks statement={caveat} evidence={evidence} />
            </p>
          ))}
        </section>
      )}
    </section>
  );
}
