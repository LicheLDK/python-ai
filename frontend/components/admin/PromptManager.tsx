"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
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
import * as aiApi from "@/services/ai";
import type { PromptRead } from "@/types";

export function PromptManager() {
  const [rows, setRows] = useState<PromptRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("");
  const [activate, setActivate] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await aiApi.listPrompts({ page_size: 50 });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "프롬프트 조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !template.trim()) return;
    setBusy(true);
    try {
      await aiApi.createPrompt({
        name: name.trim(),
        template: template.trim(),
        activate,
      });
      setName("");
      setTemplate("");
      await reload();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "생성 실패");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<PromptRead>[] = [
    { key: "name", header: "Name", render: (r) => r.name },
    { key: "ver", header: "Ver", render: (r) => r.version },
    {
      key: "active",
      header: "Active",
      render: (r) => (
        <StatusBadge status={r.active ? "active" : "inactive"} />
      ),
    },
    {
      key: "actions",
      header: "",
      render: (r) => (
        <div style={{ display: "flex", gap: "0.35rem" }}>
          {!r.active ? (
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await aiApi.activatePrompt(r.id);
                  await reload();
                } catch (e) {
                  alert(e instanceof ApiError ? e.message : "활성화 실패");
                }
              }}
            >
              Activate
            </Button>
          ) : null}
          <Button
            variant="secondary"
            onClick={async () => {
              const next = prompt("New template (creates new version)", r.template);
              if (next == null || !next.trim()) return;
              try {
                await aiApi.updatePrompt(r.id, {
                  template: next.trim(),
                  create_new_version: true,
                });
                await reload();
              } catch (e) {
                alert(e instanceof ApiError ? e.message : "버전 생성 실패");
              }
            }}
          >
            New version
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1.25rem" }}>
      <form
        onSubmit={onCreate}
        style={{
          display: "grid",
          gap: "0.75rem",
          background: "#fff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: "1rem",
        }}
      >
        <h3 style={{ margin: 0 }}>Create prompt</h3>
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <label style={{ display: "grid", gap: "0.35rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Template</span>
          <textarea
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            required
            rows={5}
            style={{
              padding: "0.55rem",
              borderRadius: 6,
              border: "1px solid #d1d5db",
              fontFamily: "inherit",
            }}
          />
        </label>
        <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="checkbox"
            checked={activate}
            onChange={(e) => setActivate(e.target.checked)}
          />
          Activate immediately
        </label>
        <Button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create"}
        </Button>
      </form>

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
            empty={<EmptyState>프롬프트가 없습니다.</EmptyState>}
          />
        </div>
      ) : null}
    </div>
  );
}
