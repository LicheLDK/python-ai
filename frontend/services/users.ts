import { apiFetch } from "@/services/http";
import type { UserRead } from "@/types";

export async function getMe(): Promise<UserRead> {
  return apiFetch<UserRead>("/api/v1/users/me");
}

export async function updateMe(input: { name: string }): Promise<UserRead> {
  return apiFetch<UserRead>("/api/v1/users/me", {
    method: "PATCH",
    body: input,
  });
}
