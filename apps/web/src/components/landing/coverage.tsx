"use client";

import { ArrowRight } from "lucide-react";
import { JP_ROUTE_ORDER } from "./data";
import { Reveal } from "./reveal";
import { Section, SectionHeading } from "./section";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/**
 * What Torii covers, named rather than implied.
 *
 * This used to be three country pills — Japan, the United States, the United Kingdom —
 * all marked live. Only Japan is. A visitor who picked one of the other two would reach
 * a scope picker that could not serve them, which is a worse first impression than a
 * shorter list honestly told.
 *
 * Naming the five Japan routes is also the stronger pitch: "we cover your country" is a
 * claim, and "技術・人文知識・国際業務, 留学, 短期滞在, 家族滞在, 日本人の配偶者等" is
 * evidence. The labels are the scope picker's own, so what is promised here is what the
 * next screen offers.
 */
export function Coverage() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <div className="relative overflow-hidden border-y border-border/60 bg-muted/25">
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -bottom-40 left-1/2 size-128 -translate-x-1/2 rounded-full bg-primary/8 blur-[120px]"
      />

      <Section id="coverage" size="tight" className="relative">
        <SectionHeading
          eyebrow={t.coverage.eyebrow}
          eyebrowIcon={<span aria-hidden>🇯🇵</span>}
          title={t.coverage.title}
          body={t.coverage.body}
        />

        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {JP_ROUTE_ORDER.map((route, index) => {
            const copy = t.coverage.routes[route.id];
            return (
              <Reveal key={route.id} delay={index * 70} direction="fade">
                <div className="group relative flex h-full items-center gap-3 overflow-hidden rounded-2xl border border-border/70 bg-card p-4 transition-[transform,border-color,box-shadow] duration-300 ease-out-expo hover:-translate-y-1 hover:border-primary/40 hover:shadow-panel-lg">
                  {/* A wash that arrives from the pointer's side of the card on hover. */}
                  <span
                    aria-hidden
                    className="pointer-events-none absolute inset-0 bg-linear-to-r from-primary/8 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
                  />
                  <div className="relative min-w-0 flex-1">
                    <p className="text-sm font-semibold">{copy.name}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      <span className="font-medium text-foreground/70">{route.kanji}</span>
                      {" · "}
                      {copy.detail}
                    </p>
                  </div>
                  <ArrowRight className="relative size-4 shrink-0 text-muted-foreground transition-all duration-300 group-hover:translate-x-0.5 group-hover:text-primary" />
                </div>
              </Reveal>
            );
          })}

          <Reveal delay={JP_ROUTE_ORDER.length * 70} direction="fade">
            <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-border/80 bg-transparent p-4 text-center">
              <p className="text-xs leading-relaxed text-muted-foreground">{t.coverage.more}</p>
            </div>
          </Reveal>
        </div>
      </Section>
    </div>
  );
}
