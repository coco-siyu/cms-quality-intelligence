import { ChevronDown } from "lucide-react";

import { Button } from "../ui/button";
import type { DemoStatus } from "../../features/measures/demo/types";
import { statusIcons, statusLabels } from "./statusPresentation";

export function StatusMark({ status, badge = false }: { status: DemoStatus; badge?: boolean }) {
  const Icon = statusIcons[status];
  return (
    <span className={`status-mark status-${status} ${badge ? "status-badge" : ""}`}>
      <Icon size={13} />
      {statusLabels[status]}
    </span>
  );
}

export function DemoBadge() {
  return <span className="demo-badge">Fictional data</span>;
}

export function SectionTitle({
  children,
  demo = true,
}: {
  children: React.ReactNode;
  demo?: boolean;
}) {
  return (
    <div className="section-title">
      <h2>{children}</h2>
      {demo && <DemoBadge />}
    </div>
  );
}

export function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-select">
      <span>{label}</span>
      <span className="select-wrap">
        <select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown size={13} />
      </span>
    </label>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="loading-state" role="status">
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="empty-state api-error-state" role="alert">
      <h2>Data unavailable</h2>
      <p>{message}</p>
      <p className="quiet-label">No fictional records were substituted for this API failure.</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function TextButton(props: React.ComponentProps<typeof Button>) {
  return <Button variant="link" {...props} />;
}
