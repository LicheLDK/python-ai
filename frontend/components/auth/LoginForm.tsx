"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ErrorState } from "@/components/ui/States";
import { ApiError } from "@/services/http";
import * as authApi from "@/services/auth";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.login({ email, password });
      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "로그인에 실패했습니다.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="grid w-full gap-4">
      <div className="mb-1 flex items-center gap-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-soft text-brand">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-bold">AI SaaS</div>
          <div className="text-xs text-muted">Sign in to continue</div>
        </div>
      </div>
      <h1 className="m-0 text-2xl font-bold tracking-tight">Login</h1>
      <Input
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <Input
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error ? <ErrorState message={error} /> : null}
      <Button type="submit" disabled={busy} className="w-full py-2.5">
        {busy ? "로그인 중…" : "로그인"}
      </Button>
      <p className="m-0 text-sm text-muted">
        계정이 없나요?{" "}
        <Link href="/register" className="font-semibold text-brand hover:underline">
          회원가입
        </Link>
      </p>
    </form>
  );
}
