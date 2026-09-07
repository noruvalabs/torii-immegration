"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Check, Sparkles, Coins, Zap, ArrowRight } from "lucide-react";
import { PRICING_TIER_ORDER } from "./data";
import { Reveal } from "./reveal";
import { Section, SectionHeading } from "./section";
import { StartCaseButton } from "./start-case-button";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

const CURRENCIES = [
  { id: "usd", label: "USD $" },
  { id: "jpy", label: "JPY ¥" },
] as const;

export function Pricing() {
  const { lang } = useLang();
  const { user } = useAuth();
  const t = dictionary[lang];
  const tiers = t.pricing.tiers;

  const [currency, setCurrency] = useState<"usd" | "jpy">(lang === "ja" ? "jpy" : "usd");

  useEffect(() => {
    setCurrency(lang === "ja" ? "jpy" : "usd");
  }, [lang]);

  return (
    <div className="relative border-t border-border/60 bg-linear-to-b from-background via-muted/20 to-background">
      <Section id="pricing">
        <SectionHeading
          eyebrow={t.pricing.eyebrow}
          eyebrowIcon={<Coins className="size-3.5 text-amber-500" />}
          title={t.pricing.title}
          body={t.pricing.body}
        />

        {/* The welcome bonus, said once and prominently. It is the answer to the only
            question a first-time reader has on this section: what does it cost to look. */}
        <Reveal delay={140} className="mx-auto mt-12 max-w-3xl">
          <div className="flex flex-col items-start gap-5 rounded-2xl border border-emerald-500/30 bg-emerald-500/6 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-4 sm:items-center">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                <Sparkles className="size-5" />
              </span>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
                    {t.pricing.welcomeBonus.badge}
                  </span>
                  <span className="text-sm font-semibold">{t.pricing.welcomeBonus.title}</span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                  {t.pricing.welcomeBonus.body}
                </p>
              </div>
            </div>

            <StartCaseButton
              size="sm"
              signedOutLabel={lang === "ja" ? "無料特典を受け取る" : "Claim 3 free passes"}
              className="h-10 shrink-0 self-stretch px-4 text-xs sm:self-auto"
            />
          </div>
        </Reveal>

        {/* Currency switcher. The indicator is a single sliding element rather than a
            background on the active button, so the change reads as one movement. */}
        <Reveal delay={180} className="mt-12 flex items-center justify-center gap-3">
          <span className="text-xs font-medium text-muted-foreground">{t.pricing.currencyLabel}</span>
          <div className="relative inline-flex rounded-full border border-border/70 bg-muted/50 p-1 text-xs font-medium">
            <span
              aria-hidden
              className="absolute inset-y-1 w-[calc(50%-0.25rem)] rounded-full bg-card shadow-panel transition-transform duration-300 ease-out-expo"
              style={{ transform: `translateX(${currency === "usd" ? 0 : 100}%)` }}
            />
            {CURRENCIES.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setCurrency(option.id)}
                aria-pressed={currency === option.id}
                className={cn(
                  "relative z-10 w-24 cursor-pointer rounded-full px-3 py-1.5 transition-colors duration-200",
                  currency === option.id ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </Reveal>

        {/* Stretched, so the four cards share a height and their buttons line up — the
            feature lists are different lengths and ragged card bottoms read as a bug. */}
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PRICING_TIER_ORDER.map((id, i) => {
            const tier = tiers[i];
            const isFree = id === "free";
            const isPopular = id === "standard";
            const price = currency === "usd" ? tier.price_usd : tier.price_jpy;
            const unit = currency === "usd" ? tier.unit_usd : tier.unit_jpy;

            return (
              <Reveal
                key={id}
                delay={i * 90}
                direction="fade"
                className={cn(
                  "relative flex h-full flex-col rounded-2xl border bg-card p-6 transition-[transform,border-color,box-shadow] duration-300 ease-out-expo hover:-translate-y-1",
                  isPopular
                    ? "ring-gradient border-transparent shadow-panel-lg lg:-mt-3 lg:pb-8 lg:pt-8"
                    : isFree
                      ? "border-emerald-500/35 shadow-panel hover:border-emerald-500/60 hover:shadow-panel-lg"
                      : "border-border/70 shadow-panel hover:border-foreground/20 hover:shadow-panel-lg",
                )}
              >
                {tier.badge && (
                  <span
                    className={cn(
                      "absolute -top-3 left-6 rounded-full px-2.5 py-0.5 text-[10px] font-semibold shadow-panel",
                      isFree
                        ? "bg-emerald-600 text-white dark:bg-emerald-500"
                        : isPopular
                          ? "bg-primary text-primary-foreground"
                          : "bg-amber-500 text-white dark:bg-amber-600",
                    )}
                  >
                    {tier.badge}
                  </span>
                )}

                <div className="flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-sm font-semibold leading-snug">{tier.name}</h3>
                    <span
                      className={cn(
                        "shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px]",
                        isFree
                          ? "bg-emerald-500/15 font-semibold text-emerald-700 dark:text-emerald-300"
                          : "bg-muted text-muted-foreground",
                      )}
                    >
                      {tier.credits} {tier.credits === 1 ? "Pass" : "Passes"}
                    </span>
                  </div>

                  <div className="mt-5 flex items-baseline gap-2">
                    <span className="text-display text-4xl font-semibold tabular-nums">{price}</span>
                    <span className="text-xs font-medium text-muted-foreground">
                      {isFree
                        ? `/ 3 ${lang === "ja" ? "無料パス" : "free passes"}`
                        : `/ ${tier.credits} ${t.pricing.perCase}`}
                    </span>
                  </div>

                  <p className="mt-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">{unit}</p>

                  <p className="mt-3 min-h-9 text-xs leading-relaxed text-muted-foreground">
                    {tier.description}
                  </p>

                  <div className="mt-5 border-t border-border/60 pt-4">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {lang === "ja" ? "含まれる機能" : "Included"}
                    </p>
                    <ul className="mt-3 space-y-2">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-2 text-xs leading-snug text-foreground/90">
                          <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="mt-6 border-t border-border/60 pt-5">
                  {user ? (
                    isFree ? (
                      <Link
                        href="/scope"
                        className="inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-md border border-border/80 bg-background px-4 text-xs font-medium tracking-tight transition-all duration-200 hover:border-foreground/20 hover:bg-accent active:scale-[0.98]"
                      >
                        <span>{lang === "ja" ? "無料で申請を開始" : "Start free case"}</span>
                        <ArrowRight className="size-3.5" />
                      </Link>
                    ) : (
                      <Link
                        href="/credits"
                        className={cn(
                          "inline-flex h-10 w-full items-center justify-center gap-1.5 rounded-md px-4 text-xs font-medium tracking-tight transition-all duration-200 active:scale-[0.98]",
                          isPopular
                            ? "bg-primary text-primary-foreground hover:bg-primary/90"
                            : "border border-border/80 bg-background hover:border-foreground/20 hover:bg-accent",
                        )}
                      >
                        <Zap className="size-3.5" />
                        <span>
                          {currency === "usd" ? `Top up ${tier.price_usd}` : `チャージ ${tier.price_jpy}`}
                        </span>
                      </Link>
                    )
                  ) : (
                    <StartCaseButton
                      variant={isPopular ? "solid" : "outline"}
                      signedOutLabel={tier.cta}
                      showArrow={false}
                      className="h-10 w-full text-xs"
                    />
                  )}
                </div>
              </Reveal>
            );
          })}
        </div>

        <p className="mx-auto mt-12 max-w-2xl text-center text-xs leading-relaxed text-muted-foreground">
          {t.pricing.footnote}
        </p>
      </Section>
    </div>
  );
}
