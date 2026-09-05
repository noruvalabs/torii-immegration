"use client";

import { FileSignature, ScanSearch, Search } from "lucide-react";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

const ICONS = [Search, FileSignature, ScanSearch];

/**
 * Three cards, straight after the hero, answering the sentence it just made.
 *
 * The hero claims a lawyer's fee is mostly avoidable. This says what that fee is actually
 * buying — knowing the requirements, filling the forms, catching the errors — and that
 * those three are what Torii does. Naming the work is more persuasive than naming the
 * saving, and it keeps the claim to things the product genuinely performs.
 */
export function ValueProps() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="relative border-b border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <Reveal className="max-w-2xl">
          <p className="text-sm font-medium text-[var(--color-torii)]">{t.valueProps.eyebrow}</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            {t.valueProps.title}
          </h2>
        </Reveal>

        <div className="mt-12 grid gap-5 lg:grid-cols-3">
          {t.valueProps.items.map((item, index) => {
            const Icon = ICONS[index] ?? Search;
            return (
              <Reveal
                key={item.title}
                delay={index * 90}
                className="group relative overflow-hidden rounded-[var(--radius-lg)] border bg-card p-7 transition-all duration-300 hover:-translate-y-1.5 hover:border-primary/40 hover:shadow-[0_24px_48px_-24px_var(--color-primary)]"
              >
                {/* A wash of accent that arrives with the pointer, not before it. */}
                <span
                  aria-hidden
                  className="pointer-events-none absolute inset-x-0 -top-24 h-40 bg-gradient-to-b from-primary/12 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                />
                <span className="relative inline-flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
                  <Icon className="size-5" />
                </span>
                <h3 className="relative mt-5 text-lg font-semibold tracking-tight">{item.title}</h3>
                <p className="relative mt-2.5 text-sm leading-relaxed text-muted-foreground">
                  {item.body}
                </p>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
