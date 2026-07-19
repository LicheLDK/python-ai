"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import {
  Bot,
  FileText,
  LayoutDashboard,
  LogOut,
  ScanText,
  Sparkles,
  Workflow,
  Shield,
  Users,
  Activity,
  History,
  ClipboardList,
  MessageSquareText,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/cn";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/ocr", label: "OCR", icon: ScanText },
  { href: "/ai", label: "AI", icon: Bot },
  { href: "/pipelines", label: "Pipelines", icon: Workflow },
];

const adminItems = [
  { href: "/admin", label: "Admin home", icon: Shield },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/usage", label: "AI usage", icon: Activity },
  { href: "/admin/ocr", label: "OCR history", icon: History },
  { href: "/admin/audit", label: "Audit", icon: ClipboardList },
  { href: "/admin/prompts", label: "Prompts", icon: MessageSquareText },
];

function NavLink({
  href,
  label,
  icon: Icon,
  active,
}: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
        active
          ? "bg-brand text-white shadow-sm shadow-brand/30"
          : "text-sidebar-muted hover:bg-sidebar-hover hover:text-white",
      )}
    >
      <Icon className="h-4 w-4 shrink-0 opacity-90" />
      {label}
    </Link>
  );
}

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
    <div className="grid min-h-screen grid-cols-[240px_1fr] bg-surface">
      <aside className="flex flex-col gap-1 bg-sidebar px-3 py-5 text-white">
        <div className="mb-5 flex items-center gap-2.5 px-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/20 text-brand">
            <Sparkles className="h-4 w-4 text-indigo-300" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight">AI SaaS</div>
            <div className="text-[11px] text-sidebar-muted">Framework</div>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          {items.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <NavLink
                key={item.href}
                href={item.href}
                label={item.label}
                icon={item.icon}
                active={
                  item.href === "/admin"
                    ? pathname === "/admin"
                    : active
                }
              />
            );
          })}
        </nav>

        <div className="mt-auto space-y-3 pt-6">
          {!admin && user?.role === "admin" ? (
            <div>
              <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Admin
              </div>
              <Link
                href="/admin"
                className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-sidebar-muted transition hover:bg-sidebar-hover hover:text-white"
              >
                <Shield className="h-4 w-4" />
                Admin console
              </Link>
            </div>
          ) : null}
          {admin ? (
            <Link
              href="/dashboard"
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-sidebar-muted transition hover:bg-sidebar-hover hover:text-white"
            >
              <LayoutDashboard className="h-4 w-4" />
              Back to app
            </Link>
          ) : null}

          <div className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/5 px-2.5 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/30 text-xs font-bold text-indigo-100">
              {(user?.email?.[0] ?? "U").toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium text-slate-200">
                {user?.email}
              </div>
              <div className="text-[10px] text-sidebar-muted">{user?.role}</div>
            </div>
            <button
              type="button"
              title="Logout"
              className="rounded-lg p-1.5 text-sidebar-muted transition hover:bg-white/10 hover:text-white"
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
      <main className="min-w-0 px-6 py-6 md:px-8">{children}</main>
    </div>
  );
}
