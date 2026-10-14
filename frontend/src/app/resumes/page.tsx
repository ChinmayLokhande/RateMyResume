"use client";

import { ChevronDown, ChevronUp, Inbox, RotateCw, Search, Trash2, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Avatar,
  buttonClass,
  Card,
  EmptyState,
  inputClass,
  PageHeader,
  Skeleton,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { deleteResume, listResumes, retryResume } from "@/lib/resumes";
import type { ResumeListResponse } from "@/types/api";

const PAGE_SIZE = 10;
type SortKey = "uploaded_at" | "candidate_name" | "email" | "extraction_status";

const COLUMNS: { label: string; sort?: SortKey }[] = [
  { label: "Candidate", sort: "candidate_name" },
  { label: "Email", sort: "email" },
  { label: "Mobile" },
  { label: "Location" },
  { label: "Skills" },
  { label: "Uploaded", sort: "uploaded_at" },
  { label: "Processing", sort: "extraction_status" },
  { label: "Analysis" },
  { label: "" },
];

const FILTERS = [
  { value: "", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "processing", label: "Processing" },
  { value: "queued", label: "Queued" },
  { value: "failed", label: "Failed" },
];

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "This area is for regular user accounts. Admin accounts do not have access to resumes.";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

export default function ResumesPage() {
  const [input, setInput] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<SortKey>("uploaded_at");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ResumeListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const latest = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(input.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [input]);

  const query = useMemo(() => {
    const params = new URLSearchParams({
      sort,
      direction,
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    return params.toString();
  }, [q, status, sort, direction, page]);

  const load = useCallback(() => {
    const request = ++latest.current;
    return listResumes(query)
      .then((result) => {
        if (request !== latest.current) return;
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        if (request === latest.current) setError(describeError(err));
      });
  }, [query]);

  useEffect(() => {
    void load();
  }, [load]);

  const hasActive = data?.items.some((item) =>
    [item.extraction_status, item.analysis_status].some((s) => s === "queued" || s === "processing"),
  );
  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(() => void load(), 4000);
    return () => clearInterval(timer);
  }, [hasActive, load]);

  function toggleSort(key: SortKey) {
    if (key === sort) setDirection(direction === "asc" ? "desc" : "asc");
    else {
      setSort(key);
      setDirection(key === "uploaded_at" ? "desc" : "asc");
    }
    setPage(1);
  }

  async function runAction(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      await load();
    } catch (err) {
      setActionError(describeError(err));
    }
  }

  const filtered = Boolean(q || status);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <PageHeader
        title="Resumes"
        subtitle="Everything you have uploaded, with live processing status."
        action={
          <Link href="/upload" className={buttonClass("primary")}>
            <UploadCloud size={16} />
            Upload
          </Link>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-xs">
          <Search size={16} className="pointer-events-none absolute left-3.5 top-3 text-muted" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search by name or email"
            maxLength={100}
            aria-label="Search by name or email"
            className={`${inputClass} pl-10`}
          />
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by processing status">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              aria-pressed={status === filter.value}
              onClick={() => {
                setStatus(filter.value);
                setPage(1);
              }}
              className={`rounded-full px-3.5 py-1.5 text-sm transition ${
                status === filter.value
                  ? "bg-ink text-white"
                  : "bg-white text-muted ring-1 ring-inset ring-line hover:text-ink"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}
      {actionError && <p className="mb-4 rounded-xl bg-red-50 p-3 text-red-700">{actionError}</p>}

      {!data && !error && (
        <Card className="space-y-3 p-5">
          {[0, 1, 2, 3].map((n) => (
            <Skeleton key={n} className="h-12 w-full" />
          ))}
        </Card>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          icon={<Inbox size={26} />}
          title={filtered ? "No resumes match" : "No resumes yet"}
          text={
            filtered
              ? "Try a different search or filter."
              : "Upload your first resume and it will appear here as it is processed."
          }
          action={
            !filtered && (
              <Link href="/upload" className={buttonClass("primary")}>
                Upload resumes
              </Link>
            )
          }
        />
      )}

      {data && data.items.length > 0 && (
        <>
          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-black/5 text-xs uppercase tracking-wide text-muted">
                  {COLUMNS.map((column, i) => (
                    <th key={i} className="whitespace-nowrap px-4 py-3 font-medium">
                      {column.sort ? (
                        <button
                          onClick={() => toggleSort(column.sort!)}
                          className="inline-flex items-center gap-1 uppercase hover:text-ink"
                        >
                          {column.label}
                          {sort === column.sort &&
                            (direction === "asc" ? <ChevronUp size={13} /> : <ChevronDown size={13} />)}
                        </button>
                      ) : (
                        column.label
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-black/5">
                {data.items.map((item) => (
                  <tr key={item.id} className="transition hover:bg-black/[0.02]">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar name={item.candidate_name ?? item.original_filename} />
                        <div className="min-w-0">
                          <Link
                            href={`/resumes/${item.id}`}
                            className="font-medium hover:text-accent hover:underline"
                          >
                            {item.candidate_name ?? "Unnamed candidate"}
                          </Link>
                          <div className="max-w-[13rem] truncate text-xs text-muted">
                            {item.original_filename}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">{item.email ?? "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3">{item.mobile ?? "—"}</td>
                    <td className="px-4 py-3">{item.location ?? "—"}</td>
                    <td className="px-4 py-3">
                      {item.skills.length === 0 ? (
                        "—"
                      ) : (
                        <div className="flex max-w-[16rem] flex-wrap gap-1">
                          {item.skills.slice(0, 3).map((skill) => (
                            <span key={skill} className="rounded-full bg-black/[0.05] px-2 py-0.5 text-xs">
                              {skill}
                            </span>
                          ))}
                          {item.skills.length > 3 && (
                            <span className="px-1 text-xs text-muted">+{item.skills.length - 3}</span>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-muted">
                      {new Date(item.uploaded_at).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.extraction_status} />
                      {item.error_message && (
                        <div className="mt-1 max-w-[12rem] text-xs text-muted">{item.error_message}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.analysis_status} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {item.extraction_status === "failed" && (
                        <button
                          onClick={() => void runAction(() => retryResume(item.id))}
                          title="Retry processing"
                          aria-label={`Retry ${item.original_filename}`}
                          className="rounded-full p-2 text-accent hover:bg-accent/10"
                        >
                          <RotateCw size={16} />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete ${item.original_filename}? This cannot be undone.`))
                            void runAction(() => deleteResume(item.id));
                        }}
                        title="Delete"
                        aria-label={`Delete ${item.original_filename}`}
                        className="rounded-full p-2 text-muted hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted">
              {data.total} resume{data.total === 1 ? "" : "s"} · page {data.page} of {data.total_pages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className={buttonClass("secondary")}
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.total_pages}
                className={buttonClass("secondary")}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </main>
  );
}