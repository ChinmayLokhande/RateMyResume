"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiError } from "@/lib/api";
import { analyzeResume, getAnalysis, getResume } from "@/lib/resumes";
import type { AnalysisResponse, ResumeDetail } from "@/types/api";

const ACTIVE = ["queued", "processing"];

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "This area is for regular user accounts. Admin accounts do not have access to resumes.";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase text-gray-500">{label}</dt>
      <dd>{value ?? "—"}</dd>
    </div>
  );
}

function BulletList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="font-medium">{title}</h4>
      <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function Chips({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="font-medium">{title}</h4>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className="rounded bg-gray-100 px-2 py-0.5 text-xs">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function ResumeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const detail = await getResume(id);
      let latest: AnalysisResponse | null = null;
      try {
        latest = await getAnalysis(id);
      } catch (err) {
        // 404 only means "no analysis yet"; anything else is a real error
        if (!(err instanceof ApiError && err.status === 404)) throw err;
      }
      setResume(detail);
      setAnalysis(latest);
      setError(null);
    } catch (err) {
      setError(describeError(err));
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const active =
    resume !== null &&
    (ACTIVE.includes(resume.extraction_status) || ACTIVE.includes(resume.analysis_status));
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => void load(), 4000);
    return () => clearInterval(timer);
  }, [active, load]);

  async function runAnalysis() {
    setActionError(null);
    try {
      await analyzeResume(id);
      await load();
    } catch (err) {
      setActionError(describeError(err));
    }
  }

  if (error) {
    return (
      <main className="mx-auto max-w-4xl space-y-3 p-6">
        <Link href="/resumes" className="text-blue-700 hover:underline">
          ← Back to resumes
        </Link>
        <p className="rounded bg-red-50 p-3 text-red-700">{error}</p>
      </main>
    );
  }
  if (!resume) return <p className="p-6 text-gray-500">Loading…</p>;

  const canAnalyze =
    resume.extraction_status === "completed" && !ACTIVE.includes(resume.analysis_status);
  const detail = analysis?.detailed_result;
  const narrative = detail?.narrative ?? null;

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <Link href="/resumes" className="text-blue-700 hover:underline">
        ← Back to resumes
      </Link>

      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">{resume.candidate_name ?? resume.original_filename}</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
          <span>{resume.original_filename}</span>
          <span>·</span>
          <span>Uploaded {new Date(resume.uploaded_at).toLocaleString()}</span>
          <StatusBadge status={resume.extraction_status} />
          <StatusBadge status={resume.analysis_status} />
        </div>
        {resume.error_message && <p className="text-sm text-gray-600">{resume.error_message}</p>}
      </header>

      <section className="space-y-3 rounded border p-4">
        <h2 className="font-medium">Extracted details</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Field label="Email" value={resume.email} />
          <Field label="Mobile" value={resume.mobile} />
          <Field label="Location" value={resume.location} />
          <Field
            label="Read by"
            value={
              resume.extraction_method === "ocr"
                ? "OCR (scanned document)"
                : resume.extraction_method === "native_text"
                  ? "Text extraction"
                  : null
            }
          />
        </dl>
        <Chips title="Skills" items={resume.skills} />
      </section>

      <section className="space-y-4 rounded border p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-medium">Analysis</h2>
          <button
            onClick={runAnalysis}
            disabled={!canAnalyze}
            className="rounded border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-40"
          >
            {ACTIVE.includes(resume.analysis_status)
              ? "Analysis running…"
              : analysis
                ? "Re-run analysis"
                : "Run analysis"}
          </button>
        </div>
        {actionError && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{actionError}</p>}
        {resume.analysis_status === "failed" && (
          <p className="rounded bg-amber-50 p-2 text-sm text-amber-800">
            The latest analysis run failed.
            {analysis ? " Showing the previous result." : " You can try again."}
          </p>
        )}

        {!analysis && resume.extraction_status !== "completed" && (
          <p className="text-sm text-gray-500">Analysis becomes available once extraction finishes.</p>
        )}
        {!analysis && resume.extraction_status === "completed" && !ACTIVE.includes(resume.analysis_status) && (
          <p className="text-sm text-gray-500">No analysis yet.</p>
        )}

        {analysis && detail && (
          <div className="space-y-5">
            <div>
              <div className="text-4xl font-semibold">
                {analysis.score ?? "—"}
                <span className="text-lg font-normal text-gray-500"> / {detail.rubric.max}</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">{detail.advisory_notice}</p>
            </div>

            <div className="space-y-3">
              <h3 className="font-medium">Score breakdown</h3>
              {detail.rubric.criteria.map((criterion) => (
                <div key={criterion.key}>
                  <div className="flex justify-between text-sm">
                    <span>{criterion.label}</span>
                    <span>
                      {criterion.points} / {criterion.max_points}
                    </span>
                  </div>
                  <div className="mt-1 h-2 rounded bg-gray-100">
                    <div
                      className="h-2 rounded bg-gray-800"
                      style={{ width: `${(criterion.points / criterion.max_points) * 100}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-gray-500">{criterion.explanation}</p>
                </div>
              ))}
            </div>

            <BulletList title="Missing or unclear" items={detail.missing_or_unclear} />

            {narrative ? (
              <div className="space-y-4">
                <div>
                  <h3 className="font-medium">Summary</h3>
                  <p className="mt-1 text-sm">{narrative.professional_summary}</p>
                </div>
                <div>
                  <h3 className="font-medium">Experience</h3>
                  <p className="mt-1 text-sm">{narrative.experience_summary}</p>
                </div>
                <div>
                  <h3 className="font-medium">Education</h3>
                  <p className="mt-1 text-sm">{narrative.education_summary}</p>
                </div>
                <Chips title="Technical skills" items={narrative.technical_skills} />
                <Chips title="Non-technical skills" items={narrative.non_technical_skills} />
                <BulletList title="Strengths" items={narrative.strengths} />
                <BulletList title="Areas to improve" items={narrative.improvements} />
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                A written assessment was not generated for this analysis (score only).
              </p>
            )}

            <p className="text-xs text-gray-400">
              Rubric {analysis.rubric_version} · prompt {analysis.prompt_version} · model{" "}
              {analysis.model_name} · {new Date(analysis.created_at).toLocaleString()}
            </p>
          </div>
        )}
      </section>

      <details className="rounded border p-4">
        <summary className="cursor-pointer font-medium">Extracted text</summary>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-gray-700">
          {resume.extracted_text ?? "No text extracted."}
        </pre>
      </details>
    </main>
  );
}