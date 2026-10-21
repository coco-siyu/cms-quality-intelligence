import { Link, useParams } from "@tanstack/react-router";
import { ArrowLeft, ExternalLink, LockKeyhole } from "lucide-react";

import { ErrorState, LoadingState } from "../components/cms/shared";
import { useAdminMeasure, useAdminSession } from "../features/admin/api";
import { AdminWorkspacePage } from "./AdminWorkspacePage";

const collectionLabels: Record<string, string> = {
  program_roster: "Program roster",
  ecqm: "eCQM",
  mips_cqm: "MIPS CQM",
  medicare_cqm: "Medicare CQM",
  cahps_survey: "CAHPS for MIPS Survey",
  administrative_claims: "Administrative claims",
};

export function AdminMeasureDetailPage() {
  const { measureId } = useParams({ from: "/admin/measures/$measureId" });
  const session = useAdminSession();
  const detail = useAdminMeasure(measureId, Boolean(session.data?.authenticated));

  if (session.isPending) return <LoadingState label="Checking administrator access…" />;
  if (session.isError) return <ErrorState message={session.error.message} onRetry={() => void session.refetch()} />;
  if (!session.data.authenticated) return <AdminWorkspacePage />;
  if (detail.isPending) return <LoadingState label="Loading source-backed review candidates…" />;
  if (detail.isError) return <ErrorState message={detail.error.message} onRetry={() => void detail.refetch()} />;

  return (
    <div className="visual-page admin-detail-page">
      <Link to="/admin" className="admin-back-link"><ArrowLeft aria-hidden="true" /> Review queue</Link>
      <header className="admin-detail-header">
        <div>
          <p className="admin-measure-id">Measure {detail.data.measure_id}</p>
          <h1>{detail.data.name}</h1>
          <p>{detail.data.description}</p>
        </div>
        <span className="private-state"><LockKeyhole aria-hidden="true" /> Private draft</span>
      </header>

      <section className="admin-membership-strip" aria-label="Program membership">
        {detail.data.memberships.map((membership) => (
          <article key={`${membership.program}-${membership.performance_year}`}>
            <span>PY{membership.performance_year}</span>
            <strong>{membership.is_program_member ? "Included" : "Not included"}</strong>
            <small>{membership.publication_state}</small>
          </article>
        ))}
      </section>

      <section className="admin-variants">
        <div className="admin-variants-heading">
          <p className="card-kicker">Versioned source review</p>
          <h2>Specification variants</h2>
          <p>Candidate values are source-derived but not verified until a reviewer decides them.</p>
        </div>
        {detail.data.versions.map((version) => (
          <article className="admin-variant-card surface-card" key={version.version_id}>
            <header>
              <div>
                <span>PY{version.performance_year}</span>
                <h3>{collectionLabels[version.collection_type] ?? version.collection_type}</h3>
                <p>{version.specification_identifier ?? "Roster membership record"}</p>
              </div>
              <div className="variant-status">
                <span>{version.publication_state}</span>
                <small>{version.candidates.length} field candidates</small>
              </div>
            </header>
            {version.candidates.length > 0 ? (
              <div className="candidate-list">
                {version.candidates.map((candidate) => (
                  <details key={candidate.review_item_id}>
                    <summary>
                      <span>{candidate.field_name.replaceAll("_", " ")}</span>
                      <code>{candidate.review_decision}</code>
                    </summary>
                    <div className="candidate-body">
                      <p>{candidate.candidate_value}</p>
                      <dl>
                        <div><dt>Evidence locator</dt><dd>{candidate.evidence_locator}</dd></div>
                        <div><dt>Extraction status</dt><dd>{candidate.extraction_status}</dd></div>
                        <div><dt>Source revision</dt><dd>{candidate.source_revision_id}</dd></div>
                      </dl>
                      <a href={candidate.official_url} target="_blank" rel="noreferrer">
                        {candidate.source_title} <ExternalLink aria-hidden="true" />
                      </a>
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <p className="variant-no-candidates">No field candidates are attached to this roster record.</p>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
