import { CircleHelp, Equal, Minus, Pencil, Plus } from "lucide-react";

import type { DemoStatus } from "../../features/measures/demo/types";

export const statusLabels: Record<DemoStatus, string> = {
  added: "Added",
  removed: "Removed",
  modified: "Modified",
  unchanged: "Unchanged",
  unknown: "Unknown",
};

export const statusIcons = {
  added: Plus,
  removed: Minus,
  modified: Pencil,
  unchanged: Equal,
  unknown: CircleHelp,
};
