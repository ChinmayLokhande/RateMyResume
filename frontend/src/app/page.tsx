"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { apiFetch } from "@/lib/api";
import type { MeResponse } from "@/types/api";

export default function Home() {
  const { username, roles, logout } = useAuth();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<MeResponse>("/me")
      .then(setMe)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="mx-auto max-w-xl space-y-4 p-8">
      <h1 className="text-2xl font-semibold">RateMyResume</h1>
      <p>
        Signed in as <strong>{username}</strong> (roles: {roles.join(", ") || "none"})
      </p>
      {error && <p className="text-red-600">API error: {error}</p>}
      {me && <pre className="rounded bg-gray-100 p-4 text-sm">{JSON.stringify(me, null, 2)}</pre>}
      <button onClick={logout} className="rounded border px-4 py-2 hover:bg-gray-50">
        Sign out
      </button>
    </main>
  );
}