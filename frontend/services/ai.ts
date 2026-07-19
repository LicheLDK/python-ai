import { apiFetch } from "@/services/http";
import type {
  ChatMessage,
  ChatResponse,
  Page,
  PromptRead,
  VisionResponse,
} from "@/types";

export async function chat(input: {
  messages: ChatMessage[];
  prompt_name?: string;
  prompt_version?: number;
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/v1/ai/chat", {
    method: "POST",
    body: input,
  });
}

export async function vision(input: {
  document_id?: string;
  ocr_job_id?: string;
  prompt_name?: string;
  prompt_version?: number;
  provider?: string;
  model?: string;
}): Promise<VisionResponse> {
  return apiFetch<VisionResponse>("/api/v1/ai/vision", {
    method: "POST",
    body: input,
  });
}

export async function listPrompts(params?: {
  page?: number;
  page_size?: number;
  active?: boolean;
  name?: string;
}): Promise<Page<PromptRead>> {
  const q = new URLSearchParams();
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  if (params?.active !== undefined) q.set("active", String(params.active));
  if (params?.name) q.set("name", params.name);
  const qs = q.toString();
  return apiFetch<Page<PromptRead>>(`/api/v1/ai/prompts${qs ? `?${qs}` : ""}`);
}

export async function getPrompt(id: string): Promise<PromptRead> {
  return apiFetch<PromptRead>(`/api/v1/ai/prompts/${id}`);
}

export async function createPrompt(input: {
  name: string;
  template: string;
  variables_schema?: Record<string, unknown>;
  activate?: boolean;
}): Promise<PromptRead> {
  return apiFetch<PromptRead>("/api/v1/ai/prompts", {
    method: "POST",
    body: input,
  });
}

export async function updatePrompt(
  id: string,
  input: {
    template?: string;
    variables_schema?: Record<string, unknown>;
    create_new_version?: boolean;
  },
): Promise<PromptRead> {
  return apiFetch<PromptRead>(`/api/v1/ai/prompts/${id}`, {
    method: "PATCH",
    body: input,
  });
}

export async function activatePrompt(id: string): Promise<PromptRead> {
  return apiFetch<PromptRead>(`/api/v1/ai/prompts/${id}/activate`, {
    method: "POST",
  });
}
