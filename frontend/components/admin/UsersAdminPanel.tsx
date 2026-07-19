"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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
import type { UserRead } from "@/types";

export function UsersAdminPanel() {
  const [rows, setRows] = useState<UserRead[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [edit, setEdit] = useState<UserRead | null>(null);
  const [name, setName] = useState("");
  const [role, setRole] = useState("user");
  const [status, setStatus] = useState("active");
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await adminApi.listUsers({ q: q || undefined, page_size: 50 });
      setRows(page.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "목록 조회 실패");
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    void reload();
  }, [reload]);

  function openEdit(u: UserRead) {
    setEdit(u);
    setName(u.name);
    setRole(u.role);
    setStatus(u.status === "suspended" ? "inactive" : u.status);
  }

  async function save() {
    if (!edit) return;
    setSaving(true);
    try {
      await adminApi.patchUser(edit.id, { name, role, status });
      setEdit(null);
      await reload();
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "저장 실패");
    } finally {
      setSaving(false);
    }
  }

  const columns: Column<UserRead>[] = [
    { key: "email", header: "Email", render: (r) => r.email },
    { key: "name", header: "Name", render: (r) => r.name },
    {
      key: "role",
      header: "Role",
      render: (r) => <StatusBadge status={r.role} />,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "actions",
      header: "",
      render: (r) => (
        <Button variant="secondary" onClick={() => openEdit(r)}>
          Edit
        </Button>
      ),
    },
  ];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <Input
          label="Search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="email / name"
          style={{ minWidth: 240 }}
        />
        <Button
          variant="secondary"
          style={{ alignSelf: "end" }}
          onClick={() => void reload()}
        >
          Refresh
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
            empty={<EmptyState>사용자가 없습니다.</EmptyState>}
          />
        </div>
      ) : null}

      <Modal
        open={!!edit}
        title="Edit user"
        onClose={() => setEdit(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEdit(null)}>
              Cancel
            </Button>
            <Button onClick={() => void save()} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </>
        }
      >
        <div style={{ display: "grid", gap: "0.75rem" }}>
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Role</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{ padding: "0.5rem", borderRadius: 6 }}
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <label style={{ display: "grid", gap: "0.35rem" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              style={{ padding: "0.5rem", borderRadius: 6 }}
            >
              <option value="active">active</option>
              <option value="inactive">inactive</option>
            </select>
          </label>
        </div>
      </Modal>
    </div>
  );
}
