"use client";

import { AlertCircle, ArrowLeft, BriefcaseBusiness, Mail, MapPin, Phone, RefreshCw, ScanText, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { type ReactNode, useCallback, useEffect, useState } from "react";
import { ScoreRing } from "@/components/ScoreRing";
import { StatusBadge } from "@/components/StatusBadge";
import { Avatar, Button, Card, Skeleton } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { analyzeResume, getAnalysis, getJobMatches, getResume, refreshJobMatches } from "@/lib/resumes";
import type { AnalysisResponse, JobMatchItem, ResumeDetail } from "@/types/api";

const ACTIVE = ["queued", "processing"];

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "This area is for regular user accounts. Admin accounts do not have access to resumes.";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

function InfoRow({ icon, label, value }: { icon: ReactNode; label: string; value: string | null }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 text-muted">{icon}</span>
      <div className="min-w-0">
        <div className="text-xs text-muted">{label}</div>
        <div className="break-words text-sm">{value ?? "—"}</div>
      </div>
    </div>
  );
}

function Chips({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span key={item} className="rounded-full bg-black/[0.05] px-2.5 py-1 text-xs">
          {item}
        </span>
      ))}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-2 text-sm text-ink/80">{children}</div>
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ResumeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [resume, setResume] = useState<ResumeDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [jobMatches, setJobMatches] = useState<JobMatchItem[]>([]);
  const [jobMatchesLoading, setJobMatchesLoading] = useState(false);
  const [jobMatchesError, setJobMatchesError] = useState<string | null>(null);
  const [jobMatchesReady, setJobMatchesReady] = useState(false);

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

  useEffect(() => {
    if (!resume || resume.extraction_status !== "completed" || jobMatchesReady) return;
    let cancelled = false;
    setJobMatchesLoading(true);
    getJobMatches(id)
      .then((r) => {
        if (!cancelled) {
          setJobMatches(r.results);
          setJobMatchesError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setJobMatchesError(describeError(err));
      })
      .finally(() => {
        if (!cancelled) {
          setJobMatchesLoading(false);
          setJobMatchesReady(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, resume, jobMatchesReady]);

  async function recalculateJobMatches() {
    setJobMatchesLoading(true);
    setJobMatchesError(null);
    try {
      setJobMatches((await refreshJobMatches(id)).results);
    } catch (err) {
      setJobMatchesError(describeError(err));
    } finally {
      setJobMatchesLoading(false);
    }
  }

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

  const back = (
    <Link href="/resumes" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
      <ArrowLeft size={15} />
      All resumes
    </Link>
  );

  if (error) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 px-6 py-10">
        {back}
        <p className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>
      </main>
    );
  }
  if (!resume) {
    return (
      <main className="mx-auto max-w-6xl space-y-4 px-6 py-10">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  const canAnalyze =
    resume.extraction_status === "completed" && !ACTIVE.includes(resume.analysis_status);
  const detail = analysis?.detailed_result;
  const narrative = detail?.narrative ?? null;
  const displayName = resume.candidate_name ?? resume.original_filename;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      {back}

      <Card className="mt-4 flex flex-wrap items-center gap-5 p-6">
        <Avatar name={displayName} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{displayName}</h1>
          <p className="mt-0.5 truncate text-sm text-muted">
            {resume.original_filename} · uploaded{" "}
            {new Date(resume.uploaded_at).toLocaleDateString(undefined, {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge status={resume.extraction_status} />
          <StatusBadge status={resume.analysis_status} />
        </div>
        {resume.error_message && <p className="w-full text-sm text-muted">{resume.error_message}</p>}
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <Card className="space-y-4 p-6">
            <h2 className="font-semibold">Details</h2>
            <InfoRow icon={<Mail size={16} />} label="Email" value={resume.email} />
            <InfoRow icon={<Phone size={16} />} label="Mobile" value={resume.mobile} />
            <InfoRow icon={<MapPin size={16} />} label="Location" value={resume.location} />
            <InfoRow
              icon={<ScanText size={16} />}
              label="Read by"
              value={
                resume.extraction_method === "ocr"
                  ? "OCR (scanned document)"
                  : resume.extraction_method === "native_text"
                    ? "Text extraction"
                    : null
              }
            />
          </Card>
          {resume.skills.length > 0 && (
            <Card className="space-y-3 p-6">
              <h2 className="font-semibold">Skills</h2>
              <Chips items={resume.skills} />
            </Card>
          )}
        </div>

        <div className="space-y-6 lg:col-span-2">
          <Card className="space-y-6 p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 font-semibold">
                <Sparkles size={18} className="text-accent" />
                Analysis
              </h2>
              <Button variant="secondary" onClick={runAnalysis} disabled={!canAnalyze}>
                {ACTIVE.includes(resume.analysis_status)
                  ? "Analysis running…"
                  : analysis
                    ? "Re-run analysis"
                    : "Run analysis"}
              </Button>
            </div>

            {actionError && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{actionError}</p>}
            {resume.analysis_status === "failed" && (
              <p className="flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
                <AlertCircle size={16} />
                The latest analysis run failed.
                {analysis ? " Showing the previous result." : " You can try again."}
              </p>
            )}

            {!analysis && resume.extraction_status !== "completed" && (
              <p className="text-sm text-muted">Analysis becomes available once extraction finishes.</p>
            )}
            {!analysis &&
              resume.extraction_status === "completed" &&
              !ACTIVE.includes(resume.analysis_status) && (
                <p className="text-sm text-muted">No analysis yet. Click “Run analysis” to create one.</p>
              )}

            {analysis && detail && (
              <>
                <div className="flex flex-wrap items-center gap-8">
                  <ScoreRing score={analysis.score} max={detail.rubric.max} />
                  <div className="min-w-[14rem] flex-1 space-y-3">
                    {detail.rubric.criteria.map((criterion) => (
                      <div key={criterion.key} title={criterion.explanation}>
                        <div className="flex justify-between text-sm">
                          <span>{criterion.label}</span>
                          <span className="text-muted">
                            {criterion.points} / {criterion.max_points}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 rounded-full bg-black/[0.06]">
                          <div
                            className="h-1.5 rounded-full bg-gradient-to-r from-accent to-violet-500"
                            style={{ width: `${(criterion.points / criterion.max_points) * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted">{detail.advisory_notice}</p>

                <div className="space-y-3">
                  <h3 className="text-sm font-semibold">How the score was calculated</h3>
                  <ul className="space-y-1.5 text-sm text-ink/80">
                    {detail.rubric.criteria.map((criterion) => (
                      <li key={criterion.key}>
                        <span className="font-medium text-ink">{criterion.label}:</span>{" "}
                        {criterion.explanation}
                      </li>
                    ))}
                  </ul>
                </div>

                {detail.missing_or_unclear.length > 0 && (
                  <Section title="Missing or unclear">
                    <Bullets items={detail.missing_or_unclear} />
                  </Section>
                )}

                {narrative ? (
                  <div className="space-y-5 border-t border-black/5 pt-6">
                    <Section title="Summary">{narrative.professional_summary}</Section>
                    <Section title="Experience">{narrative.experience_summary}</Section>
                    <Section title="Education">{narrative.education_summary}</Section>
                    {narrative.technical_skills.length > 0 && (
                      <Section title="Technical skills">
                        <Chips items={narrative.technical_skills} />
                      </Section>
                    )}
                    {narrative.non_technical_skills.length > 0 && (
                      <Section title="Non-technical skills">
                        <Chips items={narrative.non_technical_skills} />
                      </Section>
                    )}
                    {narrative.strengths.length > 0 && (
                      <Section title="Strengths">
                        <Bullets items={narrative.strengths} />
                      </Section>
                    )}
                    {narrative.improvements.length > 0 && (
                      <Section title="Areas to improve">
                        <Bullets items={narrative.improvements} />
                      </Section>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted">
                    A written assessment was not generated for this analysis (score only).
                  </p>
                )}

                <p className="text-xs text-muted/80">
                  Rubric {analysis.rubric_version} · prompt {analysis.prompt_version} · model{" "}
                  {analysis.model_name} · {new Date(analysis.created_at).toLocaleString()}
                </p>
              </>
            )}
          </Card>

          <Card className="space-y-5 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 font-semibold">
                <BriefcaseBusiness size={18} className="text-accent" /> Best Matching Jobs
              </h2>
              <Button
                variant="secondary"
                onClick={recalculateJobMatches}
                disabled={jobMatchesLoading || resume.extraction_status !== "completed"}
              >
                <RefreshCw size={14} className={jobMatchesLoading ? "animate-spin" : ""} />
                {jobMatchesLoading ? "Checking matches…" : "Refresh matches"}
              </Button>
            </div>
            {resume.extraction_status !== "completed" && (
              <p className="text-sm text-muted">
                {resume.extraction_status === "failed"
                  ? "Resume text extraction failed, so job matching is unavailable."
                  : "Job matching will be available once resume text extraction completes."}
              </p>
            )}
            {jobMatchesLoading && jobMatches.length === 0 && (
              <p className="text-sm text-muted">Comparing the resume with job descriptions…</p>
            )}
            {jobMatchesError && (
              <div className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
                <p>{jobMatchesError}</p>
                <p className="mt-1 text-xs">Your resume analysis and other details are still available.</p>
              </div>
            )}
            {jobMatchesReady && !jobMatchesLoading && !jobMatchesError && jobMatches.length === 0 && (
              <p className="text-sm text-muted">
                No matches returned. Make sure the job descriptions are seeded.
              </p>
            )}
            {jobMatches.map((m, i) => (
              <div key={m.job_id} className="rounded-xl border border-black/[0.07] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted">Match #{i + 1}</p>
                    <h3 className="mt-1 font-semibold">{m.job_title}</h3>
                  </div>
                  <span className="text-xl font-semibold tabular-nums text-accent">{m.fit_percentage}%</span>
                </div>
                <div
                  className="mt-3 h-2 overflow-hidden rounded-full bg-black/[0.06]"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={m.fit_percentage}
                >
                  <div className="h-full rounded-full bg-accent" style={{ width: `${m.fit_percentage}%` }} />
                </div>
                <p className="mt-3 text-sm">{m.match_summary}</p>
                {m.matching_skills.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-muted">Matching skills</p>
                    <Chips items={m.matching_skills} />
                  </div>
                )}
                {m.missing_required_skills.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-muted">Required skills not found</p>
                    <Chips items={m.missing_required_skills} />
                  </div>
                )}
                {m.relevant_evidence.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-muted">Evidence</p>
                    <Bullets items={m.relevant_evidence} />
                  </div>
                )}
              </div>
            ))}
            <p className="text-xs text-muted">
              Fit % estimates keyword alignment with the extracted resume text, not hiring outcomes.
            </p>
          </Card>

          <Card className="p-6">
            <details>
              <summary className="cursor-pointer font-semibold">Extracted text</summary>
              <pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-canvas p-4 text-xs text-ink/80">
                {resume.extracted_text ?? "No text extracted."}
              </pre>
            </details>
          </Card>
        </div>
      </div>
    </main>
  );
}