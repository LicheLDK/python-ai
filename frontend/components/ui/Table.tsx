"use client";

import type { CSSProperties, ReactNode } from "react";

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.9rem",
};

const thStyle: CSSProperties = {
  textAlign: "left",
  padding: "0.65rem 0.75rem",
  borderBottom: "2px solid #e5e7eb",
  color: "#4b5563",
  fontWeight: 600,
  background: "#f9fafb",
};

const tdStyle: CSSProperties = {
  padding: "0.65rem 0.75rem",
  borderBottom: "1px solid #f3f4f6",
  verticalAlign: "top",
};

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
}

export function Table<T>({ columns, rows, rowKey, empty }: TableProps<T>) {
  if (rows.length === 0) {
    return (
      <div style={{ padding: "1.5rem", color: "#6b7280", textAlign: "center" }}>
        {empty ?? "데이터가 없습니다."}
      </div>
    );
  }
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={{ ...thStyle, width: c.width }}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((c) => (
                <td key={c.key} style={tdStyle}>
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
