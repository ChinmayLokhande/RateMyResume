import { apiFetch } from "@/lib/api";
import type { DashboardStats } from "@/types/api";

export function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/dashboard/stats");
}