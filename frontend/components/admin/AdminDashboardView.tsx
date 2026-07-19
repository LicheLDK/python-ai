"use client";

import { useEffect, useState, type CSSProperties } from "react";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as adminApi from "@/services/admin";
import type { AdminDashboard } from "@/types";

const card: CSSProperties = {
  background: "#fff",
  borderRadius: 10,
  border: "1px solid #e5e7eb",
  padding: "1rem 1.1rem",
  minWidth: 140,
};

export function AdminDashboardView() {
  const [data, setData] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        setData(await adminApi.getDashboard());
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "대시보드 로드 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState>데이터 없음</EmptyState>;

  const topCols: Column<AdminDashboard["top_users"][number]>[] = [
    {
      key: "email",
      header: "User",
      render: (r) => r.email || r.user_id.slice(0, 8) + "…",
    },
    { key: "ocr", header: "OCR 24h", render: (r) => r.ocr_jobs },
    { key: "ai", header: "AI 24h", render: (r) => r.ai_requests },
  ];

  const provCols: Column<AdminDashboard["provider_breakdown"][number]>[] = [
    { key: "provider", header: "Provider", render: (r) => r.provider },
    { key: "req", header: "Requests", render: (r) => r.requests },
    {
      key: "tokens",
      header: "Tokens in/out",
      render: (r) => `${r.tokens_in}/${r.tokens_out}`,
    },
    {
      key: "cost",
      header: "Cost",
      render: (r) => Number(r.cost_estimate).toFixed(6),
    },
  ];

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
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>Users</div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {data.users_total}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            OCR (24h)
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {data.ocr_jobs_24h}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            AI (24h)
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {data.ai_requests_24h}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontSize: "0.8rem", color: "#6b7280" }}>
            Error rate (24h)
          </div>
          <div style={{ fontSize: "1.6rem", fontWeight: 700 }}>
            {(data.error_rate_24h * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      <section
        style={{
          background: "#fff",
          borderRadius: 10,
          border: "1px solid #e5e7eb",
        }}
      >
        <h2 style={{ margin: "1rem 1rem 0", fontSize: "1.05rem" }}>
          Top users (24h)
        </h2>
        <Table
          columns={topCols}
          rows={data.top_users}
          rowKey={(r) => r.user_id}
          empty={<EmptyState>활동 사용자 없음</EmptyState>}
        />
      </section>

      <section
        style={{
          background: "#fff",
          borderRadius: 10,
          border: "1px solid #e5e7eb",
        }}
      >
        <h2 style={{ margin: "1rem 1rem 0", fontSize: "1.05rem" }}>
          Provider breakdown (24h)
        </h2>
        <Table
          columns={provCols}
          rows={data.provider_breakdown}
          rowKey={(r) => r.provider}
          empty={<EmptyState>요청 없음</EmptyState>}
        />
      </section>
    </div>
  );
}
