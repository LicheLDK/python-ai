import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/hooks/useAuth";

export const metadata: Metadata = {
  title: "AI SaaS Framework",
  description: "AI-first document OCR / chat / pipeline console",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          background: "#f3f4f6",
          color: "#111827",
          fontFamily:
            '"Segoe UI", "Noto Sans KR", system-ui, -apple-system, sans-serif',
        }}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
