"use client";

import { JURISDICTION_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Jurisdictions() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="border-y border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t.jurisdictions.eyebrow}
        </p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          {JURISDICTION_ORDER.map((j, i) => {
            const copy = t.jurisdictions.items[j.id];
            return (
              <Reveal key={j.id} delay={i * 80}>
                <div className="flex items-center gap-3 rounded-full border bg-card px-4 py-2.5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
                  <span className="text-xl" aria-hidden>
                    {j.flag}
                  </span>
                  <div>
                    <p className="flex items-center gap-2 text-sm font-medium">
                      {copy.name}
                      {!j.live && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase text-muted-foreground">
                          {t.jurisdictions.inProgress}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">{copy.detail}</p>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
