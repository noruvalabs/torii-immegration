"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Clock,
  ShieldCheck,
  CheckCircle2,
  ChevronDown,
  ArrowRight,
  FileText,
  Calendar,
  Layers,
  Sparkles,
  AlertCircle,
  HelpCircle,
  Lock,
  Globe2,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { type DestinationInfo, type DestinationVisa } from "@/lib/destinations-data";
import { cn } from "@/lib/utils";

export function VisaDetailView({ destination }: { destination: DestinationInfo }) {
  const router = useRouter();
  const { user } = useAuth();
  const [selectedVisaId, setSelectedVisaId] = useState<string>(
    destination.visas[0]?.id || "",
  );
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const selectedVisa: DestinationVisa =
    destination.visas.find((v) => v.id === selectedVisaId) || destination.visas[0];

  function handleStartApplication() {
    const targetUrl = `/scope?destination=${destination.code}`;
    if (user) {
      router.push(targetUrl);
    } else {
      router.push(`/login?redirect=${encodeURIComponent(targetUrl)}`);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground pb-24">
      {/* Top Breadcrumb & Hero Banner */}
      <section className="relative overflow-hidden bg-[#0A0D18] pt-28 pb-14 text-white">
        {/* Ambient Glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-32 left-1/3 size-[500px] rounded-full bg-primary/20 blur-[130px]" />
          <div className="absolute top-1/2 -right-20 size-[400px] rounded-full bg-indigo-500/15 blur-[120px]" />
        </div>

        <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-xs text-white/60">
            <Link href="/" className="hover:text-white transition-colors">
              Home
            </Link>
            <span>/</span>
            <Link href="/#destinations" className="hover:text-white transition-colors">
              Visas
            </Link>
            <span>/</span>
            <span className="text-white font-medium">{destination.name} Visa</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Left Hero Content */}
            <div className="lg:col-span-7 space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1 text-xs font-semibold backdrop-blur-md">
                <span className="text-lg">{destination.flag}</span>
                <span>{destination.bannerTag}</span>
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
                {destination.name} Visa for Bangladeshi Citizens
              </h1>

              <p className="text-sm sm:text-base text-white/80 max-w-xl leading-relaxed">
                {destination.tagline}. {destination.shortDescription}
              </p>

              {/* Key Quick Metric Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                <div className="flex items-center gap-2.5 rounded-xl bg-white/5 border border-white/10 p-3 backdrop-blur-sm">
                  <Clock className="size-4 text-emerald-400 shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/60 uppercase font-medium">Processing Time</span>
                    <span className="text-xs sm:text-sm font-bold text-white">{destination.processingDays}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 rounded-xl bg-white/5 border border-white/10 p-3 backdrop-blur-sm">
                  <Calendar className="size-4 text-blue-400 shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/60 uppercase font-medium">Stay Duration</span>
                    <span className="text-xs sm:text-sm font-bold text-white">{selectedVisa.duration}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 rounded-xl bg-white/5 border border-white/10 p-3 backdrop-blur-sm col-span-2 sm:col-span-1">
                  <Layers className="size-4 text-purple-400 shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/60 uppercase font-medium">Entries</span>
                    <span className="text-xs sm:text-sm font-bold text-white">{selectedVisa.entries}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Hero Visual Card */}
            <div className="lg:col-span-5">
              <div className="relative aspect-[4/3] sm:aspect-[16/10] lg:aspect-[4/3] rounded-2xl overflow-hidden border border-white/20 shadow-2xl">
                <Image
                  src={destination.heroImage}
                  alt={destination.name}
                  fill
                  priority
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-white">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{destination.flag}</span>
                    <span className="text-sm font-bold">{destination.name} Embassy Filing Kit</span>
                  </div>
                  <span className="text-xs font-semibold bg-emerald-500/90 text-white px-2.5 py-1 rounded-full backdrop-blur-xs">
                    Verified Guidelines
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content & Sticky Action Card */}
      <section className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pt-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Details, Visa Types, Requirements, FAQs */}
          <div className="lg:col-span-7 space-y-10">
            {/* Visa Types Selection */}
            {destination.visas.length > 1 && (
              <div className="space-y-4">
                <div className="space-y-1">
                  <h2 className="text-lg font-bold text-foreground">Select Visa Category</h2>
                  <p className="text-xs text-muted-foreground">
                    Choose the visa type matching your travel purpose.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {destination.visas.map((v) => {
                    const isSelected = v.id === selectedVisa.id;
                    return (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => setSelectedVisaId(v.id)}
                        className={cn(
                          "flex flex-col text-left p-4 rounded-xl border transition-all text-xs space-y-2 relative cursor-pointer",
                          isSelected
                            ? "border-primary bg-primary/5 ring-1 ring-primary shadow-xs"
                            : "border-border bg-card hover:border-border/80 hover:bg-muted/40",
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-bold text-sm text-foreground">{v.name}</span>
                          {isSelected && (
                            <CheckCircle2 className="size-4 text-primary shrink-0 mt-0.5" />
                          )}
                        </div>
                        <p className="text-muted-foreground line-clamp-2">{v.description}</p>
                        <div className="flex items-center gap-2 text-[11px] font-semibold text-primary pt-1">
                          <span>{v.duration}</span>
                          <span>•</span>
                          <span>{v.entries}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Overview Section */}
            <div className="rounded-2xl border border-border bg-card p-6 space-y-3 shadow-xs">
              <h2 className="text-lg font-bold text-foreground">Overview &amp; Submission Mode</h2>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                {destination.overview}
              </p>
              <div className="inline-flex items-center gap-2 rounded-lg bg-muted px-3 py-1.5 text-xs font-semibold text-foreground">
                <Globe2 className="size-3.5 text-primary" />
                <span>Submission Mode: {destination.filingModeLabel}</span>
              </div>
            </div>

            {/* Required Documents Checklist */}
            <div className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-foreground">
                  Required Documents Checklist
                </h2>
                <p className="text-xs text-muted-foreground">
                  Torii verifies and organizes every document to ensure strict compliance with consular standards.
                </p>
              </div>

              <div className="rounded-2xl border border-border bg-card p-5 sm:p-6 shadow-xs divide-y divide-border/60">
                {selectedVisa.requiredDocuments.map((doc, idx) => (
                  <div key={idx} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                    <CheckCircle2 className="size-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span className="text-xs sm:text-sm text-foreground font-medium leading-relaxed">
                      {doc}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* How Torii Prepares Your File (3 Steps) */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-foreground">
                How Your Dossier is Prepared
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <span className="text-xs font-bold text-primary font-mono">STEP 1</span>
                  <h3 className="text-xs sm:text-sm font-bold text-foreground">Quick Digital Intake</h3>
                  <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                    Enter basic traveler details. Scan your passport so OCR auto-fills identity fields without errors.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <span className="text-xs font-bold text-primary font-mono">STEP 2</span>
                  <h3 className="text-xs sm:text-sm font-bold text-foreground">Auto-Generated Dossier</h3>
                  <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                    Torii generates your official typed embassy PDF form, Cover Letter, and Schedule of Stay.
                  </p>
                </div>

                <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                  <span className="text-xs font-bold text-primary font-mono">STEP 3</span>
                  <h3 className="text-xs sm:text-sm font-bold text-foreground">Submit &amp; Track</h3>
                  <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                    Download your print-ready dossier for VFS / IVAC submission or direct eVisa download.
                  </p>
                </div>
              </div>
            </div>

            {/* FAQs Accordion */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <HelpCircle className="size-5 text-primary" />
                <h2 className="text-lg font-bold text-foreground">Frequently Asked Questions</h2>
              </div>

              <div className="rounded-2xl border border-border bg-card divide-y divide-border/60 overflow-hidden shadow-xs">
                {destination.faqs.map((faq, idx) => {
                  const isOpen = openFaq === idx;
                  return (
                    <div key={idx} className="transition-colors">
                      <button
                        type="button"
                        onClick={() => setOpenFaq(isOpen ? null : idx)}
                        className="w-full flex items-center justify-between gap-4 p-4 text-left font-semibold text-xs sm:text-sm text-foreground hover:bg-muted/40 cursor-pointer"
                      >
                        <span>{faq.question}</span>
                        <ChevronDown
                          className={cn(
                            "size-4 shrink-0 text-muted-foreground transition-transform duration-200",
                            isOpen && "rotate-180 text-primary",
                          )}
                        />
                      </button>
                      {isOpen && (
                        <div className="px-4 pb-4 text-xs sm:text-sm text-muted-foreground leading-relaxed">
                          {faq.answer}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column: Sticky Pricing & Action Card */}
          <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-4">
            <div className="rounded-2xl border border-border bg-card p-6 shadow-xl space-y-5">
              {/* Header */}
              <div className="space-y-1 pb-4 border-b border-border">
                <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
                  <Sparkles className="size-3" />
                  <span>Embassy-Compliant Dossier</span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-foreground">
                  {selectedVisa.name}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Official preparation kit with full document verification.
                </p>
              </div>

              {/* Price Breakdown */}
              <div className="space-y-3 text-xs sm:text-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Government Consular Fee</span>
                  <span className="font-semibold text-foreground">{selectedVisa.governmentFee}</span>
                </div>

                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Torii Service &amp; Dossier Fee</span>
                  <span className="font-semibold text-foreground">{selectedVisa.toriiFee}</span>
                </div>

                <div className="pt-2 border-t border-border flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-foreground">Total Fee</span>
                    <span className="text-[10px] text-muted-foreground">All statutory &amp; kit fees included</span>
                  </div>
                  <span className="text-lg sm:text-xl font-extrabold text-primary">
                    {selectedVisa.totalDisplay}
                  </span>
                </div>
              </div>

              {/* Primary Start Application CTA */}
              <button
                type="button"
                onClick={handleStartApplication}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3.5 text-sm font-bold text-primary-foreground shadow-lg hover:bg-primary/90 transition-all cursor-pointer group"
              >
                <span>Start Application</span>
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
              </button>

              {/* Trust & Guarantee points */}
              <div className="space-y-2.5 pt-2 border-t border-border/80 text-[11px] text-muted-foreground">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-emerald-500 shrink-0" />
                  <span>Guaranteed on-time dossier delivery or 100% refund</span>
                </div>
                <div className="flex items-center gap-2">
                  <FileText className="size-3.5 text-blue-500 shrink-0" />
                  <span>Includes official MOFA typed PDF form &amp; Cover Letter</span>
                </div>
                <div className="flex items-center gap-2">
                  <Lock className="size-3.5 text-purple-500 shrink-0" />
                  <span>256-bit encrypted data privacy with verified consular kit</span>
                </div>
              </div>
            </div>

            {/* Need Help Card */}
            <div className="rounded-xl border border-border/80 bg-muted/30 p-4 text-xs space-y-1">
              <span className="font-bold text-foreground">Have specific travel questions?</span>
              <p className="text-muted-foreground text-[11px]">
                Our consular team and built-in AI assistant guide you through each requirement step-by-step.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Floating Bottom Bar on Mobile */}
      <div className="fixed inset-x-0 bottom-0 z-40 lg:hidden border-t border-border bg-background/95 p-3 backdrop-blur-md shadow-2xl flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <span className="text-[10px] text-muted-foreground uppercase font-medium">Total Price</span>
          <span className="text-sm font-bold text-foreground">{selectedVisa.totalDisplay}</span>
        </div>

        <button
          type="button"
          onClick={handleStartApplication}
          className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-primary py-2.5 px-4 text-xs font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-colors"
        >
          <span>Start Application</span>
          <ArrowRight className="size-3.5" />
        </button>
      </div>
    </div>
  );
}
