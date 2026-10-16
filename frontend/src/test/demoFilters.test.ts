import { describe, expect, it } from "vitest";

import { demoMeasures } from "../features/measures/demo/fixtures";
import {
  comparisonStatus,
  defaultDemoFilters,
  filterDemoMeasures,
} from "../features/measures/demo/filters";

describe("fictional measure adapter", () => {
  it("filters by status, field, review, and year", () => {
    const results = filterDemoMeasures(demoMeasures, {
      ...defaultDemoFilters,
      status: "modified",
      field: "Exclusions",
      review: "Needs re-verification",
      year: "2026",
    });

    expect(results.map((measure) => measure.id)).toEqual(["PV-103"]);
  });

  it("searches only public-facing identity text", () => {
    expect(
      filterDemoMeasures(demoMeasures, { ...defaultDemoFilters, q: "statin" }).map(
        (measure) => measure.id,
      ),
    ).toEqual(["IM-108"]);
    expect(
      filterDemoMeasures(demoMeasures, { ...defaultDemoFilters, q: "re-verification" }),
    ).toEqual([]);
  });

  it("keeps unavailable data separate from membership removal", () => {
    const measure = demoMeasures.find((candidate) => candidate.id === "FL-107");

    expect(measure?.status).toBe("unchanged");
    expect(measure?.specs.find((field) => field.name === "Eligibility")?.unavailable).toBe(true);
  });

  it("reverses membership direction for a reversed year comparison", () => {
    const measure = demoMeasures.find((candidate) => candidate.id === "FU-104");
    if (!measure) throw new Error("Missing fictional fixture FU-104");

    expect(
      comparisonStatus(measure, { ...defaultDemoFilters, from: "2026", to: "2025" }),
    ).toBe("removed");
  });
});
