import { getKeycloak } from "@/lib/keycloak";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const keycloak = getKeycloak();
  await keycloak.updateToken(30).catch(() => keycloak.login()); // refresh, or sign in again

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${keycloak.token}`);

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : (body.detail?.message ?? message);
    } catch {
      // the error body was not JSON, so keep the status text
    }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}