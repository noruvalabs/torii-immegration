"use client";

import { FileCheck, Sparkles, Send, ShieldCheck, ArrowRight } from "lucide-react";
import Link from "next/link";

const STEPS = [
  {
    step: "01",
    title: "Select Your Destination",
    description:
      "Choose from Japan, India, or Saudi Arabia. Review transparent embassy fees, official processing times, and exact document checklists.",
    icon: Sparkles,
  },
  {
    step: "02",
    title: "Smart Dossier Generation",
    description:
      "Upload your passport and basic details. Torii's intelligent engine generates your official typed MOFA/Embassy form, Cover Letter, and Schedule of Stay.",
    icon: FileCheck,
  },
  {
    step: "03",
    title: "Submit with Confidence",
    description:
      "Receive your 100% verified submission packet ready for VFS / IVAC or direct eVisa approval. Zero rejections due to paperwork mistakes.",
    icon: Send,
  },
];

export function AtlysSteps() {
  return (
    <section id="how-it-works" className="py-20 sm:py-24 bg-muted/30 border-y border-border/60">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <ShieldCheck className="size-3.5" />
            <span>The Torii Standard</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Get your visa in 3 simple steps
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground">
            No confusing embassy jargon. No handwriting mistakes. Just a seamless, guaranteed visa preparation experience.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <div
                key={s.step}
                className="relative rounded-2xl border border-border bg-card p-7 shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-3xl font-extrabold text-primary/40 font-mono">
                      {s.step}
                    </span>
                    <div className="size-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                      <Icon className="size-5" />
                    </div>
                  </div>
                  <h3 className="text-lg font-bold text-foreground">{s.title}</h3>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    {s.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Guarantee Banner */}
        <div className="rounded-2xl bg-gradient-to-r from-blue-600/10 via-indigo-600/10 to-purple-600/10 border border-primary/20 p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center sm:text-left">
            <h4 className="text-base sm:text-lg font-bold text-foreground">
              Guaranteed On-Time or 100% Refunded
            </h4>
            <p className="text-xs sm:text-sm text-muted-foreground max-w-xl">
              Every document kit is checked against official embassy guidelines. If your preparation kit is delayed, you get a full refund.
            </p>
          </div>
          <Link
            href="#destinations"
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-colors"
          >
            <span>Explore Visas</span>
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
