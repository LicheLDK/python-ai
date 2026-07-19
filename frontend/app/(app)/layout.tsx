"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { AuthGuard } from "@/components/layout/Guards";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
