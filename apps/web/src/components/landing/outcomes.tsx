"use client";

import { FileCheck2, FileDown, Link2, ListChecks } from "lucide-react";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

const ICONS = [FileCheck2, Link2, FileDown, ListChecks];

/**
 * The deliverables, stated plainly and early.
 *
 * The page explained how Torii works and what it costs before it ever said what the
 * visitor ends up holding — and the answer to that is the whole reason to sign up: a
 * filled statutory form, a checklist that cites its source, drafts that open in Word,
 * and a plan built around the lead times that actually decide a filing date.
 *
 * Nothing here is a claim about outcomes. Torii prepares paperwork; it does not verify
 * documents or decide applications, and this section is careful to promise only the
 * artefacts, which is also all the product actually produces.
 */
export function Outcomes() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="outcomes" className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-28">
        <Reveal className="max-w-2xl">
          <p className="text-sm font-medium text-primary">{t.outcomes.eyebrow}</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
            {t.outcomes.title}
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-muted-foreground">{t.outcomes.body}</p>
        </Reveal>

        <div className="mt-14 grid gap-5 sm:grid-cols-2">
          {t.outcomes.items.map((item, index) => {
            const Icon = ICONS[index] ?? FileCheck2;
            return (
              <Reveal
                key={item.title}
                delay={index * 90}
                className="rounded-[var(--radius-lg)] border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
              >
                <span className="inline-flex size-10 items-center justify-center rounded-full bg-primary/10">
                  <Icon className="size-5 text-primary" />
                </span>
                <h3 className="mt-4 text-base font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
              </Reveal>
            );
          })}
        </div>

        <Reveal
          delay={200}
          className="mt-10 flex flex-col items-start gap-3 border-t border-border/60 pt-8 sm:flex-row sm:items-center sm:gap-6"
        >
          <p className="shrink-0 text-xs font-medium text-muted-foreground">
            {t.outcomes.sourcesLabel}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {t.outcomes.sources.map((source) => (
              <span
                key={source}
                className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground"
              >
                {source}
              </span>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
