import { ApiError } from "./api";

export type ReviewStatus = "pending" | "in_review" | "resolved";
export const statusLabels: Record<ReviewStatus, string> = {
  pending: "Pending",
  in_review: "In Review",
  resolved: "Resolved",
};
export interface ReviewTask {
  id: number;
  document_id: number;
  status: ReviewStatus;
  reason: string;
  notes: string;
  resolution: string;
  version: number;
  created_at: string;
  updated_at: string;
  in_review_at: string | null;
  resolved_at: string | null;
}
export interface ReviewDetail extends ReviewTask {
  original_filename: string;
  invoice_id: number | null;
  invoice_number: string | null;
  carrier_name: string | null;
  error_code: string | null;
}
export interface ReviewHistory {
  id: number;
  task_id: number;
  from_status: ReviewStatus | null;
  to_status: ReviewStatus;
  notes: string;
  resolution: string;
  version: number;
  origin: "operator" | "pipeline";
  created_at: string;
}
export interface ReviewPage {
  items: ReviewDetail[];
  total: number;
  page: number;
  page_size: number;
}
export interface ReviewPatch {
  version: number;
  status?: ReviewStatus;
  notes?: string;
  resolution?: string;
}
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/review-tasks${path}`, options);
  } catch {
    throw new ApiError("Review service could not be reached", 503);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: { message?: string };
    } | null;
    throw new ApiError(
      body?.error?.message ?? "Review request failed",
      response.status,
    );
  }
  return response.json() as Promise<T>;
}
export function listReviewTasks(
  status: ReviewStatus | "",
  page = 1,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (status) query.set("status", status);
  return request<ReviewPage>(`?${query}`, { signal });
}
export function getReviewTask(id: number, signal?: AbortSignal) {
  return request<ReviewDetail>(`/${id}`, { signal });
}
export function getReviewHistory(id: number, signal?: AbortSignal) {
  return request<ReviewHistory[]>(`/${id}/history`, { signal });
}
export function updateReviewTask(id: number, patch: ReviewPatch) {
  return request<ReviewTask>(`/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
}
