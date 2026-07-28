"use client";

import { Check, ExternalLink } from "lucide-react";
import { FEATURE_ICONS, PLAIN_FEATURE_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Features() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const SourcedIcon = FEATURE_ICONS.sourced;
  const FormsIcon = FEATURE_ICONS.forms;

  return (
    <section id="features" className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="max-w-xl">
          <p className="text-sm font-medium text-primary">{t.features.eyebrow}</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t.features.title}</h2>
        </Reveal>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          <Reveal className="group flex flex-col gap-6 rounded-[var(--radius-lg)] border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg sm:flex-row sm:items-center lg:col-span-2">
            <div className="flex-1">
              <span className="inline-flex size-10 items-center justify-center rounded-full bg-primary/10">
                <SourcedIcon className="size-5 text-primary" />
              </span>
              <h3 className="mt-4 text-sm font-semibold">{t.features.items.sourced.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t.features.items.sourced.body}</p>
            </div>
            <div className="w-full shrink-0 rounded-[var(--radius)] border bg-background p-4 sm:w-64">
              <p className="text-xs font-medium">{t.features.coePreview.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{t.features.coePreview.body}</p>
              <p className="mt-2.5 flex items-center gap-1.5 text-xs font-medium text-primary">
                <ExternalLink className="size-3" /> {t.features.coePreview.source}
              </p>
            </div>
          </Reveal>

          <Reveal
            delay={90}
            className="rounded-[var(--radius-lg)] border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
          >
            <span className="inline-flex size-10 items-center justify-center rounded-full bg-primary/10">
              <FormsIcon className="size-5 text-primary" />
            </span>
            <h3 className="mt-4 text-sm font-semibold">{t.features.items.forms.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{t.features.items.forms.body}</p>
            <div className="mt-4 flex items-center gap-2 rounded-[var(--radius)] border bg-background px-3 py-2 text-xs">
              <span className="font-mono font-semibold">{t.features.formPreview.code}</span>
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {t.features.formPreview.version}
              </span>
              <span className="ml-auto flex items-center gap-1 text-[var(--color-success)]">
                <Check className="size-3" /> {t.features.formPreview.ready}
              </span>
            </div>
          </Reveal>

          {PLAIN_FEATURE_ORDER.map((id, i) => {
            const Icon = FEATURE_ICONS[id];
            const copy = t.features.items[id];
            return (
              <Reveal
                key={id}
                delay={(i + 2) * 90}
                className="rounded-[var(--radius-lg)] border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
              >
                <span className="inline-flex size-10 items-center justify-center rounded-full bg-primary/10">
                  <Icon className="size-5 text-primary" />
                </span>
                <h3 className="mt-4 text-sm font-semibold">{copy.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy.body}</p>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
