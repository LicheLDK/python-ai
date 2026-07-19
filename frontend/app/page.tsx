"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoadingState } from "@/components/ui/States";
import { useAuth } from "@/hooks/useAuth";

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(isAuthenticated ? "/dashboard" : "/login");
  }, [loading, isAuthenticated, router]);

  return <LoadingState label="이동 중…" />;
}
