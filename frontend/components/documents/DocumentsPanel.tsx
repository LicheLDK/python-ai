"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Table, type Column } from "@/components/ui/Table";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from "@/components/ui/States";
import { ApiError } from "@/services/http";
import * as documentsApi from "@/services/documents";
import type { DocumentRead } from "@/types";

export function DocumentUploader({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onChange(file: File | null) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await documentsApi.uploadDocument(file);
      onUploaded();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "업로드 실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "0.5rem" }}>
      <label
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.75rem",
          padding: "0.85rem 1rem",
          border: "1px dashed #9ca3af",
          borderRadius: 8,
          background: "#fff",
          cursor: "pointer",
          width: "fit-content",
        }}
      >
        <span style={{ fontWeight: 600 }}>
          {busy ? "업로드 중…" : "파일 선택 (jpeg/png/webp/pdf)"}
        </span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          disabled={busy}
          style={{ display: "none" }}
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
      </label>
      {error ? <ErrorState message={error} /> : null}
    </div>
  );
}

export function DocumentsPanel() {
  const [rows, setRows] = useState<DocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await documentsApi.listDocuments({ page_size: 50 });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "목록 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const columns: Column<DocumentRead>[] = [
    {
      key: "filename",
      header: "Filename",
      render: (r) => r.filename,
    },
    {
      key: "mime",
      header: "MIME",
      render: (r) => r.mime_type,
    },
    {
      key: "size",
      header: "Size",
      render: (r) => `${Math.round(r.size_bytes / 1024)} KB`,
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
      key: "actions",
      header: "",
      render: (r) => (
        <Button
          variant="danger"
          onClick={async () => {
            if (!confirm("이 문서를 삭제할까요?")) return;
            try {
              await documentsApi.deleteDocument(r.id);
              await reload();
            } catch (e) {
              alert(e instanceof ApiError ? e.message : "삭제 실패");
            }
          }}
        >
          삭제
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <DocumentUploader onUploaded={() => void reload()} />
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
            empty={<EmptyState>업로드된 문서가 없습니다.</EmptyState>}
          />
        </div>
      ) : null}
    </div>
  );
}
