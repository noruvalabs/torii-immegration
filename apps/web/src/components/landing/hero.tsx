"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { HeroDemo } from "./hero-demo";
import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Hero() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const { user, loading } = useAuth();

  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden
        className="bg-mesh-gradient animate-gradient-pan pointer-events-none absolute inset-x-0 top-0 h-[46rem]"
      />
      <div
        aria-hidden
        className="animate-blob-drift pointer-events-none absolute -top-40 right-0 size-[36rem] rounded-full bg-primary/15 blur-[100px]"
      />
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -left-24 top-32 size-[24rem] rounded-full bg-[var(--color-ink)]/15 blur-[100px]"
      />
      <div
        aria-hidden
        className="animate-blob-drift pointer-events-none absolute bottom-0 left-1/3 size-[20rem] rounded-full bg-primary/10 blur-[100px] [animation-duration:22s]"
      />

      <div className="relative mx-auto grid max-w-6xl gap-12 px-6 pb-20 pt-28 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:pb-28 lg:pt-36">
        <Reveal>
          <p className="inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/8 px-3 py-1 text-xs font-medium text-primary">
            {t.hero.eyebrow}
          </p>

          <h1 className="mt-6 max-w-xl text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            {t.hero.titleBefore}
            <em className="font-serif italic text-primary">{t.hero.titleAccent}</em>
            {t.hero.titleAfter}
          </h1>

          <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted-foreground">{t.hero.body}</p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <StartCaseButton />
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-full border px-6 py-3.5 text-sm font-medium transition-colors hover:bg-accent"
            >
              {t.hero.ctaSecondary}
            </a>
          </div>

          {/* What it costs to try, answered before it is asked. The objection to pressing
              that button is never the price of filing — it is not knowing whether the
              next screen wants a card. */}
          <ul className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
            {t.cta.reassure.map((item) => (
              <li key={item} className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Check className="size-3.5 shrink-0 text-[var(--color-success)]" />
                {item}
              </li>
            ))}
          </ul>

          {!user && !loading && (
            <p className="mt-4 text-sm text-muted-foreground">
              {t.cta.returningBefore}
              <Link href="/login" className="font-medium text-primary hover:underline">
                {t.cta.returningLink}
              </Link>
            </p>
          )}

          <p className="mt-7 max-w-lg text-sm text-muted-foreground">
            {t.hero.disclaimerBefore}
            <strong className="font-medium text-foreground">{t.hero.disclaimerStrong}</strong>
            {t.hero.disclaimerAfter}
          </p>
        </Reveal>

        <Reveal delay={150}>
          <HeroDemo />
        </Reveal>
      </div>
    </section>
  );
}
