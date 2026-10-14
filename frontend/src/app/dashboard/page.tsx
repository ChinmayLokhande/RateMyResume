"use client";

import { AlertTriangle, CheckCircle2, FileText, Inbox, Loader, UploadCloud } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { Avatar, buttonClass, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { getDashboardStats } from "@/lib/dashboard";
import type { DashboardStats } from "@/types/api";

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "The dashboard is for regular user accounts. Admin accounts do not have access to resumes.";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

function StatCard({
  icon,
  label,
  value,
  tint,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  tint: string;
}) {
  return (
    <Card className="p-5">
      <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tint}`}>{icon}</span>
      <div className="mt-4 text-4xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1 text-sm text-muted">{label}</div>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    () =>
      getDashboardStats()
        .then((result) => {
          setStats(result);
          setError(null);
        })
        .catch((err: unknown) => setError(describeError(err))),
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const processing = (stats?.in_progress ?? 0) > 0;
  useEffect(() => {
    if (!processing) return;
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [processing, load]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Dashboard"
        subtitle="A quick look at your resumes."
        action={
          <Link href="/upload" className={buttonClass("primary")}>
            <UploadCloud size={16} />
            Upload
          </Link>
        }
      />

      {error && <p className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}

      {!stats && !error && (
        <div className="space-y-6">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((n) => (
              <Skeleton key={n} className="h-36" />
            ))}
          </div>
          <Skeleton className="h-64" />
        </div>
      )}

      {stats && (
        <div className="space-y-8">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={<FileText size={20} />}
              label="Total uploaded"
              value={stats.total}
              tint="bg-accent/10 text-accent"
            />
            <StatCard
              icon={<CheckCircle2 size={20} />}
              label="Processed"
              value={stats.completed}
              tint="bg-green-50 text-green-700"
            />
            <StatCard
              icon={<Loader size={20} className={stats.in_progress > 0 ? "animate-spin" : ""} />}
              label="In progress"
              value={stats.in_progress}
              tint="bg-blue-50 text-blue-700"
            />
            <StatCard
              icon={<AlertTriangle size={20} />}
              label="Failed"
              value={stats.failed}
              tint="bg-red-50 text-red-700"
            />
          </div>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">Recently uploaded</h2>
              {stats.total > 0 && (
                <Link href="/resumes" className="text-sm text-accent hover:underline">
                  View all
                </Link>
              )}
            </div>
            {stats.recent.length === 0 ? (
              <EmptyState
                icon={<Inbox size={26} />}
                title="No resumes yet"
                text="Upload your first resume and it will show up here."
                action={
                  <Link href="/upload" className={buttonClass("primary")}>
                    Upload resumes
                  </Link>
                }
              />
            ) : (
              <Card className="divide-y divide-black/5">
                {stats.recent.map((item) => (
                  <Link
                    key={item.id}
                    href={`/resumes/${item.id}`}
                    className="flex items-center gap-4 px-5 py-3.5 transition first:rounded-t-card last:rounded-b-card hover:bg-black/[0.02]"
                  >
                    <Avatar name={item.candidate_name ?? item.original_filename} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">
                        {item.candidate_name ?? "Unnamed candidate"}
                      </div>
                      <div className="truncate text-xs text-muted">{item.original_filename}</div>
                    </div>
                    <span className="hidden text-sm text-muted sm:inline">
                      {new Date(item.uploaded_at).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                    <StatusBadge status={item.extraction_status} />
                  </Link>
                ))}
              </Card>
            )}
          </section>
        </div>
      )}
    </main>
  );
}