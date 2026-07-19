"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  Bot,
  Coins,
  FileText,
  ScanText,
  ShieldCheck,
} from "lucide-react";
import { Card, PageHeader } from "@/components/ui/Card";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { ApiError } from "@/services/http";
import * as ocrApi from "@/services/ocr";
import * as statsApi from "@/services/stats";
import type { OcrJobRead, StatPoint, StatsSummary } from "@/types";

function daysAgo(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

function buildSeries(points: StatPoint[]) {
  const byDate = new Map<string, Record<string, number | string>>();
  for (const p of points) {
    if (
      p.metric !== "ocr.jobs.count" &&
      p.metric !== "ai.requests.count"
    ) {
      continue;
    }
    const row = byDate.get(p.date) || { date: p.date };
    row[p.metric] = p.value;
    byDate.set(p.date, row);
  }
  return Array.from(byDate.values()).sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  tone,
  trend,
}: {
  label: string;
  value: string | number;
  icon: typeof ScanText;
  tone: "indigo" | "violet" | "blue" | "green";
  trend?: boolean;
}) {
  const tones = {
    indigo: "bg-indigo-50 text-indigo-600",
    violet: "bg-violet-50 text-violet-600",
    blue: "bg-sky-50 text-sky-600",
    green: "bg-emerald-50 text-emerald-600",
  };
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-medium text-muted">{label}</div>
          <div className="mt-1 flex items-center gap-1.5">
            <div className="text-2xl font-bold tracking-tight text-foreground">
              {value}
            </div>
            {trend ? (
              <ArrowUpRight className="h-4 w-4 text-success" />
            ) : null}
          </div>
        </div>
      </div>
    </Card>
  );
}

export function DashboardView() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [jobs, setJobs] = useState<OcrJobRead[]>([]);
  const [points, setPoints] = useState<StatPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [s, j, daily] = await Promise.all([
          statsApi.getSummary(),
          ocrApi.listOcrJobs({ page_size: 5 }),
          statsApi.getDailyStats({
            from: daysAgo(13),
            to: daysAgo(0),
            scope: "self",
          }),
        ]);
        setSummary(s);
        setJobs(j.items);
        setPoints(daily.points);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "대시보드 로드 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!summary) return <EmptyState>요약 데이터가 없습니다.</EmptyState>;

  const series = buildSeries(points);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="오늘 요약 · 일별 차트 · 최근 OCR"
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="OCR today"
          value={summary.ocr_jobs_today}
          icon={ScanText}
          tone="indigo"
        />
        <KpiCard
          label="AI today"
          value={summary.ai_requests_today}
          icon={Bot}
          tone="violet"
        />
        <KpiCard
          label="Tokens today"
          value={summary.tokens_today.toLocaleString()}
          icon={Coins}
          tone="blue"
        />
        <KpiCard
          label="Error rate"
          value={`${(summary.error_rate_today * 100).toFixed(1)}%`}
          icon={ShieldCheck}
          tone="green"
          trend={summary.error_rate_today < 0.05}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="m-0 text-base font-semibold">
              Personal daily stats (14d)
            </h2>
          </div>
          {series.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted">
              아직 집계된 일별 통계가 없습니다. (materialize cron 이후 표시)
            </div>
          ) : (
            <div className="h-[280px] w-full">
              <ResponsiveContainer>
                <ComposedChart data={series}>
                  <defs>
                    <linearGradient id="aiFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 12,
                      border: "1px solid #e2e8f0",
                      boxShadow: "0 8px 20px rgba(15,23,42,0.08)",
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="ocr.jobs.count"
                    fill="#6366f1"
                    name="OCR"
                    radius={[6, 6, 0, 0]}
                    barSize={18}
                  />
                  <Area
                    type="monotone"
                    dataKey="ai.requests.count"
                    stroke="#8b5cf6"
                    fill="url(#aiFill)"
                    name="AI"
                    strokeWidth={2}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="m-0 text-base font-semibold">Recent OCR jobs</h2>
            <Link
              href="/ocr"
              className="text-xs font-semibold text-brand hover:text-brand-hover"
            >
              View all →
            </Link>
          </div>
          {jobs.length === 0 ? (
            <EmptyState>최근 OCR 작업이 없습니다.</EmptyState>
          ) : (
            <ul className="m-0 list-none space-y-3 p-0">
              {jobs.map((job) => (
                <li
                  key={job.id}
                  className="flex items-center gap-3 rounded-xl border border-border/80 bg-slate-50/50 px-3 py-2.5"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-soft text-brand">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-foreground">
                      {job.id.slice(0, 8)}…
                    </div>
                    <div className="text-[11px] text-muted">
                      {new Date(job.created_at).toLocaleString()}
                    </div>
                  </div>
                  <StatusBadge status={job.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
