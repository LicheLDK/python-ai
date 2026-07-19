"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { ApiError } from "@/services/http";
import * as statsApi from "@/services/stats";
import type { StatPoint } from "@/types";

const METRICS = [
  "ocr.jobs.count",
  "ai.requests.count",
  "pipeline.runs.count",
] as const;

function daysAgo(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

export function DailyChart() {
  const [points, setPoints] = useState<StatPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const res = await statsApi.getDailyStats({
          from: daysAgo(13),
          to: daysAgo(0),
          scope: "self",
        });
        setPoints(res.points);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "차트 데이터 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const series = useMemo(() => {
    const byDate = new Map<string, Record<string, number | string>>();
    for (const p of points) {
      if (!METRICS.includes(p.metric as (typeof METRICS)[number])) continue;
      const row = byDate.get(p.date) || { date: p.date };
      row[p.metric] = p.value;
      byDate.set(p.date, row);
    }
    return Array.from(byDate.values()).sort((a, b) =>
      String(a.date).localeCompare(String(b.date)),
    );
  }, [points]);

  if (loading) return <LoadingState label="차트 로딩…" />;
  if (error) return <ErrorState message={error} />;
  if (series.length === 0) {
    return (
      <div style={{ color: "#6b7280", padding: "1rem" }}>
        아직 집계된 일별 통계가 없습니다. (materialize cron 이후 표시)
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={series}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="ocr.jobs.count" fill="#2563eb" name="OCR jobs" />
          <Bar dataKey="ai.requests.count" fill="#059669" name="AI requests" />
          <Bar
            dataKey="pipeline.runs.count"
            fill="#d97706"
            name="Pipelines"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
