"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  width?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  empty?: ReactNode;
  className?: string;
}

export function Table<T>({
  columns,
  rows,
  rowKey,
  empty,
  className,
}: TableProps<T>) {
  if (rows.length === 0) {
    return (
      <div className="px-6 py-10 text-center text-sm text-muted">
        {empty ?? "데이터가 없습니다."}
      </div>
    );
  }
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-slate-50/80">
            {columns.map((c) => (
              <th
                key={c.key}
                style={{ width: c.width }}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className="border-b border-slate-100 transition hover:bg-slate-50/70"
            >
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3.5 align-middle text-slate-700">
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
