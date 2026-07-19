"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as adminApi from "@/services/admin";
import type { AuditLogRead } from "@/types";

export function AuditAdminPanel() {
  const [rows, setRows] = useState<AuditLogRead[]>([]);
  const [action, setAction] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await adminApi.listAuditLogs({
        action: action || undefined,
        page_size: 50,
      });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [action]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columns: Column<AuditLogRead>[] = [
    {
      key: "created",
      header: "Created",
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
    { key: "action", header: "Action", render: (r) => r.action },
    {
      key: "resource",
      header: "Resource",
      render: (r) => `${r.resource_type}${r.resource_id ? `:${r.resource_id.slice(0, 8)}` : ""}`,
    },
    {
      key: "actor",
      header: "Actor",
      render: (r) => (r.actor_id ? r.actor_id.slice(0, 8) + "…" : "—"),
    },
    {
      key: "payload",
      header: "Payload",
      render: (r) => (
        <code style={{ fontSize: "0.75rem" }}>
          {JSON.stringify(r.payload || {}).slice(0, 80)}
        </code>
      ),
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <Input
          label="Action filter"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="admin.user.update"
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
            empty={<EmptyState>감사 로그가 없습니다.</EmptyState>}
          />
        </div>
      ) : null}
    </div>
  );
}
