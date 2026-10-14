import { apiFetch } from "@/lib/api";
import type { AdminUser, AdminUserListResponse, CreateUserInput } from "@/types/api";

export function listUsers(query: string): Promise<AdminUserListResponse> {
  return apiFetch<AdminUserListResponse>(`/admin/users?${query}`);
}

export function createUser(input: CreateUserInput): Promise<AdminUser> {
  return apiFetch<AdminUser>("/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}