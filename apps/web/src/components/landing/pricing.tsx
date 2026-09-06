"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Check, Sparkles, Coins, Zap, ArrowRight } from "lucide-react";
import { PRICING_TIER_ORDER } from "./data";
import { Reveal } from "./reveal";
import { StartCaseButton } from "./start-case-button";
import { useAuth } from "@/lib/auth-context";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

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
    <section id="pricing" className="relative border-t border-border/70 bg-gradient-to-b from-background via-muted/15 to-background py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <Reveal className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/8 px-3.5 py-1 text-xs font-medium text-primary backdrop-blur-sm">
            <Coins className="size-3.5 text-amber-500" />
            <span>{t.pricing.eyebrow}</span>
          </div>
          <h2 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
            {t.pricing.title}
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            {t.pricing.body}
          </p>
        </Reveal>

        {/* Welcome Bonus Callout Banner */}
        <Reveal delay={100} className="mx-auto mt-10 max-w-3xl">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4 sm:p-5 shadow-xs">
            <div className="flex items-start sm:items-center gap-3.5">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                <Sparkles className="size-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:text-emerald-300">
                    {t.pricing.welcomeBonus.badge}
                  </span>
                  <span className="text-xs sm:text-sm font-bold text-foreground">
                    {t.pricing.welcomeBonus.title}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t.pricing.welcomeBonus.body}
                </p>
              </div>
            </div>

            <div className="self-end sm:self-auto shrink-0">
              <StartCaseButton
                size="sm"
                signedOutLabel={lang === "ja" ? "無料特典を受け取る" : "Claim 3 Free Passes"}
                className="text-xs shadow-xs"
              />
            </div>
          </div>
        </Reveal>

        {/* Currency Switcher */}
        <div className="mt-10 flex items-center justify-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">
            {t.pricing.currencyLabel}
          </span>
          <div className="inline-flex rounded-md border border-border/80 bg-muted/40 p-0.5 text-xs font-medium">
            <button
              type="button"
              onClick={() => setCurrency("usd")}
              className={cn(
                "rounded px-3 py-1 transition-all cursor-pointer",
                currency === "usd"
                  ? "bg-background text-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              🇺🇸 USD ($)
            </button>
            <button
              type="button"
              onClick={() => setCurrency("jpy")}
              className={cn(
                "rounded px-3 py-1 transition-all cursor-pointer",
                currency === "jpy"
                  ? "bg-background text-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              🇯🇵 JPY (¥)
            </button>
          </div>
        </div>

        {/* 4 Pricing Packages Grid: Free + Starter + Standard + Family */}
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {PRICING_TIER_ORDER.map((id, i) => {
            const tier = tiers[i];
            const isFree = id === "free";
            const isPopular = id === "standard";
            const isAgency = id === "family";
            const price = currency === "usd" ? tier.price_usd : tier.price_jpy;
            const unit = currency === "usd" ? tier.unit_usd : tier.unit_jpy;

            return (
              <Reveal
                key={id}
                delay={i * 80}
                className={cn(
                  "relative flex flex-col justify-between rounded-lg border p-5 sm:p-6 transition-all duration-200 shadow-xs",
                  isPopular
                    ? "border-primary bg-card ring-2 ring-primary/30 shadow-md"
                    : isFree
                      ? "border-emerald-500/40 bg-card hover:border-emerald-500/70"
                      : "border-border/80 bg-card hover:border-foreground/20 hover:shadow-sm",
                )}
              >
                {/* Badge */}
                {tier.badge && (
                  <div className="absolute -top-3 left-5">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-[10px] font-bold shadow-xs",
                        isFree
                          ? "bg-emerald-600 text-white dark:bg-emerald-500"
                          : isPopular
                            ? "bg-primary text-primary-foreground"
                            : "bg-amber-500 text-white dark:bg-amber-600",
                      )}
                    >
                      {tier.badge}
                    </span>
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm sm:text-base font-bold text-foreground">{tier.name}</h3>
                    <span className={cn(
                      "rounded px-2 py-0.5 text-[10px] font-mono",
                      isFree
                        ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-semibold"
                        : "bg-muted text-muted-foreground",
                    )}>
                      {tier.credits} {tier.credits === 1 ? "Pass" : "Passes"}
                    </span>
                  </div>

                  {/* Price & Unit Breakdown */}
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
                      {price}
                    </span>
                    <span className="text-xs text-muted-foreground font-medium">
                      {isFree
                        ? `/ 3 ${lang === "ja" ? "無料パス" : "free passes"}`
                        : `/ ${tier.credits} ${t.pricing.perCase}`}
                    </span>
                  </div>

                  <p className={cn(
                    "mt-1 text-xs font-semibold",
                    isFree ? "text-emerald-600 dark:text-emerald-400" : "text-emerald-600 dark:text-emerald-400"
                  )}>
                    {unit}
                  </p>

                  <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground min-h-[36px]">
                    {tier.description}
                  </p>

                  <div className="mt-5 border-t border-border/70 pt-4">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2.5">
                      {lang === "ja" ? "含まれる機能:" : "Included features:"}
                    </p>
                    <ul className="space-y-2 text-xs">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-1.5 text-foreground/90">
                          <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                          <span className="leading-snug text-[11px] sm:text-xs">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-border/60">
                  {user ? (
                    isFree ? (
                      <Link
                        href="/scope"
                        className="inline-flex w-full items-center justify-center font-medium tracking-tight rounded-md transition-all duration-200 active:scale-[0.98] h-10 px-4 text-xs gap-1.5 border border-border/80 bg-background hover:bg-accent hover:border-foreground/20 text-foreground"
                      >
                        <span>{lang === "ja" ? "無料で申請を開始" : "Start Free Case"}</span>
                        <ArrowRight className="size-3.5" />
                      </Link>
                    ) : (
                      <Link
                        href="/credits"
                        className={cn(
                          "inline-flex w-full items-center justify-center font-medium tracking-tight rounded-md transition-all duration-200 active:scale-[0.98] h-10 px-4 text-xs gap-1.5",
                          isPopular
                            ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-xs"
                            : "border border-border/80 bg-background hover:bg-accent hover:border-foreground/20 text-foreground",
                        )}
                      >
                        <Zap className="size-3.5" />
                        <span>{currency === "usd" ? `Top up ${tier.price_usd}` : `チャージ ${tier.price_jpy}`}</span>
                      </Link>
                    )
                  ) : (
                    <StartCaseButton
                      variant={isPopular ? "solid" : "outline"}
                      signedOutLabel={tier.cta}
                      showArrow={false}
                      className="w-full h-10 text-xs"
                    />
                  )}
                </div>
              </Reveal>
            );
          })}
        </div>

        {/* Bottom Footnote */}
        <p className="mx-auto mt-12 max-w-2xl text-center text-xs leading-relaxed text-muted-foreground">
          {t.pricing.footnote}
        </p>
      </div>
    </section>
  );
}
