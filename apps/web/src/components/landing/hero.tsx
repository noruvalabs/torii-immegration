"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { HeroDemo } from "./hero-demo";
import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/**
 * A dark hero, and the rest of the page bright behind it.
 *
 * The page used to open on a pale mesh gradient that read as one more calm SaaS landing.
 * This inverts it: an ink panel edge to edge, the headline at display size on it, and the
 * product demo lit against the dark. The contrast is the point — the eye lands on the
 * sentence and then on the thing being sold, in that order.
 *
 * It is painted on `--color-ink`, a token that is already dark in both themes, so the
 * section reads the same whichever way the visitor has their theme set and the toggle in
 * the header keeps working for everything below it.
 */
export function Hero() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const { user, loading } = useAuth();

  return (
    <section className="relative isolate overflow-hidden bg-[var(--color-ink)] text-[var(--color-ink-foreground)]">
      <div
        aria-hidden
        className="bg-mesh-gradient animate-gradient-pan pointer-events-none absolute inset-0 opacity-[0.35]"
      />
      <div
        aria-hidden
        className="animate-blob-drift pointer-events-none absolute -top-52 right-[-10%] size-[42rem] rounded-full bg-primary/25 blur-[120px]"
      />
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -bottom-40 -left-32 size-[32rem] rounded-full bg-[var(--color-torii)]/20 blur-[120px]"
      />
      {/* A hairline of accent along the top edge, the way a status bar reads. */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
      />

      <div className="relative mx-auto grid max-w-6xl gap-14 px-6 pb-24 pt-32 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pb-32 lg:pt-40">
        <Reveal>
          <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs font-medium text-[var(--color-ink-foreground)]/80 backdrop-blur">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
            </span>
            {t.hero.eyebrow}
          </p>

          <h1 className="mt-7 max-w-2xl text-[2.75rem] font-semibold leading-[1.02] tracking-[-0.02em] sm:text-6xl lg:text-[4.2rem]">
            {t.hero.titleBefore}
            <em className="font-serif italic text-primary">{t.hero.titleAccent}</em>
            {t.hero.titleAfter}
          </h1>

          <p className="mt-7 max-w-xl text-lg leading-relaxed text-[var(--color-ink-foreground)]/70">
            {t.hero.body}
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <StartCaseButton className="px-7 py-4 text-base" />
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 px-6 py-4 text-sm font-medium text-[var(--color-ink-foreground)] transition-all hover:-translate-y-0.5 hover:bg-white/10"
            >
              {t.hero.ctaSecondary}
            </a>
          </div>

          {/* What it costs to try, answered before it is asked. The objection to pressing
              that button is never the price of filing — it is not knowing whether the
              next screen wants a card. */}
          <ul className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-2">
            {t.cta.reassure.map((item) => (
              <li
                key={item}
                className="flex items-center gap-1.5 text-sm text-[var(--color-ink-foreground)]/65"
              >
                <Check className="size-3.5 shrink-0 text-primary" />
                {item}
              </li>
            ))}
          </ul>

          {!user && !loading && (
            <p className="mt-5 text-sm text-[var(--color-ink-foreground)]/55">
              {t.cta.returningBefore}
              <Link
                href="/login"
                className="font-medium text-[var(--color-ink-foreground)] underline-offset-4 hover:underline"
              >
                {t.cta.returningLink}
              </Link>
            </p>
          )}
        </Reveal>

        <Reveal delay={150}>
          {/* The demo paints itself on `bg-card` and needs no colour help here — its
              accents (the primary blues, the success ticks, the muted labels) all read
              correctly against its own surface. Only the ring is added, to lift a light
              card off the ink panel instead of letting it float edgelessly. */}
          <div className="motion-safe:animate-float-y rounded-[var(--radius-lg)] ring-1 ring-white/10">
            <HeroDemo />
          </div>
        </Reveal>
      </div>

      <p className="relative mx-auto max-w-6xl px-6 pb-10 text-xs leading-relaxed text-[var(--color-ink-foreground)]/45">
        {t.hero.disclaimerBefore}
        <strong className="font-medium text-[var(--color-ink-foreground)]/70">
          {t.hero.disclaimerStrong}
        </strong>
        {t.hero.disclaimerAfter}
      </p>
    </section>
  );
}
