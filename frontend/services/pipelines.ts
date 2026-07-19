import { apiFetch } from "@/services/http";
import type { Page, PipelineRunRead } from "@/types";

export async function createPipelineRun(input: {
  document_id: string;
  ocr_options?: Record<string, unknown>;
  ai?: { prompt_name: string; provider?: string };
}): Promise<PipelineRunRead> {
  const created = await apiFetch<{
    id: string;
    status: PipelineRunRead["status"];
    document_id: string;
    created_at: string;
  }>("/api/v1/pipelines/runs", {
    method: "POST",
    body: input,
  });
  // 202 Created is a slim DTO — fetch full run for stages.
  try {
    return await getPipelineRun(created.id);
  } catch {
    return {
      id: created.id,
      status: created.status,
      document_id: created.document_id,
      stages: [],
      created_at: created.created_at,
    };
  }
}

export async function listPipelineRuns(params?: {
  page?: number;
  page_size?: number;
}): Promise<Page<PipelineRunRead>> {
  const q = new URLSearchParams();
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  const qs = q.toString();
  return apiFetch<Page<PipelineRunRead>>(
    `/api/v1/pipelines/runs${qs ? `?${qs}` : ""}`,
  );
}

export async function getPipelineRun(id: string): Promise<PipelineRunRead> {
  return apiFetch<PipelineRunRead>(`/api/v1/pipelines/runs/${id}`);
}
