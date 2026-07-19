"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { LoadingState } from "@/components/ui/States";
import { useAuth } from "@/hooks/useAuth";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [loading, isAuthenticated, router]);

  if (loading) return <LoadingState label="세션 확인 중…" />;
  if (!isAuthenticated) return <LoadingState label="로그인 페이지로 이동…" />;
  return <>{children}</>;
}

export function AdminGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (!isAdmin) {
      router.replace("/dashboard");
    }
  }, [loading, isAuthenticated, isAdmin, router]);

  if (loading) return <LoadingState label="권한 확인 중…" />;
  if (!isAuthenticated || !isAdmin) {
    return <LoadingState label="접근 권한이 없습니다…" />;
  }
  return <>{children}</>;
}
