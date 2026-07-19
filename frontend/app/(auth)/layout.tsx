import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "1.5rem",
        background:
          "linear-gradient(160deg, #eef2ff 0%, #f3f4f6 45%, #ecfeff 100%)",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 12,
          padding: "1.75rem",
          boxShadow: "0 8px 28px rgba(15,23,42,0.08)",
          width: "100%",
          maxWidth: 420,
        }}
      >
        {children}
      </div>
    </div>
  );
}
