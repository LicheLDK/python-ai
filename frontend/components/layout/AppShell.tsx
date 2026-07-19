"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { CSSProperties, ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/hooks/useAuth";

const shell: CSSProperties = {
  minHeight: "100vh",
  display: "grid",
  gridTemplateColumns: "220px 1fr",
  background: "#f3f4f6",
  color: "#111827",
  fontFamily:
    '"Segoe UI", "Noto Sans KR", system-ui, -apple-system, sans-serif',
};

const side: CSSProperties = {
  background: "#111827",
  color: "#f9fafb",
  padding: "1.25rem 1rem",
  display: "flex",
  flexDirection: "column",
  gap: "0.35rem",
};

const main: CSSProperties = {
  padding: "1.5rem 1.75rem",
  maxWidth: 1100,
  width: "100%",
};

const linkBase: CSSProperties = {
  display: "block",
  padding: "0.55rem 0.7rem",
  borderRadius: 6,
  color: "#e5e7eb",
  textDecoration: "none",
  fontSize: "0.92rem",
};

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/documents", label: "Documents" },
  { href: "/ocr", label: "OCR" },
  { href: "/ai", label: "AI" },
  { href: "/pipelines", label: "Pipelines" },
];

const adminItems = [
  { href: "/admin", label: "Admin home" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/usage", label: "AI usage" },
  { href: "/admin/ocr", label: "OCR history" },
  { href: "/admin/audit", label: "Audit" },
  { href: "/admin/prompts", label: "Prompts" },
];

export function AppShell({
  children,
  admin = false,
}: {
  children: ReactNode;
  admin?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const items = admin ? adminItems : navItems;

  return (
    <div style={shell}>
      <aside style={side}>
        <div style={{ marginBottom: "1rem" }}>
          <div style={{ fontWeight: 700, fontSize: "1rem" }}>AI SaaS</div>
          <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>
            {user?.email}
          </div>
        </div>
        {items.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                ...linkBase,
                background: active ? "#1f2937" : "transparent",
                fontWeight: active ? 700 : 500,
              }}
            >
              {item.label}
            </Link>
          );
        })}
        <div style={{ flex: 1 }} />
        {!admin && user?.role === "admin" ? (
          <Link href="/admin" style={linkBase}>
            Admin →
          </Link>
        ) : null}
        {admin ? (
          <Link href="/dashboard" style={linkBase}>
            ← App
          </Link>
        ) : null}
        <Button
          variant="secondary"
          style={{ marginTop: "0.5rem", width: "100%" }}
          onClick={async () => {
            await logout();
            router.replace("/login");
          }}
        >
          Logout
        </Button>
      </aside>
      <main style={main}>{children}</main>
    </div>
  );
}
