import type {
  ApiErrorPayload,
  PerformanceYearList,
  PublicMeasureDetail,
  PublicMeasureNavigation,
  PublicMeasurePage,
} from "./types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiClientError extends Error {
  readonly status: number;
  readonly payload?: ApiErrorPayload;

  constructor(status: number, message: string, payload?: ApiErrorPayload) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.payload = payload;
  }
}

async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    throw new ApiClientError(
      0,
      error instanceof Error ? error.message : "The API could not be reached.",
    );
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => undefined)) as ApiErrorPayload | undefined;
    throw new ApiClientError(response.status, payload?.message ?? `API request failed (${response.status}).`, payload);
  }
  return (await response.json()) as T;
}

export type MeasureListParameters = {
  q?: string;
  performance_year?: number;
  from_year?: number;
  to_year?: number;
  change_status?: string;
  affected_field?: string;
  verification_status?: string;
  page?: number;
  page_size?: number;
};

function queryString(parameters: MeasureListParameters): string {
  const search = new URLSearchParams();
  Object.entries(parameters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const measureApi = {
  performanceYears(signal?: AbortSignal) {
    return apiGet<PerformanceYearList>("/api/performance-years", signal);
  },
  list(parameters: MeasureListParameters, signal?: AbortSignal) {
    return apiGet<PublicMeasurePage>(`/api/measures${queryString(parameters)}`, signal);
  },
  get(measureId: string, fromYear: number, toYear: number, signal?: AbortSignal) {
    const parameters = queryString({ from_year: fromYear, to_year: toYear });
    return apiGet<PublicMeasureDetail>(
      `/api/measures/${encodeURIComponent(measureId)}${parameters}`,
      signal,
    );
  },
  navigation(
    measureId: string,
    parameters: MeasureListParameters,
    signal?: AbortSignal,
  ) {
    return apiGet<PublicMeasureNavigation>(
      `/api/measures/${encodeURIComponent(measureId)}/navigation${queryString(parameters)}`,
      signal,
    );
  },
};
