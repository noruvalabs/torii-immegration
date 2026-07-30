"use client";

import { Check, Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Trust() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
      <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
        <Reveal>
          <p className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
            <Scale className="size-4" /> {t.trust.eyebrow}
          </p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t.trust.title}</h2>
          <p className="mt-4 text-muted-foreground">{t.trust.body}</p>
          <ul className="mt-6 space-y-4 text-sm">
            {t.trust.points.map((point) => (
              <li key={point.strong} className="flex gap-3">
                <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                <span>
                  <strong className="font-medium">{point.strong}</strong>
                  {point.rest}
                </span>
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal
          delay={120}
          className="rounded-[var(--radius-lg)] border bg-card p-6 shadow-[0_1px_0_0_rgba(0,0,0,0.02),0_20px_50px_-30px_rgba(0,0,0,0.4)] transition-transform hover:-translate-y-1 sm:p-7"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold">{t.trust.card.title}</p>
            <Badge tone="warning">{t.trust.card.badge}</Badge>
          </div>
          <div className="mt-4 space-y-3 text-sm">
            <div>
              <p className="text-xs font-medium text-muted-foreground">{t.trust.card.reasonLabel}</p>
              <p className="mt-1 rounded-[var(--radius)] border bg-background px-3 py-2">{t.trust.card.reason}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">{t.trust.card.messageLabel}</p>
              <p className="mt-1 rounded-[var(--radius)] border bg-background px-3 py-2 text-muted-foreground">
                {t.trust.card.message}
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="flex size-3.5 shrink-0 items-center justify-center rounded-sm bg-primary text-primary-foreground">
                <Check className="size-2.5" />
              </span>
              {t.trust.card.consent}
            </div>
          </div>
          <div className="mt-4 rounded-[var(--radius)] bg-primary px-4 py-2.5 text-center text-sm font-medium text-primary-foreground opacity-90">
            {t.trust.card.sent}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
