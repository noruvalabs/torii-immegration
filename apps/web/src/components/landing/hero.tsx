"use client";

import Link from "next/link";
import { ArrowDown, Check } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { HeroDemo } from "./hero-demo";
import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Hero() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const { user } = useAuth();

  return (
    <section className="relative overflow-hidden">
      {/* Backdrop: a slow mesh and two soft lights. Kept to three layers — the original
          four drifting blobs plus a panning mesh read as weather. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[42rem]">
        <div className="bg-mesh-gradient animate-gradient-pan absolute inset-0" />
        <div className="animate-blob-drift absolute -top-32 right-0 size-[34rem] rounded-full bg-primary/12 blur-[110px]" />
        <div className="animate-blob-drift-slow absolute -left-24 top-40 size-[24rem] rounded-full bg-[var(--color-ink)]/12 blur-[110px]" />
      </div>

      <div className="relative mx-auto grid max-w-6xl gap-14 px-6 pb-16 pt-28 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-12 lg:px-8 lg:pb-20 lg:pt-34">
        <div>
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3.5 py-1.5 text-xs font-medium text-muted-foreground shadow-panel backdrop-blur-sm">
              <span className="animate-ping-ring relative size-1.5 rounded-full bg-emerald-500 text-emerald-500" />
              <span className="text-foreground/80">{t.hero.eyebrow}</span>
            </span>
          </Reveal>

          <Reveal delay={80}>
            <h1 className="text-display mt-6 max-w-2xl text-4xl font-semibold leading-[1.08] sm:text-5xl lg:text-[3.25rem]">
              {t.hero.titleBefore}
              <em className="font-serif italic text-primary">{t.hero.titleAccent}</em>
              {t.hero.titleAfter}
            </h1>
          </Reveal>

          <Reveal delay={150}>
            <p className="mt-6 max-w-lg text-base leading-relaxed text-muted-foreground sm:text-lg">
              {t.hero.body}
            </p>
          </Reveal>

          <Reveal delay={220}>
            {/* Stacked full-width on a phone: side by side, the two buttons wrap to
                different widths and the pair reads as ragged rather than as a choice. */}
            <div className="mt-9 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <StartCaseButton className="h-12 w-full px-6 text-[0.9375rem] sm:w-auto" />
              <a
                href="#dashboard-showcase"
                className="group inline-flex h-12 w-full items-center justify-center gap-2 rounded-md border border-border/80 bg-card/70 px-5 text-sm font-medium tracking-tight text-foreground backdrop-blur-sm transition-all duration-200 hover:border-foreground/20 hover:bg-accent active:scale-[0.98] sm:w-auto"
              >
                <span>{lang === "ja" ? "実際の画面を見る" : "See it in action"}</span>
                <ArrowDown className="size-4 text-muted-foreground transition-transform duration-300 group-hover:translate-y-0.5" />
              </a>
            </div>
          </Reveal>

          {/* What it costs to try, answered before it is asked. The objection to pressing
              that button is never the price of filing — it is not knowing whether the
              next screen wants a card. */}
          <Reveal delay={280}>
            <ul className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2">
              {t.cta.reassure.map((item) => (
                <li key={item} className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Check className="size-3.5 shrink-0 text-[var(--color-success)]" />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>

          {!user && (
            <Reveal delay={320}>
              <p className="mt-5 text-sm text-muted-foreground">
                {t.cta.returningBefore}
                <Link
                  href="/login"
                  className="font-medium text-primary underline-offset-4 transition-colors hover:underline"
                >
                  {t.cta.returningLink}
                </Link>
              </p>
            </Reveal>
          )}

          <Reveal delay={360}>
            <p className="mt-7 max-w-lg border-l-2 border-border/70 pl-4 text-sm leading-relaxed text-muted-foreground">
              {t.hero.disclaimerBefore}
              <strong className="font-medium text-foreground">{t.hero.disclaimerStrong}</strong>
              {t.hero.disclaimerAfter}
            </p>
          </Reveal>
        </div>

        <Reveal delay={200} direction="scale" blur className="relative">
          {/* A pool of light under the panel, so it sits on the page rather than floating
              above it. The panel used to drift up and down forever, which undercut the one
              thing it is there to demonstrate: that this is a real, steady product. */}
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-6 rounded-[2rem] bg-gradient-to-br from-primary/12 via-transparent to-primary/8 blur-2xl"
          />
          <div className="relative">
            <HeroDemo />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
