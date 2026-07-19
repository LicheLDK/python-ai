"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { AdminGuard } from "@/components/layout/Guards";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminGuard>
      <AppShell admin>{children}</AppShell>
    </AdminGuard>
  );
}
