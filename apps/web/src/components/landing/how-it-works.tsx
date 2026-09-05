"use client";

import { STAGE_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/**
 * The four stages, drawn as a sequence rather than a grid.
 *
 * These were two columns of numbered paragraphs, which reads as four unrelated features.
 * A connecting rail and oversized step numerals say the thing the copy is claiming — that
 * this is one path with an end — and the rail fills as each step reveals, so scrolling the
 * section walks it.
 */
export function HowItWorks() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="how-it-works" className="relative border-b border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="max-w-2xl">
          <p className="text-sm font-medium text-[var(--color-torii)]">{t.howItWorks.eyebrow}</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
            {t.howItWorks.titleBefore}
            <em className="font-serif italic text-primary">{t.howItWorks.titleAccent}</em>
            {t.howItWorks.titleAfter}
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">{t.howItWorks.body}</p>
        </Reveal>

        <ol className="relative mt-16">
          {/* The rail the steps hang from. Hidden on a phone, where the cards stack and a
              vertical line beside them would only take width from the text. */}
          <span
            aria-hidden
            className="absolute left-0 right-0 top-7 hidden h-px bg-gradient-to-r from-border via-primary/40 to-border lg:block"
          />

          <div className="grid gap-10 lg:grid-cols-4 lg:gap-6">
            {STAGE_ORDER.map((stage, i) => {
              const copy = t.howItWorks.stages[stage.id];
              return (
                <Reveal key={stage.id} delay={i * 120} className="group relative">
                  <li className="list-none">
                    <span className="relative z-10 inline-flex size-14 items-center justify-center rounded-full border bg-background font-mono text-lg font-semibold text-muted-foreground shadow-sm transition-all duration-300 group-hover:-translate-y-1 group-hover:border-primary group-hover:bg-primary group-hover:text-primary-foreground group-hover:shadow-[0_16px_32px_-16px_var(--color-primary)]">
                      {stage.step}
                    </span>
                    <h3 className="mt-6 text-base font-semibold tracking-tight">{copy.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {copy.body}
                    </p>
                  </li>
                </Reveal>
              );
            })}
          </div>
        </ol>
      </div>
    </section>
  );
}
