"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export function NavBar() {
  const { username, roles, logout } = useAuth();
  const pathname = usePathname();
  const isUser = roles.includes("user");

  const linkClass = (href: string) =>
    `rounded px-3 py-1.5 text-sm ${
      pathname.startsWith(href) ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-100"
    }`;

  return (
    <nav className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
        <Link href="/" className="mr-4 font-semibold">
          RateMyResume
        </Link>
        {isUser && (
          <>
            <Link href="/resumes" className={linkClass("/resumes")}>
              Resumes
            </Link>
            <Link href="/upload" className={linkClass("/upload")}>
              Upload
            </Link>
          </>
        )}
        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="text-gray-600">{username}</span>
          <button onClick={logout} className="rounded border px-3 py-1.5 hover:bg-gray-50">
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}