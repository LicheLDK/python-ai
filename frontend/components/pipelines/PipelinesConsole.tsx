"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { usePolling } from "@/hooks/usePolling";
import { ApiError } from "@/services/http";
import * as documentsApi from "@/services/documents";
import * as pipelinesApi from "@/services/pipelines";
import type { DocumentRead, PipelineRunRead } from "@/types";

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

export function PipelinesConsole() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [runs, setRuns] = useState<PipelineRunRead[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [promptName, setPromptName] = useState("ocr_analysis");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PipelineRunRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [d, r] = await Promise.all([
        documentsApi.listDocuments({ page_size: 50 }),
        pipelinesApi.listPipelineRuns({ page_size: 20 }),
      ]);
      setDocs(d.items);
      setRuns(r.items);
      if (!documentId && d.items[0]) setDocumentId(d.items[0].id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "불러오기 실패");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const { data: polled } = usePolling(
    () => pipelinesApi.getPipelineRun(activeId!),
    {
      enabled: !!activeId,
      stopWhen: (run) => TERMINAL.has(run.status),
    },
  );

  useEffect(() => {
    if (!polled) return;
    setDetail(polled);
    setRuns((prev) => {
      const idx = prev.findIndex((r) => r.id === polled.id);
      if (idx < 0) return [polled, ...prev];
      const next = [...prev];
      next[idx] = polled;
      return next;
    });
  }, [polled]);

  async function start() {
    if (!documentId) return;
    setBusy(true);
    setError(null);
    try {
      const run = await pipelinesApi.createPipelineRun({
        document_id: documentId,
        ai: promptName ? { prompt_name: promptName } : undefined,
      });
      setActiveId(run.id);
      setDetail(run);
      setRuns((prev) => [run, ...prev]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "파이프라인 시작 실패");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<PipelineRunRead>[] = [
    {
      key: "id",
      header: "Run",
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
          onClick={() => {
            setActiveId(r.id);
            setDetail(r);
          }}
        >
          {r.id.slice(0, 8)}…
        </button>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "doc",
      header: "Document",
      render: (r) => r.document_id.slice(0, 8) + "…",
    },
  ];

  if (loading) return <LoadingState />;

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          alignItems: "end",
          background: "#fff",
          padding: "1rem",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
        }}
      >
        <label style={{ display: "grid", gap: "0.35rem", minWidth: 240 }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Document</span>
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: 6 }}
          >
            {docs.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "grid", gap: "0.35rem", minWidth: 180 }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>
            AI prompt
          </span>
          <input
            value={promptName}
            onChange={(e) => setPromptName(e.target.value)}
            style={{
              padding: "0.5rem",
              borderRadius: 6,
              border: "1px solid #d1d5db",
            }}
          />
        </label>
        <Button onClick={() => void start()} disabled={busy || !documentId}>
          {busy ? "시작 중…" : "파이프라인 실행"}
        </Button>
      </div>
      {error ? <ErrorState message={error} /> : null}
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
        }}
      >
        <Table
          columns={columns}
          rows={runs}
          rowKey={(r) => r.id}
          empty={<EmptyState>실행 이력이 없습니다.</EmptyState>}
        />
      </div>
      {detail ? (
        <div
          style={{
            background: "#fff",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            padding: "1rem",
          }}
        >
          <h3 style={{ marginTop: 0 }}>
            Stages · <StatusBadge status={detail.status} />
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
            {(detail.stages || []).map((s) => (
              <li key={s.name} style={{ marginBottom: "0.35rem" }}>
                <strong>{s.name}</strong> — <StatusBadge status={s.status} />
                {s.error ? (
                  <span style={{ color: "#991b1b" }}> ({s.error})</span>
                ) : null}
                {s.output_ref ? (
                  <span style={{ color: "#6b7280" }}>
                    {" "}
                    → {JSON.stringify(s.output_ref)}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
