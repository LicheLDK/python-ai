import { apiFetch } from "@/services/http";
import type { DocumentRead, Page } from "@/types";

export async function listDocuments(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<Page<DocumentRead>> {
  const q = new URLSearchParams();
  if (params?.page) q.set("page", String(params.page));
  if (params?.page_size) q.set("page_size", String(params.page_size));
  if (params?.status) q.set("status", params.status);
  const qs = q.toString();
  return apiFetch<Page<DocumentRead>>(
    `/api/v1/documents${qs ? `?${qs}` : ""}`,
  );
}

export async function getDocument(id: string): Promise<DocumentRead> {
  return apiFetch<DocumentRead>(`/api/v1/documents/${id}`);
}

export async function uploadDocument(file: File): Promise<DocumentRead> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<DocumentRead>("/api/v1/documents", {
    method: "POST",
    formData: form,
  });
}

export async function deleteDocument(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
}
