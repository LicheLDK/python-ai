import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen place-items-center bg-[radial-gradient(ellipse_at_top,_#eef2ff_0%,_#f8fafc_45%,_#f1f5f9_100%)] p-6">
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-7 shadow-[var(--shadow-card)]">
        {children}
      </div>
    </div>
  );
}
