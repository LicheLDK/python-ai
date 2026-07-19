/**
 * In-memory access-token store (ADR-029).
 * Refresh token stays in HttpOnly cookie; never write access tokens to localStorage.
 */

import type { UserRead } from "@/types";

let accessToken: string | null = null;
let currentUser: UserRead | null = null;

type Listener = () => void;
const listeners = new Set<Listener>();

function notify(): void {
  listeners.forEach((fn) => fn());
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  notify();
}

export function clearAccessToken(): void {
  accessToken = null;
  currentUser = null;
  notify();
}

export function getCurrentUser(): UserRead | null {
  return currentUser;
}

export function setCurrentUser(user: UserRead | null): void {
  currentUser = user;
  notify();
}

export function subscribeAuth(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Read non-HttpOnly csrf_token cookie (path=/api/v1/auth). */
export function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_token="));
  if (!match) return null;
  return decodeURIComponent(match.slice("csrf_token=".length));
}
