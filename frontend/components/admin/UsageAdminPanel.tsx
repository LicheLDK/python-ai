"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as adminApi from "@/services/admin";
import type { AiUsageRead } from "@/types";

export function UsageAdminPanel() {
  const [rows, setRows] = useState<AiUsageRead[]>([]);
  const [provider, setProvider] = useState("");
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await adminApi.listUsage({
        provider: provider || undefined,
        user_id: userId || undefined,
        page_size: 50,
      });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [provider, userId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columns: Column<AiUsageRead>[] = [
    {
      key: "created",
      header: "Created",
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
    { key: "provider", header: "Provider", render: (r) => r.provider },
    { key: "model", header: "Model", render: (r) => r.model },
    {
      key: "type",
      header: "Type",
      render: (r) => r.request_type,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
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
    {
      key: "user",
      header: "User",
      render: (r) => r.user_id.slice(0, 8) + "…",
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <label style={{ display: "grid", gap: "0.35rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Provider</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: 6, minWidth: 140 }}
          >
            <option value="">(all)</option>
            <option value="openai">openai</option>
            <option value="gemini">gemini</option>
            <option value="ollama">ollama</option>
          </select>
        </label>
        <Input
          label="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="uuid"
        />
        <Button
          variant="secondary"
          style={{ alignSelf: "end" }}
          onClick={() => void reload()}
        >
          Apply
        </Button>
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? (
        <div
          style={{
            background: "#fff",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
          }}
        >
          <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty={<EmptyState>사용량 기록이 없습니다.</EmptyState>}
          />
        </div>
      ) : null}
    </div>
  );
}
