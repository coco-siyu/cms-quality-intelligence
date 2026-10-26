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
  source_excerpt: string | null;
  extraction_status: string;
  evidence_locator: string;
  review_decision: "pending" | "approve" | "needs_revision" | "not_applicable";
  reviewed_value: string | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  reviewer_notes: string | null;
  publication_state: "draft" | "published" | "withdrawn";
  publication_eligibility:
    | "eligible"
    | "published"
    | "not_approved"
    | "missing_source_excerpt"
    | "unsupported_field"
    | "stale_source"
    | "unverified_source"
    | "unverified_membership"
    | "field_conflict";
  publication_blocker: string | null;
  published_field: string | null;
  published_at: string | null;
  published_by: string | null;
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

export type AdminMeasureVersion = {
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
};

export type AdminMeasureDetail = {
  measure_id: string;
  name: string;
  description: string;
  is_public: boolean;
  memberships: {
    performance_year: number;
    program: string;
    is_program_member: boolean;
    publication_state: "draft" | "published" | "withdrawn";
    verified_at: string | null;
  }[];
  versions: AdminMeasureVersion[];
};

export type AdminSourceExtraction = {
  extraction_id: string;
  sequence: number;
  status: "extracted" | "manual_review" | "failed";
  page_count: number | null;
  segment_count: number;
  error: string | null;
  extractor_version: string;
  forced: boolean;
  extracted_at: string;
  created_by: string;
};

export type AdminSourceRevision = {
  revision_id: string;
  revision_number: number;
  content_hash: string;
  source_url: string | null;
  final_url: string | null;
  http_status: number | null;
  mime_type: string | null;
  byte_length: number | null;
  publication_date: string | null;
  retrieved_at: string;
  last_source_check_at: string;
  extraction: AdminSourceExtraction | null;
};

export type AdminSourceCheck = {
  check_id: string;
  outcome: "new_revision" | "unchanged" | "reprocessed" | "failed";
  checked_at: string;
  requested_url: string;
  final_url: string | null;
  http_status: number | null;
  mime_type: string | null;
  byte_length: number | null;
  content_hash: string | null;
  error: string | null;
  forced: boolean;
  checked_by: string;
  revision_id: string | null;
  extraction_id: string | null;
};

export type AdminSourceSummary = {
  source_id: string;
  title: string;
  official_url: string;
  source_format: "html" | "pdf";
  is_active: boolean;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  deactivated_at: string | null;
  revision_count: number;
  latest_revision: AdminSourceRevision | null;
  latest_check: AdminSourceCheck | null;
};

export type AdminSourceDetail = AdminSourceSummary & {
  revisions: AdminSourceRevision[];
  checks: AdminSourceCheck[];
};

export type AdminSourceCreate = {
  source_id: string;
  title: string;
  official_url: string;
  source_format: "html" | "pdf";
  notes: string | null;
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
  publishCandidate(reviewItemId: string) {
    return adminRequest<AdminFieldCandidate>(
      `/api/admin/review-items/${encodeURIComponent(reviewItemId)}/publish`,
      {
        method: "POST",
        headers: { "X-CMSQI-Admin-Action": "publish-field" },
      },
    );
  },
  sources(signal?: AbortSignal) {
    return adminRequest<{ items: AdminSourceSummary[] }>("/api/admin/sources", { signal });
  },
  createSource(source: AdminSourceCreate) {
    return adminRequest<AdminSourceDetail>("/api/admin/sources", {
      method: "POST",
      headers: { "X-CMSQI-Admin-Action": "source-registry" },
      body: JSON.stringify(source),
    });
  },
  updateSource(sourceId: string, update: { is_active: boolean }) {
    return adminRequest<AdminSourceDetail>(
      `/api/admin/sources/${encodeURIComponent(sourceId)}`,
      {
        method: "PATCH",
        headers: { "X-CMSQI-Admin-Action": "source-registry" },
        body: JSON.stringify(update),
      },
    );
  },
  checkSource(sourceId: string, force: boolean) {
    return adminRequest<AdminSourceDetail>(
      `/api/admin/sources/${encodeURIComponent(sourceId)}/check`,
      {
        method: "POST",
        headers: { "X-CMSQI-Admin-Action": "source-check" },
        body: JSON.stringify({ force }),
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
      queryClient.removeQueries({ queryKey: ["admin-sources"] });
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

export function useAdminSources(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-sources"],
    queryFn: ({ signal }) => adminApi.sources(signal),
    enabled,
    retry: false,
  });
}

export function useAdminSourceCreate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (source: AdminSourceCreate) => adminApi.createSource(source),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-sources"] }),
  });
}

export function useAdminSourceUpdate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceId, isActive }: { sourceId: string; isActive: boolean }) =>
      adminApi.updateSource(sourceId, { is_active: isActive }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-sources"] }),
  });
}

export function useAdminSourceCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sourceId, force }: { sourceId: string; force: boolean }) =>
      adminApi.checkSource(sourceId, force),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-sources"] }),
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

export function useAdminFieldPublication(measureId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reviewItemId: string) => adminApi.publishCandidate(reviewItemId),
    onSuccess: (updatedCandidate) => {
      queryClient.setQueryData<AdminMeasureDetail>(
        ["admin-review", "measure", measureId],
        (detail) =>
          detail
            ? {
                ...detail,
                is_public: true,
                versions: detail.versions.map((version) => ({
                  ...version,
                  publication_state: version.candidates.some(
                    (candidate) => candidate.review_item_id === updatedCandidate.review_item_id,
                  )
                    ? "published"
                    : version.publication_state,
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
      void queryClient.invalidateQueries({ queryKey: ["measures"] });
    },
  });
}
