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
  size?: "default" | "sm";
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
  size = "default",
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
        "group relative isolate inline-flex items-center justify-center font-medium tracking-tight rounded-md transition-all duration-200 active:scale-[0.98]",
        size === "sm"
          ? "h-8 px-3.5 text-xs gap-1.5"
          : "h-11 px-5 text-sm gap-2",
        variant === "solid"
          ? "bg-primary text-primary-foreground hover:bg-primary/90"
          : "border border-border/80 bg-background/80 hover:bg-accent hover:border-foreground/20 text-foreground",
        loading && "opacity-70 pointer-events-none",
        className,
      )}
    >
      <span className="relative z-10">{label}</span>
      {showArrow && (
        <ArrowRight
          className={cn(
            "relative z-10 transition-transform duration-200 group-hover:translate-x-0.5",
            size === "sm" ? "size-3.5" : "size-4",
          )}
        />
      )}
    </Link>
  );
}
