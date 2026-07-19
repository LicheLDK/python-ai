import { apiFetch } from "@/services/http";
import type { OcrJobRead, OcrResultsResponse, Page } from "@/types";

export async function createOcrJob(input: {
  document_id: string;
  options?: {
    lang?: string;
    preprocess?: { deskew?: boolean; denoise?: boolean; contrast?: boolean };
  };
}): Promise<OcrJobRead> {
  const created = await apiFetch<{
    id: string;
    document_id: string;
    status: OcrJobRead["status"];
    created_at: string;
  }>("/api/v1/ocr/jobs", {
    method: "POST",
    body: input,
  });
  try {
    return await getOcrJob(created.id);
  } catch {
    return {
      id: created.id,
      document_id: created.document_id,
      status: created.status,
      created_at: created.created_at,
    };
  }
}

export async function listOcrJobs(params?: {
  page?: number;
  page_size?: number;
}): Promise<Page<OcrJobRead>> {
  const q = new URLSearchParams();
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  const qs = q.toString();
  return apiFetch<Page<OcrJobRead>>(`/api/v1/ocr/jobs${qs ? `?${qs}` : ""}`);
}

export async function getOcrJob(id: string): Promise<OcrJobRead> {
  return apiFetch<OcrJobRead>(`/api/v1/ocr/jobs/${id}`);
}

export async function getOcrResults(id: string): Promise<OcrResultsResponse> {
  return apiFetch<OcrResultsResponse>(`/api/v1/ocr/jobs/${id}/results`);
}
