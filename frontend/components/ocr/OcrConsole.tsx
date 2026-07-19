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
import * as ocrApi from "@/services/ocr";
import type { DocumentRead, OcrJobRead, OcrResultsResponse } from "@/types";

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

export function OcrConsole() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [jobs, setJobs] = useState<OcrJobRead[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [results, setResults] = useState<OcrResultsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [d, j] = await Promise.all([
        documentsApi.listDocuments({ page_size: 50 }),
        ocrApi.listOcrJobs({ page_size: 20 }),
      ]);
      setDocs(d.items);
      setJobs(j.items);
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
    () => ocrApi.getOcrJob(activeJobId!),
    {
      enabled: !!activeJobId,
      stopWhen: (job) => TERMINAL.has(job.status),
    },
  );

  useEffect(() => {
    if (!polled) return;
    setJobs((prev) => {
      const idx = prev.findIndex((j) => j.id === polled.id);
      if (idx < 0) return [polled, ...prev];
      const next = [...prev];
      next[idx] = polled;
      return next;
    });
    if (polled.status === "succeeded") {
      void ocrApi
        .getOcrResults(polled.id)
        .then(setResults)
        .catch((e) =>
          setError(e instanceof ApiError ? e.message : "결과 조회 실패"),
        );
    }
  }, [polled]);

  async function startJob() {
    if (!documentId) return;
    setBusy(true);
    setError(null);
    setResults(null);
    try {
      const job = await ocrApi.createOcrJob({ document_id: documentId });
      setActiveJobId(job.id);
      setJobs((prev) => [job, ...prev]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "OCR 시작 실패");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<OcrJobRead>[] = [
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
          onClick={() => {
            setActiveJobId(r.id);
            setResults(null);
          }}
        >
          {r.id.slice(0, 8)}…
        </button>
      ),
    },
    {
      key: "doc",
      header: "Document",
      render: (r) => r.document_id.slice(0, 8) + "…",
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "error",
      header: "Error",
      render: (r) => r.error || "—",
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
        <label style={{ display: "grid", gap: "0.35rem", minWidth: 260 }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Document</span>
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: 6 }}
          >
            {docs.length === 0 ? (
              <option value="">문서 없음 — Documents에서 업로드</option>
            ) : (
              docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename}
                </option>
              ))
            )}
          </select>
        </label>
        <Button onClick={() => void startJob()} disabled={busy || !documentId}>
          {busy ? "시작 중…" : "OCR 시작"}
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
          rows={jobs}
          rowKey={(r) => r.id}
          empty={<EmptyState>OCR 작업이 없습니다.</EmptyState>}
        />
      </div>
      {results ? (
        <div
          style={{
            background: "#fff",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            padding: "1rem",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Results</h3>
          {results.pages.map((p) => (
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
          ))}
        </div>
      ) : null}
    </div>
  );
}
