"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/components/landing/i18n";
import { dictionary } from "@/components/landing/dictionary";

import { cn } from "@/lib/utils";

type Props = {
  className?: string;
};

export function LandingAuthLink({ className }: Props) {
  const { user, loading } = useAuth();
  const { lang } = useLang();
  const t = dictionary[lang];

  if (loading) return null;

  if (user) {
    const dashboardHref = ["admin", "ops", "employer"].includes(user.role) ? "/admin" : "/dashboard";
    return (
      <Link
        href={dashboardHref}
        className={cn("text-sm font-medium text-muted-foreground transition-colors hover:text-foreground", className)}
      >
        {t.nav.dashboard}
      </Link>
    );
  }

  return (
    <Link
      href="/login"
      className={cn("text-sm font-medium text-muted-foreground transition-colors hover:text-foreground", className)}
    >
      {t.nav.signIn}
    </Link>
  );
}
