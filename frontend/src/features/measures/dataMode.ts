export type DataMode = "api" | "demo";

export function getDataMode(): DataMode {
  return import.meta.env.VITE_DATA_MODE === "demo" ? "demo" : "api";
}
