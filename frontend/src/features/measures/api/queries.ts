import { useQuery } from "@tanstack/react-query";

import type { DemoFilters } from "../demo/types";
import { filtersToApiFilters, filtersToApiParameters } from "./adapters";
import { measureApi } from "./client";

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
