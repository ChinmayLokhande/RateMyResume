"use client";

import { FileText, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export function NavBar() {
  const { username, roles, logout } = useAuth();
  const pathname = usePathname();

  const links: { href: string; label: string }[] = [];
  if (roles.includes("user")) {
    links.push(
      { href: "/dashboard", label: "Dashboard" },
      { href: "/resumes", label: "Resumes" },
      { href: "/upload", label: "Upload" },
    );  }
  if (roles.includes("admin")) links.push({ href: "/admin/users", label: "Users" });

  return (
    <nav className="sticky top-0 z-10 border-b border-black/5 bg-white/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-1 px-6 py-3">
        <Link href="/" className="mr-6 flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-violet-500 text-white">
            <FileText size={18} />
          </span>
          RateMyResume
        </Link>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-full px-3.5 py-1.5 text-sm transition ${
              pathname.startsWith(link.href)
                ? "bg-black/[0.06] text-ink"
                : "text-muted hover:text-ink"
            }`}
          >
            {link.label}
          </Link>
        ))}
        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="hidden text-muted sm:inline">{username}</span>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-muted transition hover:bg-black/[0.05] hover:text-ink"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}