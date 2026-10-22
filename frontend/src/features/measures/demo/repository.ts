import { demoMeasures, demoNews } from "./fixtures";
import { filterDemoMeasures } from "./filters";
import type { DemoFilters, DemoMeasure, DemoNewsItem } from "./types";

export type DemoMeasureListResult = {
  items: DemoMeasure[];
  total: number;
};

export interface DemoMeasureRepository {
  list(filters: DemoFilters): Promise<DemoMeasureListResult>;
  get(measureId: string): Promise<DemoMeasure | undefined>;
  news(): Promise<DemoNewsItem[]>;
}

export const mockMeasureRepository: DemoMeasureRepository = {
  async list(filters) {
    return {
      items: filterDemoMeasures(demoMeasures, filters),
      total: demoMeasures.length,
    };
  },
  async get(measureId) {
    return demoMeasures.find((measure) => measure.id === measureId);
  },
  async news() {
    return demoNews;
  },
};
