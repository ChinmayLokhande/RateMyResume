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

function messageFrom(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : "Invalid input",
      )
      .join("; ");
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return fallback;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const keycloak = getKeycloak();
  await keycloak.updateToken(30).catch(() => keycloak.login()); // refresh, or sign in again

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${keycloak.token}`);

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // the error body was not JSON, so keep the status text
    }
    throw new ApiError(response.status, messageFrom(body, response.statusText));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}