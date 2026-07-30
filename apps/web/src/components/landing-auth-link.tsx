"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/components/landing/i18n";
import { dictionary } from "@/components/landing/dictionary";

export function LandingAuthLink() {
  const { user, loading } = useAuth();
  const { lang } = useLang();
  const t = dictionary[lang];

  if (loading) return null;

  if (user) {
    const dashboardHref = ["admin", "ops", "employer"].includes(user.role) ? "/admin" : "/dashboard";
    return (
      <Link
        href={dashboardHref}
        className="text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        {t.nav.dashboard} →
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className="text-sm font-medium text-muted-foreground hover:text-foreground"
    >
      {t.nav.signIn} →
    </Link>
  );
}
