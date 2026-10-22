import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClientError } from "../measures/api/client";
import type { ApiErrorPayload } from "../measures/api/types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type AdminSession = {
  configured: boolean;
  authenticated: boolean;
  username: string | null;
};

export type AdminReviewSummary = {
  private_measures: number;
  draft_versions: number;
  pending_candidates: number;
  decided_candidates: number;
  source_revisions: number;
  newer_revision_flags: number;
};

export type AdminMeasureSummary = {
  measure_id: string;
  name: string;
  description: string;
  performance_years: number[];
  draft_versions: number;
  pending_candidates: number;
  decided_candidates: number;
  source_documents: number;
  newer_revision_detected: boolean;
  last_source_check_at: string | null;
};

export type AdminMeasurePage = {
  items: AdminMeasureSummary[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};

export type AdminFieldCandidate = {
  review_item_id: string;
  field_name: string;
  candidate_value: string;
  extraction_status: string;
  evidence_locator: string;
  review_decision: "pending" | "approve" | "needs_revision" | "not_applicable";
  reviewed_value: string | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  source_id: string;
  source_revision_id: string;
  source_title: string;
  official_url: string;
  source_content_hash: string;
  review_history: AdminCandidateReview[];
};

export type AdminCandidateReview = {
  decision: "approve" | "needs_revision" | "not_applicable";
  reviewed_value: string | null;
  reviewer_name: string;
  reviewed_at: string;
  reviewer_notes: string | null;
};

export type AdminCandidateDecision = {
  decision: AdminCandidateReview["decision"];
  reviewed_value: string | null;
  reviewer_notes: string | null;
};

export type AdminMeasureDetail = {
  measure_id: string;
  name: string;
  description: string;
  is_public: false;
  memberships: {
    performance_year: number;
    program: string;
    is_program_member: boolean;
    publication_state: "draft" | "published" | "withdrawn";
    verified_at: string | null;
  }[];
  versions: {
    version_id: string;
    performance_year: number;
    program: string;
    collection_type: string;
    specification_identifier: string | null;
    publication_state: "draft" | "published" | "withdrawn";
    verification_status: string;
    newer_revision_detected: boolean;
    last_source_check_at: string;
    candidates: AdminFieldCandidate[];
  }[];
};

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch (error) {
    throw new ApiClientError(
      0,
      error instanceof Error ? error.message : "The API could not be reached.",
    );
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => undefined)) as ApiErrorPayload | undefined;
    throw new ApiClientError(
      response.status,
      payload?.message ?? `API request failed (${response.status}).`,
      payload,
    );
  }
  return (await response.json()) as T;
}

export const adminApi = {
  session(signal?: AbortSignal) {
    return adminRequest<AdminSession>("/api/admin/session", { signal });
  },
  login(username: string, password: string) {
    return adminRequest<AdminSession>("/api/admin/session", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  logout() {
    return adminRequest<AdminSession>("/api/admin/session", { method: "DELETE" });
  },
  summary(signal?: AbortSignal) {
    return adminRequest<AdminReviewSummary>("/api/admin/review-summary", { signal });
  },
  measures(q: string, signal?: AbortSignal) {
    const search = new URLSearchParams({ page_size: "100" });
    if (q.trim()) search.set("q", q.trim());
    return adminRequest<AdminMeasurePage>(`/api/admin/measures?${search}`, { signal });
  },
  measure(measureId: string, signal?: AbortSignal) {
    return adminRequest<AdminMeasureDetail>(
      `/api/admin/measures/${encodeURIComponent(measureId)}`,
      { signal },
    );
  },
  reviewCandidate(reviewItemId: string, decision: AdminCandidateDecision) {
    return adminRequest<AdminFieldCandidate>(
      `/api/admin/review-items/${encodeURIComponent(reviewItemId)}`,
      {
        method: "PATCH",
        headers: { "X-CMSQI-Admin-Action": "review-decision" },
        body: JSON.stringify(decision),
      },
    );
  },
};

export function useAdminSession() {
  return useQuery({
    queryKey: ["admin-session"],
    queryFn: ({ signal }) => adminApi.session(signal),
    retry: false,
  });
}

export function useAdminLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      adminApi.login(username, password),
    onSuccess: (session) => queryClient.setQueryData(["admin-session"], session),
  });
}

export function useAdminLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => adminApi.logout(),
    onSuccess: (session) => {
      queryClient.setQueryData(["admin-session"], session);
      queryClient.removeQueries({ queryKey: ["admin-review"] });
    },
  });
}

export function useAdminReviewSummary(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-review", "summary"],
    queryFn: ({ signal }) => adminApi.summary(signal),
    enabled,
    retry: false,
  });
}

export function useAdminMeasures(q: string, enabled: boolean) {
  return useQuery({
    queryKey: ["admin-review", "measures", q],
    queryFn: ({ signal }) => adminApi.measures(q, signal),
    enabled,
    retry: false,
  });
}

export function useAdminMeasure(measureId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["admin-review", "measure", measureId],
    queryFn: ({ signal }) => adminApi.measure(measureId, signal),
    enabled: enabled && Boolean(measureId),
    retry: false,
  });
}

export function useAdminCandidateReview(measureId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reviewItemId,
      decision,
    }: {
      reviewItemId: string;
      decision: AdminCandidateDecision;
    }) => adminApi.reviewCandidate(reviewItemId, decision),
    onSuccess: (updatedCandidate) => {
      queryClient.setQueryData<AdminMeasureDetail>(
        ["admin-review", "measure", measureId],
        (detail) =>
          detail
            ? {
                ...detail,
                versions: detail.versions.map((version) => ({
                  ...version,
                  candidates: version.candidates.map((candidate) =>
                    candidate.review_item_id === updatedCandidate.review_item_id
                      ? updatedCandidate
                      : candidate,
                  ),
                })),
              }
            : detail,
      );
      void queryClient.invalidateQueries({ queryKey: ["admin-review", "summary"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-review", "measures"] });
    },
  });
}
