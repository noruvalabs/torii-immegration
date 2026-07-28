"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { PRICING_TIER_ORDER } from "./data";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

export function Pricing() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const tiers = t.pricing.tiers;

  return (
    <section id="pricing" className="border-t border-border/60">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="mx-auto max-w-xl text-center">
          <p className="text-sm font-medium text-primary">{t.pricing.eyebrow}</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t.pricing.title}</h2>
          <p className="mt-4 text-lg text-muted-foreground">{t.pricing.body}</p>
        </Reveal>

        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          {PRICING_TIER_ORDER.map((id, i) => {
            const tier = tiers[i];
            const highlighted = id === "guided";
            return (
              <Reveal
                key={id}
                delay={i * 100}
                className={cn(
                  "relative flex flex-col rounded-[var(--radius-lg)] border p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg",
                  highlighted ? "border-primary bg-card ring-1 ring-primary/40" : "bg-card",
                )}
              >
                {highlighted && (
                  <span className="absolute -top-3 left-7 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground">
                    {t.pricing.popular}
                  </span>
                )}
                <h3 className="text-sm font-semibold">{tier.name}</h3>
                <div className="mt-3 flex items-baseline gap-1.5">
                  <span className="text-3xl font-semibold tracking-tight">{tier.price}</span>
                  {tier.price !== t.pricing.free && (
                    <span className="text-sm text-muted-foreground">/ {t.pricing.perCase}</span>
                  )}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{tier.description}</p>

                <ul className="mt-6 flex-1 space-y-3 text-sm">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5">
                      <Check className="mt-0.5 size-4 shrink-0 text-primary" />
                      <span className="text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link
                  href="/scope"
                  className={cn(
                    "mt-7 inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-medium transition-all",
                    highlighted
                      ? "bg-primary text-primary-foreground shadow-md hover:-translate-y-0.5"
                      : "border hover:bg-accent",
                  )}
                >
                  {tier.cta}
                </Link>
              </Reveal>
            );
          })}
        </div>

        <p className="mx-auto mt-10 max-w-2xl text-center text-xs leading-relaxed text-muted-foreground">
          {t.pricing.footnote}
        </p>
      </div>
    </section>
  );
}
