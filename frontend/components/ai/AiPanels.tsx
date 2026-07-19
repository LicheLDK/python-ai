"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState, StatusBadge } from "@/components/ui/States";
import { Table, type Column } from "@/components/ui/Table";
import { ApiError } from "@/services/http";
import * as aiApi from "@/services/ai";
import * as documentsApi from "@/services/documents";
import type {
  ChatMessage,
  ChatResponse,
  DocumentRead,
  PromptRead,
  UsageBlock,
  VisionResponse,
} from "@/types";

function UsageLine({ usage }: { usage: UsageBlock }) {
  return (
    <p style={{ fontSize: "0.85rem", color: "#4b5563", margin: "0.35rem 0 0" }}>
      tokens in/out: {usage.tokens_in}/{usage.tokens_out} · latency{" "}
      {usage.latency_ms}ms
      {usage.cost_estimate != null
        ? ` · est. $${Number(usage.cost_estimate).toFixed(6)}`
        : ""}
    </p>
  );
}

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [promptName, setPromptName] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [last, setLast] = useState<ChatResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: input.trim() },
    ];
    setMessages(nextMessages);
    setInput("");
    setBusy(true);
    setError(null);
    try {
      const res = await aiApi.chat({
        messages: nextMessages,
        prompt_name: promptName || undefined,
      });
      setLast(res);
      setMessages([...nextMessages, res.message]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "채팅 실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "0.75rem" }}>
      <h3 style={{ margin: 0 }}>Chat</h3>
      <input
        placeholder="prompt_name (optional)"
        value={promptName}
        onChange={(e) => setPromptName(e.target.value)}
        style={{ padding: "0.5rem", borderRadius: 6, border: "1px solid #d1d5db" }}
      />
      <div
        style={{
          minHeight: 180,
          maxHeight: 320,
          overflowY: "auto",
          background: "#f9fafb",
          borderRadius: 8,
          padding: "0.75rem",
          border: "1px solid #e5e7eb",
        }}
      >
        {messages.length === 0 ? (
          <span style={{ color: "#6b7280" }}>메시지를 입력하세요.</span>
        ) : (
          messages.map((m, i) => (
            <div key={`${m.role}-${i}`} style={{ marginBottom: "0.5rem" }}>
              <strong>{m.role}:</strong> {m.content}
            </div>
          ))
        )}
      </div>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: "0.5rem" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something…"
          style={{
            flex: 1,
            padding: "0.55rem 0.7rem",
            borderRadius: 6,
            border: "1px solid #d1d5db",
          }}
        />
        <Button type="submit" disabled={busy}>
          {busy ? "…" : "Send"}
        </Button>
      </form>
      {last ? <UsageLine usage={last.usage} /> : null}
      {error ? <ErrorState message={error} /> : null}
    </div>
  );
}

export function VisionPanel() {
  const [docs, setDocs] = useState<DocumentRead[]>([]);
  const [documentId, setDocumentId] = useState("");
  const [promptName, setPromptName] = useState("");
  const [result, setResult] = useState<VisionResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void documentsApi
      .listDocuments({ page_size: 50 })
      .then((p) => {
        setDocs(p.items);
        if (p.items[0]) setDocumentId(p.items[0].id);
      })
      .catch(() => undefined);
  }, []);

  async function run() {
    if (!documentId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await aiApi.vision({
        document_id: documentId,
        prompt_name: promptName || undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Vision 실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: "0.75rem" }}>
      <h3 style={{ margin: 0 }}>Vision</h3>
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
      <input
        placeholder="prompt_name (optional)"
        value={promptName}
        onChange={(e) => setPromptName(e.target.value)}
        style={{ padding: "0.5rem", borderRadius: 6, border: "1px solid #d1d5db" }}
      />
      <Button onClick={() => void run()} disabled={busy || !documentId}>
        {busy ? "분석 중…" : "Vision 실행"}
      </Button>
      {result ? (
        <>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              background: "#f9fafb",
              padding: "0.75rem",
              borderRadius: 6,
            }}
          >
            {typeof result.result === "string"
              ? result.result
              : JSON.stringify(result.result, null, 2)}
          </pre>
          <UsageLine usage={result.usage} />
        </>
      ) : null}
      {error ? <ErrorState message={error} /> : null}
    </div>
  );
}

export function PromptBrowser() {
  const [rows, setRows] = useState<PromptRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PromptRead | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const page = await aiApi.listPrompts({
          page_size: 50,
          active: true,
        });
        setRows(page.items);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "프롬프트 조회 실패");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const columns: Column<PromptRead>[] = [
    {
      key: "name",
      header: "Name",
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
          onClick={() => setSelected(r)}
        >
          {r.name}
        </button>
      ),
    },
    { key: "ver", header: "Ver", render: (r) => r.version },
    {
      key: "active",
      header: "Active",
      render: (r) => (
        <StatusBadge status={r.active ? "active" : "inactive"} />
      ),
    },
  ];

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;

  return (
    <div style={{ display: "grid", gap: "0.75rem" }}>
      <h3 style={{ margin: 0 }}>Active prompts (read-only)</h3>
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          border: "1px solid #e5e7eb",
        }}
      >
        <Table columns={columns} rows={rows} rowKey={(r) => r.id} />
      </div>
      {selected ? (
        <pre
          style={{
            whiteSpace: "pre-wrap",
            background: "#f9fafb",
            padding: "0.75rem",
            borderRadius: 6,
            border: "1px solid #e5e7eb",
          }}
        >
          {selected.template}
        </pre>
      ) : null}
    </div>
  );
}
