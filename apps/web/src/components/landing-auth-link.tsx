"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function LandingAuthLink() {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (user) {
    return (
      <Link
        href="/admin"
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
