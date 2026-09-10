"use client";

import Link from "next/link";
import {
  ShieldCheck,
  CheckCircle2,
  Landmark,
  ArrowRight,
  Sparkles,
  Scale,
  FileCheck,
  Coins,
  ArrowLeft,
} from "lucide-react";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { Reveal } from "./reveal";
import { ToriiLogo } from "@/components/brand/ToriiLogo";
import { StartCaseButton } from "./start-case-button";

export function AboutView() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const about = t.about;

  const principleIcons = [Landmark, ShieldCheck, FileCheck, Coins];

  return (
    <div className="relative overflow-hidden pt-28 pb-20 sm:pt-32 sm:pb-28">
      {/* Background glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -z-10 size-144 -translate-x-1/2 rounded-full bg-primary/8 blur-[130px]"
      />

      <div className="mx-auto max-w-4xl px-6 sm:px-8">
        {/* Breadcrumb */}
        <Reveal>
          <div className="flex items-center justify-between border-b border-border/60 pb-6">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
              {lang === "ja" ? "ホームに戻る" : "Back to Home"}
            </Link>

            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {about.eyebrow}
            </span>
          </div>
        </Reveal>

        {/* Hero Section */}
        <Reveal delay={80} className="mt-10 text-center sm:mt-14">
          <div className="inline-flex items-center justify-center gap-3">
            <ToriiLogo size={42} />
            <span className="text-2xl font-bold tracking-tight">Torii</span>
          </div>
          <h1 className="mt-6 text-3xl font-extrabold tracking-tight sm:text-5xl lg:text-5xl">
            {about.title}
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            {about.subtitle}
          </p>
        </Reveal>

        {/* Key Stats Bar */}
        <Reveal delay={140} className="mt-12 sm:mt-16">
          <div className="grid grid-cols-2 gap-4 rounded-2xl border border-border/70 bg-card p-6 shadow-panel sm:grid-cols-4">
            {about.stats.map((stat, idx) => (
              <div key={idx} className="text-center">
                <p className="text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                  {stat.value}
                </p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </Reveal>

        {/* The Origin Story */}
        <Reveal delay={180} className="mt-16 sm:mt-20">
          <div className="rounded-3xl border border-border/60 bg-muted/20 p-8 sm:p-10">
            <div className="flex items-center gap-2.5 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="size-4" />
              <span>{lang === "ja" ? "創業ストーリー" : "Origin Story"}</span>
            </div>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {about.storyHeading}
            </h2>
            <div className="mt-6 space-y-4 text-sm leading-relaxed text-muted-foreground sm:text-base">
              {about.story.map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
          </div>
        </Reveal>

        {/* 4 Core Principles */}
        <div className="mt-16 sm:mt-20">
          <Reveal>
            <div className="text-center">
              <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                {lang === "ja" ? "行動規範" : "Our Commitments"}
              </p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                {about.principlesHeading}
              </h2>
            </div>
          </Reveal>

          <div className="mt-10 grid gap-6 sm:grid-cols-2">
            {about.principles.map((item, idx) => {
              const Icon = principleIcons[idx] || CheckCircle2;
              return (
                <Reveal key={idx} delay={idx * 70}>
                  <div className="flex h-full flex-col rounded-2xl border border-border/60 bg-card p-6 transition-all hover:border-border">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Icon className="size-5" />
                    </div>
                    <h3 className="mt-4 text-base font-semibold text-foreground">
                      {item.title}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                      {item.body}
                    </p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>

        {/* Backed by Official Standards Strip */}
        <Reveal delay={200} className="mt-16 sm:mt-20">
          <div className="rounded-2xl border border-border/60 bg-card/60 p-6 sm:p-8">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Landmark className="size-4 text-primary" />
              <span>{about.standardsHeading}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {about.standardsBody}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              {t.outcomes.sources.map((source) => (
                <span
                  key={source}
                  className="inline-flex items-center gap-2 rounded-xl border border-border/80 bg-muted/40 px-3.5 py-2 text-xs font-medium text-foreground"
                >
                  <Landmark className="size-3.5 text-primary/80" />
                  {source}
                </span>
              ))}
            </div>
          </div>
        </Reveal>

        {/* Bottom CTA Card */}
        <Reveal delay={240} className="mt-16 sm:mt-20">
          <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border border-primary/20 bg-linear-to-b from-primary/10 via-primary/5 to-transparent p-8 text-center sm:flex-row sm:text-left sm:p-10">
            <div>
              <h3 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
                {lang === "ja" ? "あなたの申請要件を確認しませんか？" : "Ready to file with confidence?"}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {lang === "ja"
                  ? "わずか2分で適格性を確認できます。クレジットカード登録は不要です。"
                  : "Check your eligibility in 2 minutes. 3 free filing passes included on signup."}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-3">
              <Link
                href="/pricing"
                className="inline-flex h-11 items-center justify-center rounded-md border border-border/80 bg-card px-5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              >
                {t.nav.pricing}
              </Link>
              <StartCaseButton
                size="default"
                signedOutLabel={about.cta}
                className="h-11 px-5"
              />
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
