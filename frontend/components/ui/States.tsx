"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function LoadingState({ label = "불러오는 중…" }: { label?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-white px-6 py-10 text-center text-sm text-muted shadow-[var(--shadow-card)]">
      <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-brand/20 border-t-brand" />
      {label}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-border bg-slate-50/80 px-6 py-10 text-center text-sm text-muted">
      {children}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-danger-soft px-4 py-3 text-sm font-medium text-red-800">
      {message}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "succeeded" || status === "active" || status === "uploaded"
      ? "bg-success-soft text-success"
      : status === "failed" || status === "cancelled"
        ? "bg-danger-soft text-danger"
        : status === "running" || status === "queued"
          ? "bg-brand-soft text-brand"
          : "bg-slate-100 text-slate-600";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
        tone,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {status}
    </span>
  );
}
