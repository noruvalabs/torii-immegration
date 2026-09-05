"use client";

import { ArrowRight } from "lucide-react";
import { JP_ROUTE_ORDER } from "./data";
import { Reveal } from "./reveal";
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
 * claim, and "工 技術・人文知識・国際業務, 留学, 短期滞在, 家族滞在, 日本人の配偶者等" is
 * evidence. The labels are the scope picker's own, so what is promised here is what the
 * next screen offers.
 */
export function Coverage() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="coverage" className="border-y border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
        <Reveal className="text-center">
          <p className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/8 px-3 py-1 text-xs font-medium text-primary">
            <span aria-hidden>🇯🇵</span>
            {t.coverage.eyebrow}
          </p>
          <h2 className="mx-auto mt-4 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
            {t.coverage.title}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">{t.coverage.body}</p>
        </Reveal>

        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {JP_ROUTE_ORDER.map((route, index) => {
            const copy = t.coverage.routes[route.id];
            return (
              <Reveal key={route.id} delay={index * 70}>
                <div className="group flex h-full items-center gap-3 rounded-[var(--radius-lg)] border bg-card p-4 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-lg">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold">{copy.name}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      <span className="font-medium text-foreground/70">{route.kanji}</span>
                      {" · "}
                      {copy.detail}
                    </p>
                  </div>
                  <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
                </div>
              </Reveal>
            );
          })}

          <Reveal delay={JP_ROUTE_ORDER.length * 70}>
            <div className="flex h-full items-center justify-center rounded-[var(--radius-lg)] border border-dashed bg-transparent p-4 text-center">
              <p className="text-xs text-muted-foreground">{t.coverage.more}</p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
