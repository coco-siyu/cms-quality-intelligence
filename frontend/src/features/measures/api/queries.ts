import { useQuery } from "@tanstack/react-query";

import type { DemoFilters } from "../demo/types";
import { filtersToApiFilters, filtersToApiParameters } from "./adapters";
import { changeApi, measureApi } from "./client";

export function useApiMeasureList(filters: DemoFilters) {
  const parameters = filtersToApiParameters(filters);
  return useQuery({
    queryKey: ["public-measures", parameters],
    queryFn: ({ signal }) => measureApi.list(parameters, signal),
  });
}

export function useApiMeasure(measureId: string, filters: DemoFilters) {
  return useQuery({
    queryKey: ["public-measure", measureId, filters.from, filters.to],
    queryFn: ({ signal }) =>
      measureApi.get(measureId, Number(filters.from), Number(filters.to), signal),
    enabled: Boolean(measureId),
  });
}

export function useApiMeasureNavigation(measureId: string, filters: DemoFilters) {
  const parameters = filtersToApiFilters(filters);
  return useQuery({
    queryKey: ["public-measure-navigation", measureId, parameters],
    queryFn: ({ signal }) => measureApi.navigation(measureId, parameters, signal),
    enabled: Boolean(measureId),
    retry: false,
  });
}

export function usePerformanceYears(enabled = true) {
  return useQuery({
    queryKey: ["performance-years"],
    queryFn: ({ signal }) => measureApi.performanceYears(signal),
    enabled,
  });
}

export function useApiChanges(fromYear: number, toYear: number) {
  const parameters = {
    from_year: fromYear,
    to_year: toYear,
    collection_type: "program_roster" as const,
    page_size: 100,
  };
  return useQuery({
    queryKey: ["public-changes", parameters],
    queryFn: ({ signal }) => changeApi.list(parameters, signal),
    enabled: fromYear !== toYear,
  });
}

export function useApiMeasureComparison(
  measureId: string,
  program: string,
  fromYear: number,
  toYear: number,
) {
  // The current public measure summary and dashboard projection is explicitly
  // roster-scoped. Detailed collection variants stay private until the public
  // contract exposes a variant selector and identity on measure versions.
  const parameters = {
    program,
    collection_type: "program_roster" as const,
    from_year: fromYear,
    to_year: toYear,
  };
  return useQuery({
    queryKey: ["public-measure-comparison", measureId, parameters],
    queryFn: ({ signal }) => changeApi.get(measureId, parameters, signal),
    enabled: Boolean(measureId && program) && fromYear !== toYear,
    retry: false,
  });
}

export function useApiImpactExplanation(
  measureId: string,
  program: string,
  fromYear: number,
  toYear: number,
) {
  const parameters = {
    program,
    collection_type: "program_roster" as const,
    from_year: fromYear,
    to_year: toYear,
  };
  return useQuery({
    queryKey: ["public-impact-explanation", measureId, parameters],
    queryFn: ({ signal }) => changeApi.impact(measureId, parameters, signal),
    enabled: Boolean(measureId && program) && fromYear !== toYear,
    retry: false,
  });
}
