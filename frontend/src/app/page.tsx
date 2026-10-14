"use client";

import { Gauge, ScanText, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { HeroIllustration } from "@/components/HeroIllustration";
import { buttonClass, Card } from "@/components/ui";

const FEATURES = [
  {
    icon: UploadCloud,
    title: "Upload in bulk",
    text: "Drop in one resume or twenty. PDF and Word files are processed in the background.",
  },
  {
    icon: ScanText,
    title: "Read locally",
    text: "Text extraction, OCR for scans and the AI model all run on your own machine.",
  },
  {
    icon: Gauge,
    title: "Transparent scoring",
    text: "A documented rubric explains every point, so the score is never a black box.",
  },
];

export default function Home() {
  const { roles } = useAuth();
  const isUser = roles.includes("user");
  const isAdmin = roles.includes("admin");

  return (
    <main className="mx-auto max-w-6xl px-6 py-14">
      <section className="grid items-center gap-10 md:grid-cols-2">
        <div>
          <p className="text-sm font-medium text-accent">Resume management and analysis</p>
          <h1 className="mt-3 text-5xl font-semibold tracking-tight">Resumes, understood.</h1>
          <p className="mt-5 max-w-md text-lg text-muted">
            Upload resumes, extract the details that matter, and see a clear, explainable assessment
            of each one.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {isUser && (
              <>
                <Link href="/dashboard" className={buttonClass("primary", "px-5 py-2.5")}>
                  Open dashboard
                </Link>
                <Link href="/upload" className={buttonClass("secondary", "px-5 py-2.5")}>
                  Upload resumes
                </Link>
                <Link href="/resumes" className={buttonClass("secondary", "px-5 py-2.5")}>
                  View my resumes
                </Link>
              </>
            )}
            {isAdmin && (
              <Link href="/admin/users" className={buttonClass("primary", "px-5 py-2.5")}>
                Manage users
              </Link>
            )}
          </div>
          {isAdmin && !isUser && (
            <p className="mt-4 max-w-md text-sm text-muted">
              Admin accounts manage users and do not have access to resume content.
            </p>
          )}
        </div>
        <HeroIllustration />
      </section>

      <section className="mt-20 grid gap-5 md:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <Card key={title} className="p-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 text-accent">
              <Icon size={20} />
            </span>
            <h2 className="mt-4 font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-muted">{text}</p>
          </Card>
        ))}
      </section>
    </main>
  );
}