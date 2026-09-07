"use client";

import { Check } from "lucide-react";
import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function CtaBand() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="mx-auto max-w-6xl px-6 pb-24 pt-4 sm:pb-28 lg:px-8">
      <Reveal direction="scale" className="relative">
        <div className="relative overflow-hidden rounded-3xl bg-ink px-8 py-14 sm:px-14 sm:py-18">
          <div
            aria-hidden
            className="animate-blob-drift pointer-events-none absolute -right-20 -top-28 size-96 rounded-full bg-primary/30 blur-[90px]"
          />
          <div
            aria-hidden
            className="animate-blob-drift-slow pointer-events-none absolute -bottom-28 -left-20 size-80 rounded-full bg-white/10 blur-[90px]"
          />
          <div className="relative flex flex-col items-start gap-9 sm:flex-row sm:items-center sm:justify-between sm:gap-12">
            <div>
              <h2 className="text-display max-w-md text-3xl font-semibold text-ink-foreground sm:text-4xl">
                {t.ctaBand.title}
              </h2>
              <p className="mt-4 max-w-md text-base leading-relaxed text-ink-foreground/70">
                {t.ctaBand.body}
              </p>
            </div>

            <div className="shrink-0">
              <StartCaseButton
                signedOutLabel={t.ctaBand.cta}
                className="animate-sheen h-12 overflow-hidden px-6 text-[0.9375rem]"
              />
              <ul className="mt-4 space-y-1.5">
                {t.cta.reassure.map((item) => (
                  <li
                    key={item}
                    className="flex items-center gap-2 text-xs text-ink-foreground/65"
                  >
                    <Check className="size-3.5 shrink-0 text-emerald-400" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
