export type DemoStatus = "added" | "removed" | "modified" | "unchanged";

export type DemoReviewStatus = "Approved" | "In review" | "Needs re-verification";

export type DemoFilters = {
  q: string;
  status: string;
  year: string;
  field: string;
  review: string;
  from: string;
  to: string;
};

export type DemoSpecField = {
  name: string;
  before: string;
  after: string;
  removed?: string;
  added?: string;
  unavailable?: boolean;
};

export type DemoMeasure = {
  id: string;
  name: string;
  status: DemoStatus;
  field: string;
  years: number[];
  review: DemoReviewStatus;
  verified: string;
  description: string;
  specs: DemoSpecField[];
  unavailable?: boolean;
};

export type DemoNewsItem = {
  id: string;
  status: DemoStatus;
  title: string;
  body: string;
  date: string;
  applies: string;
};
