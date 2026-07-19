import {
  clearAccessToken,
  setAccessToken,
  setCurrentUser,
} from "@/lib/auth";
import { apiFetch } from "@/services/http";
import type { TokenResponse, UserRead } from "@/types";

export async function register(input: {
  email: string;
  password: string;
  name: string;
}): Promise<{ user: UserRead }> {
  return apiFetch<{ user: UserRead }>("/api/v1/auth/register", {
    method: "POST",
    body: input,
    skipAuth: true,
    skipRefresh: true,
  });
}

export async function login(input: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: input,
    skipAuth: true,
    skipRefresh: true,
  });
  setAccessToken(data.access_token);
  setCurrentUser(data.user);
  return data;
}

export async function refresh(): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    skipAuth: true,
    skipRefresh: true,
    csrf: true,
  });
  setAccessToken(data.access_token);
  setCurrentUser(data.user);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>("/api/v1/auth/logout", {
      method: "POST",
      skipRefresh: true,
      csrf: true,
    });
  } finally {
    clearAccessToken();
  }
}

export async function fetchCsrf(): Promise<string> {
  const data = await apiFetch<{ csrf_token: string }>("/api/v1/auth/csrf", {
    method: "GET",
    skipAuth: true,
    skipRefresh: true,
  });
  return data.csrf_token;
}
