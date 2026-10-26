import { useState } from "react";
import { AlertTriangle, ArrowUpRight, ChevronDown, ExternalLink, FileText } from "lucide-react";

import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../ui/dialog";
import type { DemoMeasure } from "../../features/measures/demo/types";
import { DemoBadge, SectionTitle } from "./shared";

export function EvidencePanel({ measure }: { measure: DemoMeasure }) {
  const [openYear, setOpenYear] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<number[]>([]);

  const excerpt = (year: number) => {
    const field = measure.specs.find((candidate) => candidate.name === measure.field) ?? measure.specs[0];
    if (!field) return "No fictional excerpt is available.";
    return year === 2025 ? field.before : field.after;
  };

  return (
    <section className="evidence-section">
      <SectionTitle>Source evidence</SectionTitle>
      <p className="section-subtext">Fictional excerpts · Not verified CMS source material</p>
      <div className="evidence-grid">
        {measure.years.map((year) => (
          <article
            key={year}
            className={`evidence-item ${
              year === 2026 && measure.review === "Needs re-verification"
                ? "evidence-warning"
                : ""
            }`}
          >
            <div className="evidence-heading">
              <FileText size={16} />
              <strong>PY{year}</strong>
              {year === 2026 && measure.review === "Needs re-verification" && (
                <span className="warning-text">Needs re-verification</span>
              )}
            </div>
            <p className="evidence-citation">
              Fictional PY{year} APP Plus prototype specification
              <br />
              Section 4.2 · {measure.id}
            </p>
            <blockquote>{excerpt(year)}</blockquote>
            <Button
              variant="link"
              className="evidence-expand"
              aria-expanded={expanded.includes(year)}
              onClick={() =>
                setExpanded((current) =>
                  current.includes(year)
                    ? current.filter((candidate) => candidate !== year)
                    : [...current, year],
                )
              }
            >
              Revision details <ChevronDown size={14} />
            </Button>
            {expanded.includes(year) && (
              <dl className="revision-details">
                <dt>Prototype revision reference</dt>
                <dd className="font-mono">DEMO-{measure.id}-{year}-v1</dd>
                <dt>Fictional publication date</dt>
                <dd>{year === 2025 ? "Nov 2024" : "Sep 2026"}</dd>
                <dt>Prototype source check</dt>
                <dd>Oct 14, 2026</dd>
              </dl>
            )}
            <Button variant="link" className="evidence-open" onClick={() => setOpenYear(year)}>
              View evidence <ArrowUpRight size={14} />
            </Button>
          </article>
        ))}
        {measure.specs.some((field) => field.unavailable) && (
          <article className="evidence-item missing-evidence">
            <strong>PY2026, eligibility</strong>
            <h3>No excerpt found</h3>
            <p>
              The fictional document does not include eligibility text. It is unavailable,
              not a confirmed change.
            </p>
          </article>
        )}
      </div>

      <Dialog open={openYear !== null} onOpenChange={(open) => !open && setOpenYear(null)}>
        <DialogContent className="evidence-dialog">
          <DemoBadge />
          <DialogTitle className="font-display">PY{openYear} source evidence</DialogTitle>
          <DialogDescription>
            Fictional APP Plus prototype · {measure.id} · {measure.name}
          </DialogDescription>
          <blockquote>{excerpt(openYear ?? 2026)}</blockquote>
          <div className="warning-callout">
            <AlertTriangle size={18} />
            <p>
              This excerpt is fictional prototype content, not verified regulatory evidence. No
              official document has been ingested.
            </p>
          </div>
          <dl className="revision-details">
            <dt>Prototype revision reference</dt>
            <dd className="font-mono">DEMO-{measure.id}-{openYear}-v1</dd>
            <dt>Prototype source check</dt>
            <dd>Oct 14, 2026</dd>
          </dl>
          <Button asChild variant="outline">
            <a href="https://qpp.cms.gov/mips/explore-measures" target="_blank" rel="noreferrer">
              Browse official CMS measures <ExternalLink size={14} />
            </a>
          </Button>
        </DialogContent>
      </Dialog>
    </section>
  );
}
