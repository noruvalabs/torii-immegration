"use client";

import { STAGE_ORDER } from "./data";
import { Reveal } from "./reveal";
import { Section, SectionHeading } from "./section";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function HowItWorks() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <Section id="how-it-works">
      <SectionHeading
        eyebrow={t.howItWorks.eyebrow}
        title={
          <>
            {t.howItWorks.titleBefore}
            <em className="font-serif italic text-primary">{t.howItWorks.titleAccent}</em>
            {t.howItWorks.titleAfter}
          </>
        }
        body={t.howItWorks.body}
      />

      <div className="relative mt-16">
        {/* The rail the four steps hang off. It is one continuous line rather than four
            separate cards because the point of this section is that the stages follow
            from each other. */}
        <div
          aria-hidden
          className="absolute left-4.5 top-2 bottom-2 w-px bg-linear-to-b from-transparent via-border to-transparent lg:left-0 lg:right-0 lg:top-4.5 lg:bottom-auto lg:h-px lg:w-auto lg:bg-linear-to-r"
        />

        <ol className="relative grid gap-10 lg:grid-cols-4 lg:gap-8">
          {STAGE_ORDER.map((stage, i) => {
            const copy = t.howItWorks.stages[stage.id];
            return (
              <Reveal
                as="li"
                key={stage.id}
                delay={i * 110}
                direction="fade"
                className="group flex gap-5 lg:flex-col lg:gap-0"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border/70 bg-card font-mono text-xs font-semibold text-muted-foreground shadow-panel transition-all duration-300 group-hover:border-primary/50 group-hover:text-primary">
                  {stage.step}
                </span>
                <div className="lg:mt-6 lg:pr-4">
                  <h3 className="text-base font-semibold">{copy.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy.body}</p>
                </div>
              </Reveal>
            );
          })}
        </ol>
      </div>
    </Section>
  );
}
