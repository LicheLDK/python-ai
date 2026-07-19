import { apiFetch } from "@/services/http";
import type { StatPoint, StatsSummary } from "@/types";

export async function getDailyStats(params: {
  from: string;
  to: string;
  metric?: string;
  scope?: "self" | "global";
}): Promise<{ points: StatPoint[] }> {
  const q = new URLSearchParams({
    from: params.from,
    to: params.to,
  });
  if (params.metric) q.set("metric", params.metric);
  if (params.scope) q.set("scope", params.scope);
  return apiFetch<{ points: StatPoint[] }>(`/api/v1/stats/daily?${q}`);
}

export async function getMonthlyStats(params: {
  from_month: string;
  to_month: string;
  metric?: string;
  scope?: "self" | "global";
}): Promise<{ points: { month: string; metric: string; value: number }[] }> {
  const q = new URLSearchParams({
    from_month: params.from_month,
    to_month: params.to_month,
  });
  if (params.metric) q.set("metric", params.metric);
  if (params.scope) q.set("scope", params.scope);
  return apiFetch(`/api/v1/stats/monthly?${q}`);
}

export async function getSummary(): Promise<StatsSummary> {
  return apiFetch<StatsSummary>("/api/v1/stats/summary");
}

export async function exportCsv(params: {
  from: string;
  to: string;
  metric?: string;
  scope?: "self" | "global";
}): Promise<string> {
  const q = new URLSearchParams({
    from: params.from,
    to: params.to,
    format: "csv",
  });
  if (params.metric) q.set("metric", params.metric);
  if (params.scope) q.set("scope", params.scope);
  return apiFetch<string>(`/api/v1/stats/export?${q}`);
}
