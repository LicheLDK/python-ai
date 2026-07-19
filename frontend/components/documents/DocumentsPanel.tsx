"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, PageHeader } from "@/components/ui/Card";
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
import { cn } from "@/lib/cn";

export function DocumentUploader({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

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
    <div className="grid gap-3">
      <label
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition",
          dragOver
            ? "border-brand bg-brand-soft"
            : "border-indigo-200 bg-indigo-50/40 hover:border-brand hover:bg-brand-soft/60",
          busy && "pointer-events-none opacity-60",
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          void onChange(e.dataTransfer.files?.[0] ?? null);
        }}
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-brand shadow-sm">
          <UploadCloud className="h-6 w-6" />
        </div>
        <div className="text-sm font-semibold text-slate-800">
          {busy
            ? "업로드 중…"
            : "파일을 끌어다 놓거나 클릭하여 업로드"}
        </div>
        <div className="text-xs text-muted">jpeg / png / webp / pdf</div>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          disabled={busy}
          className="hidden"
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
      render: (r) => (
        <span className="font-medium text-foreground">{r.filename}</span>
      ),
    },
    {
      key: "mime",
      header: "MIME",
      render: (r) => <span className="text-muted">{r.mime_type}</span>,
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
      render: (r) => (
        <span className="text-muted">
          {new Date(r.created_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "72px",
      render: (r) => (
        <Button
          variant="ghost"
          className="!px-2 text-danger hover:bg-danger-soft"
          title="삭제"
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
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Documents"
        description="업로드 · 목록 · 삭제 (jpeg/png/webp/pdf)"
      />
      <div className="mb-5">
        <DocumentUploader onUploaded={() => void reload()} />
      </div>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? (
        <Card>
          <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty={<EmptyState>업로드된 문서가 없습니다.</EmptyState>}
          />
        </Card>
      ) : null}
    </div>
  );
}
