"use client";

import Link from "next/link";
import { ArrowLeft, ShieldCheck, AlertTriangle, Info, FileText, Scale, Receipt, Cookie } from "lucide-react";
import { useLang } from "@/components/landing/i18n";
import { Reveal } from "@/components/landing/reveal";
import { LEGAL_DOCUMENTS, type PolicyKey } from "./legal-content";
import { cn } from "@/lib/utils";

const POLICY_ICONS: Record<PolicyKey, typeof ShieldCheck> = {
  privacy: ShieldCheck,
  terms: Scale,
  refund: Receipt,
  cookies: Cookie,
};


export function LegalPageView({ policyKey }: { policyKey: PolicyKey }) {
  const { lang } = useLang();
  const doc = LEGAL_DOCUMENTS[policyKey][lang];
  const Icon = POLICY_ICONS[policyKey] || FileText;

  return (
    <div className="relative overflow-hidden pt-28 pb-20 sm:pt-32 sm:pb-28">
      {/* Subtle top glow matching landing aesthetic */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -z-10 size-128 -translate-x-1/2 rounded-full bg-primary/5 blur-[120px]"
      />

      <article className="mx-auto max-w-3xl px-6 sm:px-8">
        <Reveal>
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/60 pb-6">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
              {lang === "ja" ? "ホームに戻る" : "Back to Home"}
            </Link>

            <span className="text-xs text-muted-foreground">
              {lang === "ja" ? `最終改定日: ${doc.lastUpdated}` : `Last updated: ${doc.lastUpdated}`}
            </span>
          </div>

          <div className="mt-8 flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Icon className="size-5" />
            </div>
            <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
              {doc.badge}
            </span>
          </div>

          <h1 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {doc.title}
          </h1>

          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            {doc.summary}
          </p>

          {doc.disclaimer && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm text-foreground/90">
              <ShieldCheck className="size-5 shrink-0 text-primary mt-0.5" />
              <p className="leading-relaxed">{doc.disclaimer}</p>
            </div>
          )}
        </Reveal>

        {/* Quick section navigation pills */}
        <div className="mt-10 flex flex-wrap gap-2 border-y border-border/60 py-4">
          {doc.sections.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className="rounded-lg bg-muted/60 px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              {section.title.replace(/^\d+\.\s*/, "")}
            </a>
          ))}
        </div>

        {/* Policy Sections */}
        <div className="mt-10 space-y-12">
          {doc.sections.map((section, idx) => (
            <Reveal key={section.id} delay={Math.min(idx * 50, 200)}>
              <section id={section.id} className="scroll-mt-28 space-y-4">
                <h2 className="text-xl font-semibold tracking-tight text-foreground">
                  {section.title}
                </h2>

                <div className="space-y-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                  {section.content.map((paragraph, pIdx) => (
                    <p key={pIdx}>{paragraph}</p>
                  ))}
                </div>

                {section.subsections && (
                  <div className="mt-4 space-y-4 rounded-xl border border-border/50 bg-card/40 p-5">
                    {section.subsections.map((sub, sIdx) => (
                      <div key={sIdx} className="space-y-2">
                        <h3 className="text-sm font-semibold text-foreground">
                          {sub.title}
                        </h3>
                        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-muted-foreground">
                          {sub.items.map((item, itemIdx) => (
                            <li key={itemIdx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {section.callout && (
                  <div
                    className={cn(
                      "mt-5 flex items-start gap-3.5 rounded-xl border p-4.5 text-sm leading-relaxed",
                      section.callout.type === "warning" &&
                        "border-amber-500/30 bg-amber-500/10 text-amber-950 dark:text-amber-200",
                      section.callout.type === "shield" &&
                        "border-emerald-500/30 bg-emerald-500/10 text-emerald-950 dark:text-emerald-200",
                      section.callout.type === "info" &&
                        "border-sky-500/30 bg-sky-500/10 text-sky-950 dark:text-sky-200",
                    )}
                  >
                    {section.callout.type === "warning" && (
                      <AlertTriangle className="size-5 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
                    )}
                    {section.callout.type === "shield" && (
                      <ShieldCheck className="size-5 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5" />
                    )}
                    {section.callout.type === "info" && (
                      <Info className="size-5 shrink-0 text-sky-600 dark:text-sky-400 mt-0.5" />
                    )}
                    <div>
                      <h4 className="font-semibold">{section.callout.title}</h4>
                      <p className="mt-1 opacity-90">{section.callout.text}</p>
                    </div>
                  </div>
                )}
              </section>
            </Reveal>
          ))}
        </div>

      </article>
    </div>
  );
}
