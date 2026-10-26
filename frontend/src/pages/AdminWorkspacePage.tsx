import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, Database, FileCheck2, LogOut, Search, ShieldCheck } from "lucide-react";

import { ErrorState, LoadingState } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  useAdminLogin,
  useAdminLogout,
  useAdminMeasures,
  useAdminReviewSummary,
  useAdminSession,
} from "../features/admin/api";
import { parseAdminSearch } from "../features/admin/search";

function LoginPanel({ configured }: { configured: boolean }) {
  const login = useAdminLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate({ username, password });
  }

  return (
    <div className="admin-gate surface-card">
      <div className="admin-gate-mark"><ShieldCheck aria-hidden="true" /></div>
      <p className="page-eyebrow">Protected workspace</p>
      <h1>Review desk</h1>
      <p>
        Inspect source-backed CMS drafts before anything is eligible for the public API.
        This workspace never substitutes prototype fixtures.
      </p>
      {!configured ? (
        <div className="admin-setup-note" role="status">
          <AlertTriangle aria-hidden="true" />
          <span>
            <strong>Administrator access is not configured.</strong>
            <small>
              From the backend directory, run <code>uv run python -m
              app.commands.generate_admin_credentials</code>, copy the generated values into
              the root <code>.env</code>, then restart FastAPI.
            </small>
          </span>
        </div>
      ) : (
        <form className="admin-login-form" onSubmit={submit}>
          <label>
            <span>Username</span>
            <Input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            <span>Password</span>
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {login.isError && <p className="admin-form-error" role="alert">{login.error.message}</p>}
          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Enter review workspace"}
          </Button>
        </form>
      )}
    </div>
  );
}

function ReviewWorkspace({ username }: { username: string }) {
  const rawSearch = useSearch({ from: "/admin" });
  const search = parseAdminSearch(rawSearch);
  const navigate = useNavigate({ from: "/admin" });
  const summary = useAdminReviewSummary(true);
  const measures = useAdminMeasures(search.q ?? "", true);
  const logout = useAdminLogout();

  if (summary.isPending || measures.isPending) {
    return <LoadingState label="Opening the protected review workspace…" />;
  }
  if (summary.isError) {
    return <ErrorState message={summary.error.message} onRetry={() => void summary.refetch()} />;
  }
  if (measures.isError) {
    return <ErrorState message={measures.error.message} onRetry={() => void measures.refetch()} />;
  }

  const metrics = [
    ["Measures in review", summary.data.private_measures],
    ["Draft variants", summary.data.draft_versions],
    ["Pending fields", summary.data.pending_candidates],
    ["Reviewed fields", summary.data.decided_candidates],
    ["Source revisions", summary.data.source_revisions],
  ] as const;

  return (
    <div className="visual-page admin-page">
      <header className="admin-page-header">
        <div>
          <p className="page-eyebrow">Protected CMS evidence workspace</p>
          <h1>Review desk</h1>
          <p>
            Each source-derived field remains private until its own review and publication
            steps are complete.
          </p>
        </div>
        <div className="admin-identity">
          <span>Signed in as <strong>{username}</strong></span>
          <Button variant="outline" asChild>
            <Link to="/admin/sources"><Database aria-hidden="true" /> Sources</Link>
          </Button>
          <Button variant="outline" onClick={() => logout.mutate()} disabled={logout.isPending}>
            <LogOut aria-hidden="true" /> Sign out
          </Button>
        </div>
      </header>

      {summary.data.newer_revision_flags > 0 && (
        <div className="admin-warning" role="alert">
          <AlertTriangle aria-hidden="true" />
          {summary.data.newer_revision_flags} draft variants have newer source revisions and cannot
          be approved yet.
        </div>
      )}

      <section className="admin-metrics" aria-label="Review queue summary">
        {metrics.map(([label, value]) => (
          <article key={label} className="surface-card">
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </section>

      <section className="admin-queue surface-card">
        <div className="admin-queue-heading">
          <div>
            <p className="card-kicker">Human verification queue</p>
            <h2>Staged measures</h2>
          </div>
          <label className="admin-search">
            <Search aria-hidden="true" />
            <span className="sr-only">Search staged measures</span>
            <Input
              type="search"
              value={search.q ?? ""}
              placeholder="Search ID or measure name"
              onChange={(event) =>
                void navigate({ search: event.target.value ? { q: event.target.value } : {}, replace: true })
              }
            />
          </label>
        </div>

        <div className="admin-table-scroll">
          <table className="admin-review-table">
            <thead>
              <tr>
                <th>Measure</th>
                <th>Performance years</th>
                <th>Draft variants</th>
                <th>Field review</th>
                <th>Sources</th>
                <th><span className="sr-only">Open</span></th>
              </tr>
            </thead>
            <tbody>
              {measures.data.items.map((measure) => (
                <tr key={measure.measure_id}>
                  <td>
                    <span className="admin-measure-id">{measure.measure_id}</span>
                    <strong>{measure.name}</strong>
                  </td>
                  <td>{measure.performance_years.map((year) => `PY${year}`).join(" · ")}</td>
                  <td>{measure.draft_versions}</td>
                  <td>
                    <span className="review-count pending">{measure.pending_candidates} pending</span>
                    <small>{measure.decided_candidates} reviewed</small>
                  </td>
                  <td>{measure.source_documents}</td>
                  <td>
                    <Link
                      to="/admin/measures/$measureId"
                      params={{ measureId: measure.measure_id }}
                      aria-label={`Review ${measure.measure_id}`}
                    >
                      <ArrowRight aria-hidden="true" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {measures.data.items.length === 0 && (
          <div className="empty-state">No measures in review match this search.</div>
        )}
        <p className="admin-boundary-note">
          <FileCheck2 aria-hidden="true" /> Review decisions stay private and retain their audit
          history. Publishing remains a separate follow-on action.
        </p>
      </section>
    </div>
  );
}

export function AdminWorkspacePage() {
  const session = useAdminSession();
  if (session.isPending) return <LoadingState label="Checking administrator access…" />;
  if (session.isError) return <ErrorState message={session.error.message} onRetry={() => void session.refetch()} />;
  if (!session.data.authenticated) return <LoginPanel configured={session.data.configured} />;
  return <ReviewWorkspace username={session.data.username ?? "administrator"} />;
}
