"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
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
    <form
      onSubmit={onSubmit}
      style={{ display: "grid", gap: "0.85rem", maxWidth: 380, width: "100%" }}
    >
      <h1 style={{ margin: 0 }}>Login</h1>
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
      <Button type="submit" disabled={busy}>
        {busy ? "로그인 중…" : "로그인"}
      </Button>
      <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
        계정이 없나요? <Link href="/register">회원가입</Link>
      </p>
    </form>
  );
}
