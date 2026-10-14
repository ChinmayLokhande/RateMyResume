"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
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
  { label: "Actions" },
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

  // Wait 300 ms after typing stops before searching
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
        if (request !== latest.current) return; // a newer request replaced this one
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

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">My resumes</h1>

      <div className="flex flex-wrap gap-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search by name or email"
          maxLength={100}
          className="w-72 rounded border px-3 py-2"
          aria-label="Search by name or email"
        />
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="rounded border px-3 py-2"
          aria-label="Filter by processing status"
        >
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {error && <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
      {actionError && <p className="rounded bg-red-50 p-3 text-red-700">{actionError}</p>}
      {!data && !error && <p className="text-gray-500">Loading…</p>}

      {data && data.items.length === 0 && (
        <p className="rounded border border-dashed p-8 text-center text-gray-500">
          {q || status ? "No resumes match your filters." : "No resumes yet. Upload one to get started."}
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {COLUMNS.map((column) => (
                    <th key={column.label} className="whitespace-nowrap px-3 py-2 font-medium">
                      {column.sort ? (
                        <button onClick={() => toggleSort(column.sort!)} className="hover:underline">
                          {column.label}
                          {sort === column.sort ? (direction === "asc" ? " ▲" : " ▼") : ""}
                        </button>
                      ) : (
                        column.label
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-2">
                      <Link
                        href={`/resumes/${item.id}`}
                        className="font-medium text-blue-700 hover:underline"
                      >
                        {item.candidate_name ?? item.original_filename}
                      </Link>
                      <div className="max-w-[14rem] truncate text-xs text-gray-500">
                        {item.original_filename}
                      </div>
                    </td>
                    <td className="px-3 py-2">{item.email ?? "—"}</td>
                    <td className="px-3 py-2">{item.mobile ?? "—"}</td>
                    <td className="px-3 py-2">{item.location ?? "—"}</td>
                    <td className="max-w-[14rem] px-3 py-2">
                      {item.skills.length === 0
                        ? "—"
                        : item.skills.slice(0, 3).join(", ") +
                          (item.skills.length > 3 ? ` +${item.skills.length - 3}` : "")}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {new Date(item.uploaded_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={item.extraction_status} />
                      {item.error_message && (
                        <div className="mt-1 max-w-[12rem] text-xs text-gray-500">{item.error_message}</div>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={item.analysis_status} />
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">
                      {item.extraction_status === "failed" && (
                        <button
                          onClick={() => runAction(() => retryResume(item.id))}
                          className="mr-3 text-blue-700 hover:underline"
                        >
                          Retry
                        </button>
                      )}
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete ${item.original_filename}? This cannot be undone.`))
                            void runAction(() => deleteResume(item.id));
                        }}
                        className="text-red-700 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">
              {data.total} resume{data.total === 1 ? "" : "s"} · page {data.page} of {data.total_pages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="rounded border px-3 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= data.total_pages}
                className="rounded border px-3 py-1.5 disabled:opacity-40"
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