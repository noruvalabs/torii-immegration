"use client";

import { ChevronDown } from "lucide-react";
import { FAQ_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Faq() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="faq" className="border-t border-border/60">
      <div className="mx-auto max-w-3xl px-6 py-24 sm:py-32">
        <Reveal>
          <h2 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            {t.faq.titleBefore}
            <em className="font-serif italic text-primary">{t.faq.titleAccent}</em>
          </h2>
        </Reveal>

        <div className="mt-10 divide-y divide-border/60">
          {FAQ_ORDER.map((id, i) => {
            const copy = t.faq.items[id];
            return (
              <Reveal key={id} delay={Math.min(i * 60, 300)}>
                <details className="group py-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-base font-medium marker:content-none">
                    {copy.question}
                    <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
                  </summary>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{copy.answer}</p>
                </details>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
