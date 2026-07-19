"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, ScanText, Users } from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as adminApi from "@/services/admin";
import type { AdminDashboard } from "@/types";

function Kpi({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  icon: typeof Users;
  tone: string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${tone}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="text-xs font-medium text-muted">{label}</div>
          <div className="mt-1 text-2xl font-bold tracking-tight">{value}</div>
        </div>
      </div>
    </Card>
  );
}

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
    <div className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Users"
          value={data.users_total}
          icon={Users}
          tone="bg-indigo-50 text-indigo-600"
        />
        <Kpi
          label="OCR 24h"
          value={data.ocr_jobs_24h}
          icon={ScanText}
          tone="bg-violet-50 text-violet-600"
        />
        <Kpi
          label="AI 24h"
          value={data.ai_requests_24h}
          icon={Bot}
          tone="bg-sky-50 text-sky-600"
        />
        <Kpi
          label="Error rate 24h"
          value={`${(data.error_rate_24h * 100).toFixed(1)}%`}
          icon={Activity}
          tone="bg-emerald-50 text-emerald-600"
        />
      </div>

      <Card>
        <h2 className="m-0 border-b border-border px-5 py-4 text-base font-semibold">
          Top users (24h)
        </h2>
        <Table
          columns={topCols}
          rows={data.top_users}
          rowKey={(r) => r.user_id}
          empty={<EmptyState>상위 사용자 없음</EmptyState>}
        />
      </Card>

      <Card>
        <h2 className="m-0 border-b border-border px-5 py-4 text-base font-semibold">
          Provider breakdown (24h)
        </h2>
        <Table
          columns={provCols}
          rows={data.provider_breakdown}
          rowKey={(r) => r.provider}
          empty={<EmptyState>프로바이더 사용량 없음</EmptyState>}
        />
      </Card>
    </div>
  );
}
