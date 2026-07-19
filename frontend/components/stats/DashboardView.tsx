"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { DailyChart } from "@/components/stats/DailyChart";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as ocrApi from "@/services/ocr";
import * as statsApi from "@/services/stats";
import type { OcrJobRead, StatsSummary } from "@/types";

const card: CSSProperties = {
  background: "#fff",
  borderRadius: 10,
  border: "1px solid #e5e7eb",
  padding: "1rem 1.1rem",
  minWidth: 140,
};

export function DashboardView() {
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [jobs, setJobs] = useState<OcrJobRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [s, j] = await Promise.all([
          statsApi.getSummary(),
          ocrApi.listOcrJobs({ page_size: 5 }),
        ]);
        setSummary(s);
        setJobs(j.items);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "대시보드 로드 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const columns: Column<OcrJobRead>[] = [
    {
      key: "id",
      header: "Job",
      render: (r) => r.id.slice(0, 8) + "…",
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "created",
      header: "Created",
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
  ];

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!summary) return <EmptyState>요약 데이터가 없습니다.</EmptyState>;

  return (
    <div style={{ display: "grid", gap: "1.25rem" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "0.75rem",
        }}
      >
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            OCR today
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {summary.ocr_jobs_today}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            AI today
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {summary.ai_requests_today}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            Tokens today
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {summary.tokens_today}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            Error rate
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {(summary.error_rate_today * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      <section
        style={{
          background: "#fff",
          borderRadius: 10,
          border: "1px solid #e5e7eb",
          padding: "1rem",
        }}
      >
        <h2 style={{ marginTop: 0, fontSize: "1.05rem" }}>
          Personal daily stats (14d)
        </h2>
        <DailyChart />
      </section>

      <section
        style={{
          background: "#fff",
          borderRadius: 10,
          border: "1px solid #e5e7eb",
        }}
      >
        <h2 style={{ margin: "1rem 1rem 0", fontSize: "1.05rem" }}>
          Recent OCR jobs
        </h2>
        <Table
          columns={columns}
          rows={jobs}
          rowKey={(r) => r.id}
          empty={<EmptyState>최근 OCR 작업이 없습니다.</EmptyState>}
        />
      </section>
    </div>
  );
}
