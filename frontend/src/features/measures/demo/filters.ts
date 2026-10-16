import type { DemoFilters, DemoMeasure, DemoStatus } from "./types";

export const defaultDemoFilters: DemoFilters = {
  q: "",
  status: "all",
  year: "all",
  field: "all",
  review: "all",
  from: "2025",
  to: "2026",
};

const allowedYears = new Set(["2025", "2026"]);

export function parseDemoFilters(value: Record<string, unknown>): DemoFilters {
  const stringValue = (key: keyof DemoFilters, fallback: string) =>
    typeof value[key] === "string" ? value[key] : fallback;

  const from = stringValue("from", defaultDemoFilters.from);
  const to = stringValue("to", defaultDemoFilters.to);

  return {
    q: stringValue("q", "").slice(0, 200),
    status: stringValue("status", "all"),
    year: stringValue("year", "all"),
    field: stringValue("field", "all"),
    review: stringValue("review", "all"),
    from: allowedYears.has(from) ? from : defaultDemoFilters.from,
    to: allowedYears.has(to) ? to : defaultDemoFilters.to,
  };
}

export function comparisonStatus(measure: DemoMeasure, filters: DemoFilters): DemoStatus {
  if (filters.from === filters.to) return "unchanged";
  if (filters.from === "2026") {
    if (measure.status === "added") return "removed";
    if (measure.status === "removed") return "added";
  }
  return measure.status;
}

export function filterDemoMeasures(measures: DemoMeasure[], filters: DemoFilters) {
  const query = filters.q.trim().toLowerCase();

  return measures.filter((measure) => {
    const searchableText = [measure.id, measure.name, measure.description].join(" ").toLowerCase();
    return (
      (filters.from !== filters.to || measure.years.includes(Number(filters.from))) &&
      (filters.status === "all" || comparisonStatus(measure, filters) === filters.status) &&
      (filters.year === "all" || measure.years.includes(Number(filters.year))) &&
      (filters.field === "all" ||
        measure.field === filters.field ||
        (filters.field === "Eligibility" && measure.unavailable)) &&
      (filters.review === "all" || measure.review === filters.review) &&
      (!query || searchableText.includes(query))
    );
  });
}
