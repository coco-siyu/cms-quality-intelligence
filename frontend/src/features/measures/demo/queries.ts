import { useQuery } from "@tanstack/react-query";

import { mockMeasureRepository } from "./repository";
import type { DemoFilters } from "./types";

export function useDemoMeasureList(filters: DemoFilters) {
  return useQuery({
    queryKey: ["demo-measures", filters],
    queryFn: () => mockMeasureRepository.list(filters),
  });
}

export function useDemoMeasure(measureId: string) {
  return useQuery({
    queryKey: ["demo-measure", measureId],
    queryFn: () => mockMeasureRepository.get(measureId),
  });
}

export function useDemoNews() {
  return useQuery({
    queryKey: ["demo-news"],
    queryFn: () => mockMeasureRepository.news(),
  });
}
