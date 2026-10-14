"use client";

import { FileText, UploadCloud, X } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, buttonClass, Card, PageHeader } from "@/components/ui";
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
    <main className="mx-auto max-w-3xl px-6 py-10">
      <PageHeader title="Upload resumes" subtitle="PDF or Word files, up to 20 at a time." />

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
        className={`rounded-card border-2 border-dashed px-6 py-14 text-center transition ${
          dragging ? "border-accent bg-accent/5" : "border-line bg-white"
        }`}
      >
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 text-accent">
          <UploadCloud size={26} />
        </span>
        <p className="mt-4 font-medium">Drag and drop resumes here</p>
        <p className="mt-1 text-sm text-muted">PDF or DOCX, up to 10 MB each</p>
        <Button className="mt-5" variant="secondary" onClick={() => inputRef.current?.click()}>
          Choose files
        </Button>
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
        <ul className="mt-4 space-y-1 rounded-xl bg-red-50 p-4 text-sm text-red-700">
          {rejected.map((item, i) => (
            <li key={i}>
              <strong>{item.filename}</strong>: {item.detail}
            </li>
          ))}
        </ul>
      )}

      {files.length > 0 && (
        <section className="mt-6 space-y-4">
          <h2 className="font-semibold">Ready to upload ({files.length})</h2>
          <Card className="divide-y divide-black/5">
            {files.map((file) => (
              <div key={`${file.name}-${file.size}`} className="flex items-center gap-3 px-4 py-3 text-sm">
                <FileText size={18} className="shrink-0 text-muted" />
                <span className="flex-1 truncate">{file.name}</span>
                <span className="text-muted">{(file.size / 1024).toFixed(0)} KB</span>
                <button
                  onClick={() => setFiles(files.filter((f) => f !== file))}
                  disabled={uploading}
                  className="rounded-full p-1.5 text-muted hover:bg-black/[0.05] hover:text-red-600"
                  aria-label={`Remove ${file.name}`}
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </Card>
          <Button onClick={submit} disabled={uploading}>
            {uploading ? "Uploading…" : `Upload ${files.length} file${files.length > 1 ? "s" : ""}`}
          </Button>
        </section>
      )}

      {error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-700">Upload failed: {error}</p>}

      {results && (
        <section className="mt-6 space-y-4">
          <h2 className="font-semibold">Results</h2>
          <Card className="divide-y divide-black/5">
            {results.map((item, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-3 text-sm">
                <FileText size={18} className="shrink-0 text-muted" />
                <span className="flex-1 truncate">{item.filename}</span>
                {item.detail && <span className="hidden text-muted sm:inline">{item.detail}</span>}
                <StatusBadge
                  status={
                    item.status === "accepted"
                      ? "completed"
                      : item.status === "duplicate"
                        ? "queued"
                        : "failed"
                  }
                />
                <span className="w-20 text-right capitalize text-muted">{item.status}</span>
              </div>
            ))}
          </Card>
          <Link href="/resumes" className={buttonClass("secondary")}>
            View my resumes
          </Link>
        </section>
      )}
    </main>
  );
}