"use client";

import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function CtaBand() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="mx-auto max-w-6xl px-6 py-20 sm:py-28">
      <Reveal className="relative overflow-hidden rounded-[var(--radius-lg)] bg-[var(--color-ink)] px-8 py-16 sm:px-16 sm:py-20">
        <div
          aria-hidden
          className="animate-blob-drift pointer-events-none absolute -right-16 -top-24 size-[24rem] rounded-full bg-primary/30 blur-[90px]"
        />
        <div
          aria-hidden
          className="animate-blob-drift-slow pointer-events-none absolute -bottom-24 -left-16 size-[20rem] rounded-full bg-white/10 blur-[90px]"
        />

        <div className="relative flex flex-col items-start gap-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-[var(--color-ink-foreground)] sm:text-4xl">
              {t.ctaBand.title}
            </h2>
            <p className="mt-3 max-w-md text-base text-[var(--color-ink-foreground)]/75">{t.ctaBand.body}</p>
          </div>
          <StartCaseButton signedOutLabel={t.ctaBand.cta} className="shrink-0 shadow-lg" />
        </div>
      </Reveal>
    </section>
  );
}
