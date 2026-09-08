"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

/**
 * A call to action that stays reachable on a phone.
 *
 * On a narrow screen the header's button is hidden and the hero's scrolls away within a
 * swipe, so for most of a long marketing page there was nothing to press — the reader had
 * to scroll back up to act on what convinced them. This appears once they are past the
 * hero and leaves the desktop layout, which never had the problem, untouched.
 */
export function StickyCta() {
  const { user } = useAuth();
  const { lang } = useLang();
  const t = dictionary[lang];
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 700);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 border-t border-border/60 bg-background/85 px-4 pb-4 pt-3 backdrop-blur-xl transition-transform duration-500 ease-out-expo sm:hidden",
        visible ? "translate-y-0" : "translate-y-full",
      )}
      // Off-screen it must not be reachable by tab or read aloud.
      aria-hidden={!visible}
    >
      <Link
        href={user ? "/scope" : "/register"}
        tabIndex={visible ? undefined : -1}
        className="animate-sheen relative flex w-full items-center justify-center overflow-hidden rounded-full bg-primary px-6 py-3.5 text-sm font-medium text-primary-foreground transition-transform active:scale-[0.98]"
      >
        {user ? t.nav.startCase : t.cta.stickyCta}
      </Link>
      {!user && (
        <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
          {t.cta.reassure.join(" · ")}
        </p>
      )}
    </div>
  );
}
