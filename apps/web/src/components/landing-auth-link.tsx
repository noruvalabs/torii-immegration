"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function LandingAuthLink() {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (user) {
    const dashboardHref = ["admin", "ops", "employer"].includes(user.role) ? "/admin" : "/dashboard";
    return (
      <Link
        href={dashboardHref}
        className="text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        Dashboard →
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className="text-sm font-medium text-muted-foreground hover:text-foreground"
    >
      Sign in →
    </Link>
  );
}
