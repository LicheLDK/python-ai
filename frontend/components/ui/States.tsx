"use client";

import type { CSSProperties, ReactNode } from "react";

const box: CSSProperties = {
  padding: "1.25rem",
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
  color: "#4b5563",
  textAlign: "center",
};

export function LoadingState({ label = "불러오는 중…" }: { label?: string }) {
  return <div style={box}>{label}</div>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div style={box}>{children}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div
      style={{
        ...box,
        borderColor: "#fecaca",
        background: "#fef2f2",
        color: "#991b1b",
      }}
    >
      {message}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const color =
    status === "succeeded" || status === "active"
      ? "#166534"
      : status === "failed" || status === "cancelled"
        ? "#991b1b"
        : status === "running" || status === "queued"
          ? "#1d4ed8"
          : "#4b5563";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.15rem 0.5rem",
        borderRadius: 999,
        fontSize: "0.75rem",
        fontWeight: 600,
        background: `${color}18`,
        color,
      }}
    >
      {status}
    </span>
  );
}
