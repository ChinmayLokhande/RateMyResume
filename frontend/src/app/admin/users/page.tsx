"use client";

import { Copy, Plus, Search, ShieldCheck } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Card, inputClass, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { createUser, listUsers } from "@/lib/admin";
import type { AdminUserListResponse, CreateUserInput } from "@/types/api";

const PAGE_SIZE = 10;
const EMPTY: CreateUserInput = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  role: "user",
  temporary_password: "",
};

function generatePassword(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  const values = crypto.getRandomValues(new Uint32Array(16));
  return Array.from(values, (n) => alphabet[n % alphabet.length]).join("");
}

// Mirrors the server rules for quick feedback; the server checks them again.
function validate(form: CreateUserInput): string | null {
  if (!/^[a-zA-Z0-9._-]{3,50}$/.test(form.username))
    return "Username must be 3 to 50 letters, numbers, dots, dashes or underscores";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return "Enter a valid email address";
  if (!form.first_name.trim() || !form.last_name.trim()) return "First and last name are required";
  if (form.temporary_password.length < 12) return "Temporary password must be at least 12 characters";
  return null;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError && error.status === 403) {
    return "Only admin accounts can manage users.";
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

export default function UsersPage() {
  const [input, setInput] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminUserListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateUserInput>(EMPTY);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<{ username: string; password: string } | null>(null);
  const latest = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(input.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [input]);

  const query = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (q) params.set("q", q);
    return params.toString();
  }, [q, page]);

  const load = useCallback(() => {
    const request = ++latest.current;
    return listUsers(query)
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

  function set<K extends keyof CreateUserInput>(key: K, value: CreateUserInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const problem = validate(form);
    if (problem) {
      setFormError(problem);
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const user = await createUser(form);
      setCreated({ username: user.username, password: form.temporary_password });
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(describeError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <PageHeader
        title="Users"
        subtitle="Create accounts and see who has access."
        action={
          <Button
            onClick={() => {
              setShowForm((open) => !open);
              setFormError(null);
            }}
          >
            <Plus size={16} />
            Add user
          </Button>
        }
      />

      {created && (
        <Card className="mb-6 border-l-4 border-green-500 p-5">
          <p className="font-medium">User {created.username} was created.</p>
          <p className="mt-1 text-sm text-muted">
            Share this temporary password securely. It is shown only once, and the user must change it
            at first sign-in.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="rounded-lg bg-canvas px-3 py-2 text-sm">{created.password}</code>
            <Button
              variant="secondary"
              onClick={() => void navigator.clipboard.writeText(created.password)}
            >
              <Copy size={14} />
              Copy
            </Button>
            <Button variant="ghost" onClick={() => setCreated(null)}>
              Done
            </Button>
          </div>
        </Card>
      )}

      {showForm && (
        <Card className="mb-6 p-6">
          <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2" noValidate>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Username</span>
              <input
                className={inputClass}
                value={form.username}
                onChange={(e) => set("username", e.target.value)}
                autoComplete="off"
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Email</span>
              <input
                type="email"
                className={inputClass}
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">First name</span>
              <input
                className={inputClass}
                value={form.first_name}
                onChange={(e) => set("first_name", e.target.value)}
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Last name</span>
              <input
                className={inputClass}
                value={form.last_name}
                onChange={(e) => set("last_name", e.target.value)}
              />
            </label>
            <label className="text-sm">
              <span className="mb-1 block font-medium">Role</span>
              <select
                className={inputClass}
                value={form.role}
                onChange={(e) => set("role", e.target.value as "user" | "admin")}
              >
                <option value="user">User (can upload and analyze resumes)</option>
                <option value="admin">Admin (manages users, no resume access)</option>
              </select>
            </label>
            <div className="text-sm">
              <span className="mb-1 block font-medium">Temporary password</span>
              <div className="flex gap-2">
                <input
                  className={inputClass}
                  value={form.temporary_password}
                  onChange={(e) => set("temporary_password", e.target.value)}
                  autoComplete="off"
                />
                <Button
                  variant="secondary"
                  onClick={() => set("temporary_password", generatePassword())}
                >
                  Generate
                </Button>
              </div>
            </div>
            {formError && (
              <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 sm:col-span-2">{formError}</p>
            )}
            <div className="flex gap-2 sm:col-span-2">
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating…" : "Create user"}
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </Card>
      )}

      <div className="relative mb-4 max-w-sm">
        <Search size={16} className="pointer-events-none absolute left-3.5 top-3 text-muted" />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search users"
          maxLength={100}
          aria-label="Search users"
          className={`${inputClass} pl-10`}
        />
      </div>

      {error && <p className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}
      {!data && !error && <p className="text-muted">Loading…</p>}
      {data && data.items.length === 0 && (
        <Card className="p-10 text-center text-muted">
          {q ? "No users match your search." : "No users yet."}
        </Card>
      )}

      {data && data.items.length > 0 && (
        <>
          <Card className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-muted">
                <tr>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Role</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/5">
                {data.items.map((user) => (
                  <tr key={user.id}>
                    <td className="px-5 py-3">
                      <div className="font-medium">
                        {[user.first_name, user.last_name].filter(Boolean).join(" ") || user.username}
                      </div>
                      <div className="text-xs text-muted">{user.username}</div>
                    </td>
                    <td className="px-5 py-3">{user.email ?? "—"}</td>
                    <td className="px-5 py-3">
                      {user.roles.length === 0 ? (
                        <span className="text-muted">—</span>
                      ) : (
                        user.roles.map((role) => (
                          <span
                            key={role}
                            className={`mr-1 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                              role === "admin"
                                ? "bg-violet-50 text-violet-700"
                                : "bg-black/[0.05] text-ink"
                            }`}
                          >
                            {role === "admin" && <ShieldCheck size={12} />}
                            {role}
                          </span>
                        ))
                      )}
                    </td>
                    <td className="px-5 py-3">{user.enabled ? "Active" : "Disabled"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-muted">
              {data.total} user{data.total === 1 ? "" : "s"} · page {data.page} of {data.total_pages}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={page >= data.total_pages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </main>
  );
}