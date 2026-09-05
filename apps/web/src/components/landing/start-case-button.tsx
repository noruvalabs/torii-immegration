"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  variant?: "solid" | "outline";
  /** Overrides the label for a signed-out visitor; signed-in always reads "start your case". */
  signedOutLabel?: string;
  showArrow?: boolean;
};

/**
 * The one button the whole page is trying to get pressed.
 *
 * Every call to action used to point at `/scope`, which sits behind the applicant
 * `AuthGuard`: a visitor who clicked "Start your case" was bounced to a bare login form
 * with no explanation of why, having been asked to commit before being told anything.
 * A first-time visitor is sent to sign-up instead — which is the step the page is
 * actually asking for — and someone already signed in goes straight to scoping, because
 * showing them a registration form would be the same mistake pointed the other way.
 */
export function StartCaseButton({
  className,
  variant = "solid",
  signedOutLabel,
  showArrow = true,
}: Props) {
  const { user, loading } = useAuth();
  const { lang } = useLang();
  const t = dictionary[lang];

  const href = user ? "/scope" : "/register";
  const label = user ? t.nav.startCase : (signedOutLabel ?? t.cta.startFree);

  return (
    <Link
      href={href}
      // Until the session resolves the destination is unknown; dimming it briefly is
      // better than sending someone to the wrong side of the auth wall.
      aria-busy={loading || undefined}
      className={cn(
        "group relative isolate inline-flex items-center justify-center gap-2 overflow-hidden rounded-full px-6 py-3.5 text-sm font-medium transition-all duration-300",
        variant === "solid"
          ? "bg-primary text-primary-foreground shadow-[0_1px_0_0_rgba(255,255,255,0.15)_inset,0_12px_24px_-8px_var(--color-primary)] hover:-translate-y-0.5 hover:shadow-[0_1px_0_0_rgba(255,255,255,0.15)_inset,0_18px_36px_-8px_var(--color-primary)] motion-safe:animate-sheen"
          : "border hover:-translate-y-0.5 hover:border-primary/40 hover:bg-accent",
        loading && "opacity-70",
        className,
      )}
    >
      <span className="relative z-10">{label}</span>
      {showArrow && (
        <ArrowRight className="relative z-10 size-4 transition-transform group-hover:translate-x-1" />
      )}
    </Link>
  );
}
