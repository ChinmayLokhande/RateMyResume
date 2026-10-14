"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { uploadResumes } from "@/lib/resumes";
import type { UploadItemResult } from "@/types/api";

const MAX_FILES = 20;
const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = [".pdf", ".docx"];

// Convenience only: the server re-checks type and size on every upload.
function problemWith(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => name.endsWith(ext))) return "Only PDF and DOCX files are supported";
  if (file.size === 0) return "File is empty";
  if (file.size > MAX_BYTES) return "File is larger than 10 MB";
  return null;
}

export default function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [rejected, setRejected] = useState<UploadItemResult[]>([]);
  const [results, setResults] = useState<UploadItemResult[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | File[]) {
    const accepted: File[] = [...files];
    const bad: UploadItemResult[] = [];
    for (const file of Array.from(incoming)) {
      const problem = problemWith(file);
      if (problem) {
        bad.push({ filename: file.name, status: "rejected", resume_id: null, detail: problem });
      } else if (accepted.length >= MAX_FILES) {
        bad.push({
          filename: file.name,
          status: "rejected",
          resume_id: null,
          detail: `At most ${MAX_FILES} files at a time`,
        });
      } else if (!accepted.some((f) => f.name === file.name && f.size === file.size)) {
        accepted.push(file);
      }
    }
    setFiles(accepted);
    setRejected(bad);
    setResults(null);
    setError(null);
  }

  async function submit() {
    setUploading(true);
    setError(null);
    try {
      setResults(await uploadResumes(files));
      setFiles([]);
      setRejected([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Upload resumes</h1>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        className={`rounded-lg border-2 border-dashed p-10 text-center ${
          dragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
        }`}
      >
        <p className="text-gray-700">Drag and drop PDF or DOCX files here</p>
        <p className="mt-1 text-sm text-gray-500">
          Up to {MAX_FILES} files, 10 MB each
        </p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 rounded border px-4 py-2 hover:bg-gray-50"
        >
          Choose files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {rejected.length > 0 && (
        <ul className="space-y-1 text-sm text-red-700">
          {rejected.map((item, i) => (
            <li key={i}>
              {item.filename}: {item.detail}
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium">Ready to upload ({files.length})</h2>
          <ul className="divide-y rounded border">
            {files.map((file) => (
              <li key={`${file.name}-${file.size}`} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span className="flex-1 truncate">{file.name}</span>
                <span className="text-gray-500">{(file.size / 1024).toFixed(0)} KB</span>
                <button
                  onClick={() => setFiles(files.filter((f) => f !== file))}
                  disabled={uploading}
                  className="text-gray-500 hover:text-red-600"
                  aria-label={`Remove ${file.name}`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
          <button
            onClick={submit}
            disabled={uploading}
            className="rounded bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {uploading ? "Uploading…" : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
          </button>
        </section>
      )}

      {error && <p className="text-red-600">Upload failed: {error}</p>}

      {results && (
        <section className="space-y-3">
          <h2 className="font-medium">Results</h2>
          <ul className="divide-y rounded border">
            {results.map((item, i) => (
              <li key={i} className="flex items-center gap-3 px-3 py-2 text-sm">
                <span className="flex-1 truncate">{item.filename}</span>
                {item.detail && <span className="text-gray-500">{item.detail}</span>}
                <StatusBadge
                  status={
                    item.status === "accepted"
                      ? "completed"
                      : item.status === "duplicate"
                        ? "queued"
                        : "failed"
                  }
                />
                <span className="w-20 text-right capitalize">{item.status}</span>
              </li>
            ))}
          </ul>
          <Link href="/resumes" className="inline-block text-blue-700 underline">
            View my resumes
          </Link>
        </section>
      )}
    </main>
  );
}