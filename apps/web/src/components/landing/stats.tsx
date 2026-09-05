"use client";

import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/**
 * The numbers band — and a deliberately unusual set of numbers.
 *
 * The pattern this borrows from puts customer counts and market share here: "trusted by
 * 70% of the industry". Torii has no such figure, and inventing one on a page selling
 * help with a sworn government application would be both a lie and a liability. Every
 * value below is instead something a reader could verify by using the product: the five
 * routes the scope picker offers, the three procedures behind each, what an eligibility
 * check costs, and the count of fields Torii will guess on a document you sign.
 *
 * That last one is zero, and it is the most persuasive number here precisely because a
 * competitor filling blanks with plausible text cannot claim it.
 */
export function Stats() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="relative isolate overflow-hidden bg-[var(--color-ink)] text-[var(--color-ink-foreground)]">
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -right-24 top-0 size-[26rem] rounded-full bg-primary/20 blur-[110px]"
      />
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"
      />

      <div className="relative mx-auto max-w-6xl px-6 py-16 sm:py-20">
        <Reveal>
          <h2 className="text-center text-sm font-medium uppercase tracking-[0.2em] text-[var(--color-ink-foreground)]/50">
            {t.stats.title}
          </h2>
        </Reveal>

        <dl className="mt-10 grid grid-cols-2 gap-x-6 gap-y-10 lg:grid-cols-4">
          {t.stats.items.map((item, index) => (
            <Reveal key={item.label} delay={index * 90} className="text-center">
              <dt className="sr-only">{item.label}</dt>
              <dd>
                <span className="block bg-gradient-to-b from-white to-white/55 bg-clip-text text-5xl font-semibold tracking-tight text-transparent sm:text-6xl">
                  {item.value}
                </span>
                <span className="mx-auto mt-3 block max-w-[15rem] text-sm leading-snug text-[var(--color-ink-foreground)]/60">
                  {item.label}
                </span>
              </dd>
            </Reveal>
          ))}
        </dl>

        <Reveal delay={360}>
          <p className="mx-auto mt-12 max-w-2xl border-t border-white/10 pt-8 text-center text-xs leading-relaxed text-[var(--color-ink-foreground)]/45">
            {t.stats.note}
          </p>
        </Reveal>
      </div>
    </section>
  );
}
