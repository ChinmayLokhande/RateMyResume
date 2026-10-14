"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";

export default function Home() {
  const router = useRouter();
  const { roles } = useAuth();
  const isUser = roles.includes("user");

  useEffect(() => {
    if (isUser) router.replace("/resumes");
  }, [isUser, router]);

  if (isUser) return null;
  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-xl font-semibold">Welcome</h1>
      <p className="mt-2 text-gray-600">
        Admin accounts manage users and do not have access to resume content. User management
        arrives in a later step.
      </p>
    </main>
  );
}