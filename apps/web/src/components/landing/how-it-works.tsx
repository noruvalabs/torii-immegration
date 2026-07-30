"use client";

import { STAGE_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function HowItWorks() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="how-it-works" className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
      <Reveal className="max-w-xl">
        <p className="text-sm font-medium text-primary">{t.howItWorks.eyebrow}</p>
        <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">
          {t.howItWorks.titleBefore}
          <em className="font-serif italic text-primary">{t.howItWorks.titleAccent}</em>
          {t.howItWorks.titleAfter}
        </h2>
        <p className="mt-4 text-lg text-muted-foreground">{t.howItWorks.body}</p>
      </Reveal>

      <div className="mt-14 grid gap-x-8 gap-y-12 sm:grid-cols-2">
        {STAGE_ORDER.map((stage, i) => {
          const copy = t.howItWorks.stages[stage.id];
          return (
            <Reveal key={stage.id} delay={i * 90} className="group flex gap-5">
              <span className="shrink-0 font-mono text-2xl font-semibold text-muted-foreground/25 transition-colors group-hover:text-primary/60">
                {stage.step}
              </span>
              <div>
                <h3 className="text-base font-semibold">{copy.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{copy.body}</p>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
