"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as adminApi from "@/services/admin";
import type { OcrJobAdminDetail, OcrJobAdminRead } from "@/types";

export function OcrHistoryAdminPanel() {
  const [rows, setRows] = useState<OcrJobAdminRead[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<OcrJobAdminDetail | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await adminApi.listOcrHistory({
        status: status || undefined,
        page_size: 50,
      });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function openDetail(id: string) {
    try {
      setDetail(await adminApi.getOcrHistoryDetail(id));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "상세 조회 실패");
    }
  }

  const columns: Column<OcrJobAdminRead>[] = [
    {
      key: "id",
      header: "Job",
      render: (r) => (
        <button
          type="button"
          style={{
            background: "none",
            border: "none",
            color: "#1d4ed8",
            cursor: "pointer",
            padding: 0,
            font: "inherit",
          }}
          onClick={() => void openDetail(r.id)}
        >
          {r.id.slice(0, 8)}…
        </button>
      ),
    },
    {
      key: "user",
      header: "User",
      render: (r) => r.user_id.slice(0, 8) + "…",
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
    {
      key: "error",
      header: "Error",
      render: (r) => r.error || "—",
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "end" }}>
        <label style={{ display: "grid", gap: "0.35rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: 6 }}
          >
            <option value="">(all)</option>
            <option value="queued">queued</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="cancelled">cancelled</option>
          </select>
        </label>
        <Button variant="secondary" onClick={() => void reload()}>
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
            empty={<EmptyState>OCR 이력이 없습니다.</EmptyState>}
          />
        </div>
      ) : null}

      <Modal
        open={!!detail}
        title="OCR job detail"
        onClose={() => setDetail(null)}
      >
        {detail ? (
          <div style={{ display: "grid", gap: "0.75rem" }}>
            <div>
              Status: <StatusBadge status={detail.job.status} />
            </div>
            {detail.pages.length === 0 ? (
              <EmptyState>결과 텍스트가 없습니다.</EmptyState>
            ) : (
              detail.pages.map((p) => (
                <pre
                  key={p.page}
                  style={{
                    whiteSpace: "pre-wrap",
                    background: "#f9fafb",
                    padding: "0.75rem",
                    borderRadius: 6,
                  }}
                >
                  {`[page ${p.page}]\n${p.text || "(empty)"}`}
                </pre>
              ))
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
