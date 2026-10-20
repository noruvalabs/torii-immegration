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
  Sparkles,
  HelpCircle,
  Lock,
  FileCheck,
  Zap,
  Check,
  ClipboardList,
  Building2,
  CreditCard,
  Send,
  UserCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { type DestinationInfo, type DestinationVisa } from "@/lib/destinations-data";
import { CountryFlag } from "@/components/landing/country-flag";
import { cn } from "@/lib/utils";

function cleanVisaName(name: string): string {
  // Strip parenthetical non-English characters like (短期滞在) or (知人訪問) for a clean display
  return name.replace(/\s*\([\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\d\s-]+\)/g, "").trim();
}

export function VisaDetailView({ destination }: { destination: DestinationInfo }) {
  const router = useRouter();
  const { user } = useAuth();
  const [selectedVisaId, setSelectedVisaId] = useState<string>(
    destination.visas[0]?.id || "",
  );
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const selectedVisa: DestinationVisa =
    destination.visas.find((v) => v.id === selectedVisaId) || destination.visas[0];

  const isPortalConcierge = destination.serviceModel === "portal_payment_concierge";

  function handleStartApplication() {
    const targetUrl = `/scope?destination=${destination.code}`;
    if (user) {
      router.push(targetUrl);
    } else {
      router.push(`/login?redirect=${encodeURIComponent(targetUrl)}`);
    }
  }

  function scrollToSection(id: string) {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  }

  // Separate user-provided documents from Torii auto-generated kit items
  const userDocuments = selectedVisa.requiredDocuments.filter(
    (doc) => !doc.toLowerCase().includes("torii"),
  );

  const toriiGeneratedDocuments = isPortalConcierge
    ? [
        `Direct Portal Online Registration & Application Filing on Official Govt Portal`,
        `Consular Embassy Fee Payment Receipt & Official Invoice`,
        `Formal Consular Cover Letter addressed to the High Commission / Mission`,
        `Official Appointment Confirmation & Submission Barcode Sheet`,
      ]
    : [
        `Official ${destination.name} Typed Visa Application Form (Embassy PDF)`,
        "Formal Consular Cover Letter addressed to the Embassy / Mission",
        destination.slug === "japan"
          ? "Day-by-Day Schedule of Stay (Official Embassy Itinerary)"
          : "Structured Travel Plan & Stay Details",
        "Pre-Submission Compliance & Verification Checklist",
      ];

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-[#080B14] pt-24 pb-14 text-white">
        {/* Ambient Glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-32 left-1/3 size-[500px] rounded-full bg-primary/20 blur-[140px]" />
          <div className="absolute top-1/2 -right-20 size-[420px] rounded-full bg-indigo-500/15 blur-[130px]" />
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
            <div className="lg:col-span-7 space-y-5">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1 text-xs font-semibold backdrop-blur-md">
                <CountryFlag code={destination.code} className="size-4 shrink-0 shadow-xs" />
                <span>
                  {isPortalConcierge
                    ? "✨ All-in-One: We Submit Online & Pay Gov Fees"
                    : destination.bannerTag || `${destination.name} Embassy Dossier`}
                </span>
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
                {destination.name} Visa for Bangladeshi Citizens
              </h1>

              <p className="text-sm sm:text-base text-white/80 max-w-xl leading-relaxed">
                {isPortalConcierge
                  ? "Fill your details once on Torii. You never have to deal with complicated government portals or foreign currency payment roadblocks — our operations team files online, pays the government fee, and delivers your confirmed barcode & invoice."
                  : `${destination.shortDescription} Torii prepares your official typed embassy forms, cover letter, and itinerary so you can submit with zero errors.`}
              </p>

              {/* Direct Hero Call To Action */}
              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <button
                  type="button"
                  onClick={handleStartApplication}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/25 hover:bg-primary/90 transition-all cursor-pointer group"
                >
                  <span>
                    {isPortalConcierge
                      ? `Start ${destination.name} Application`
                      : `Start ${destination.name} Application`}
                  </span>
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                </button>

                <button
                  type="button"
                  onClick={() => scrollToSection("requirements")}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 px-5 py-3.5 text-sm font-semibold text-white backdrop-blur-sm transition-all cursor-pointer"
                >
                  <span>Check Requirements</span>
                </button>
              </div>

              <div className="flex items-center gap-2 text-xs text-white/70">
                <Zap className="size-3.5 text-amber-400 shrink-0" />
                <span>
                  {isPortalConcierge
                    ? "Zero portal hassle • Save & reuse your profile anytime • We pay fees on your behalf"
                    : "Takes ~3 minutes • Free to start • Low service charge"}
                </span>
              </div>

              {/* Key Quick Metric Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3">
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
                  <Building2 className="size-4 text-purple-400 shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/60 uppercase font-medium">Service Model</span>
                    <span className="text-xs sm:text-sm font-bold text-white truncate" title={destination.filingModeLabel}>
                      {isPortalConcierge ? "We File & Pay Online" : "Official Form & Dossier"}
                    </span>
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
                    <CountryFlag code={destination.code} className="size-5 shrink-0 shadow-xs" />
                    <span className="text-sm font-bold">{destination.name} Filing Service</span>
                  </div>
                  <span className="text-xs font-semibold bg-emerald-500/90 text-white px-2.5 py-1 rounded-full backdrop-blur-xs">
                    {isPortalConcierge ? "Full Concierge" : "Verified Guidelines"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3-Step "How It Works" Roadmap tailored to the exact model */}
      <section className="border-b border-border bg-card/60 py-6">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-primary">
                {isPortalConcierge
                  ? "How Torii Handles Your Application • 3 Simple Steps"
                  : "How It Works • 3 Simple Steps"}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {isPortalConcierge
                  ? "You give us your info once; we handle the government website, fee payment, and paperwork."
                  : "Here is exactly what you will do to get your embassy dossier ready."}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {isPortalConcierge ? (
              <>
                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                    1
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">Fill Once on Torii (3 Mins)</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      Enter your details once. Your profile is saved so you can reuse it anytime for family or future trips without retyping.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    2
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">We File Online &amp; Pay Gov Fees</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      Torii staff logs into the official government portal, enters all verified data, and pays the government visa fee for you.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    3
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">Get Confirmed Slip &amp; Invoices</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      Download your official barcode registration slip, payment receipt, and complete filing kit from your dashboard.
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                    1
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">Quick 3-Min Intake (Free)</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      Enter travel dates and scan your passport. Auto-fill prevents spelling and date mistakes.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    2
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">Torii Generates Official Forms</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      We generate your official typed 2-page form, cover letter, and day-by-day itinerary with 100% compliance.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-4 shadow-xs">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    3
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-foreground">Print &amp; Submit in Person</span>
                    <p className="text-[11px] sm:text-xs text-muted-foreground leading-relaxed">
                      Download your print-ready dossier and submit at VFS/Embassy. Pay the government fee only upon visa approval!
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      {/* Main Content & Sticky Action Card */}
      <section id="requirements" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 pt-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Visa Category, Required Documents, FAQs */}
          <div className="lg:col-span-7 space-y-8">
            {/* Step 1: Visa Category Selection */}
            {destination.visas.length > 1 && (
              <div className="space-y-3">
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-primary uppercase tracking-wider">
                    Select Your Travel Purpose
                  </span>
                  <h2 className="text-base sm:text-lg font-bold text-foreground">
                    Which visa are you applying for?
                  </h2>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {destination.visas.map((v) => {
                    const isSelected = v.id === selectedVisa.id;
                    const cleanName = cleanVisaName(v.name);
                    return (
                      <button
                        key={v.id}
                        type="button"
                        onClick={() => setSelectedVisaId(v.id)}
                        className={cn(
                          "flex flex-col text-left p-4 rounded-xl border transition-all text-xs space-y-2 relative cursor-pointer",
                          isSelected
                            ? "border-primary bg-primary/5 ring-2 ring-primary/40 shadow-xs"
                            : "border-border bg-card hover:border-border/80 hover:bg-muted/30",
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-bold text-sm text-foreground">{cleanName}</span>
                          {isSelected ? (
                            <CheckCircle2 className="size-4 text-primary shrink-0 mt-0.5" />
                          ) : (
                            <span className="size-4 rounded-full border border-muted-foreground/30 shrink-0 mt-0.5" />
                          )}
                        </div>
                        <p className="text-muted-foreground text-[11px] line-clamp-2 leading-relaxed">
                          {v.description}
                        </p>
                        <div className="flex items-center gap-2 text-[11px] font-semibold text-primary pt-1">
                          <span>⏱ {v.duration}</span>
                          <span>•</span>
                          <span>{v.entries}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step 2: Document Checklist (Split into "You Provide" vs "Torii Prepares/Files") */}
            <div className="space-y-4">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-primary uppercase tracking-wider">
                  Checklist For {cleanVisaName(selectedVisa.name)}
                </span>
                <h2 className="text-base sm:text-lg font-bold text-foreground">
                  Required Documents Checklist
                </h2>
                <p className="text-xs text-muted-foreground">
                  {isPortalConcierge
                    ? "Upload the basic documents below. Our staff completes the online government portal filing and pays the consular fee."
                    : "Gather the basic personal documents below. Torii handles all the complicated official embassy paperwork."}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {/* 1. What you provide */}
                <div className="rounded-2xl border border-border bg-card p-5 shadow-xs space-y-3">
                  <div className="flex items-center gap-2 text-foreground font-bold text-sm pb-2 border-b border-border">
                    <ClipboardList className="size-4 text-primary" />
                    <span>Documents You Provide</span>
                  </div>

                  <div className="divide-y divide-border/60">
                    {userDocuments.map((doc, idx) => (
                      <div key={idx} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
                        <Check className="size-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span className="text-xs sm:text-sm text-foreground font-medium leading-relaxed">
                          {doc}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. What Torii prepares/handles for you */}
                <div className="rounded-2xl border border-primary/30 bg-primary/5 p-5 shadow-xs space-y-3">
                  <div className="flex items-center gap-2 text-foreground font-bold text-sm pb-2 border-b border-primary/20">
                    <FileCheck className="size-4 text-primary" />
                    <span className="text-primary font-bold">
                      {isPortalConcierge
                        ? "What Torii Handles & Delivers For You"
                        : "Documents Torii Prepares For You"}
                    </span>
                    <span className="ml-auto text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                      Included
                    </span>
                  </div>

                  <div className="divide-y divide-primary/10">
                    {toriiGeneratedDocuments.map((doc, idx) => (
                      <div key={idx} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
                        <CheckCircle2 className="size-4 text-primary shrink-0 mt-0.5" />
                        <span className="text-xs sm:text-sm text-foreground font-medium leading-relaxed">
                          {doc}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* FAQs Accordion */}
            <div className="space-y-4 pt-2">
              <div className="flex items-center gap-2">
                <HelpCircle className="size-4.5 text-primary" />
                <h2 className="text-base sm:text-lg font-bold text-foreground">Frequently Asked Questions</h2>
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

          {/* Right Column: Sticky Action & Launchpad Card */}
          <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-4">
            <div className="rounded-2xl border border-border bg-card p-6 shadow-xl space-y-5">
              {/* Header */}
              <div className="space-y-1.5 pb-4 border-b border-border">
                <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                  <Sparkles className="size-3" />
                  <span>{isPortalConcierge ? "All-In-One Concierge Service" : "Step 1: Free Online Intake"}</span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-foreground">
                  {cleanVisaName(selectedVisa.name)}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {isPortalConcierge
                    ? "Provide your details once on Torii. Our team completes official portal submission and pays the government fee on your behalf."
                    : "Start your online questionnaire now. No payment is required to check requirements and fill your details."}
                </p>
              </div>



              {/* Primary Call to Action Button */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleStartApplication}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3.5 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all cursor-pointer group"
                >
                  <span>
                    {isPortalConcierge ? "Start Online Application" : "Start Application Now"}
                  </span>
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                </button>

                <p className="text-center text-[11px] text-muted-foreground">
                  {isPortalConcierge
                    ? "✓ No portal hassle • We pay & submit for you • Official receipt"
                    : "✓ Free to start • ~3 mins • Progress saved automatically"}
                </p>
              </div>

              {/* Trust & Guarantee points */}
              <div className="space-y-2.5 pt-3 border-t border-border/80 text-[11px] text-muted-foreground">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-3.5 text-emerald-500 shrink-0" />
                  <span>100% money-back guarantee on submission accuracy</span>
                </div>
                <div className="flex items-center gap-2">
                  <FileText className="size-3.5 text-blue-500 shrink-0" />
                  <span>
                    {isPortalConcierge
                      ? "Official barcode registration slip & payment invoice"
                      : "Generates official typed PDF form & formal cover letter"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <UserCheck className="size-3.5 text-indigo-500 shrink-0" />
                  <span>Profile saved securely — reuse for future trips &amp; family</span>
                </div>
                <div className="flex items-center gap-2">
                  <Lock className="size-3.5 text-purple-500 shrink-0" />
                  <span>256-bit encrypted data privacy</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Floating Bottom Bar on Mobile */}
      <div className="fixed inset-x-0 bottom-0 z-40 lg:hidden border-t border-border bg-background/95 p-3 backdrop-blur-md shadow-2xl flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold uppercase">
            {isPortalConcierge ? "All-in-One Service" : "Free to start"}
          </span>
          <span className="text-xs font-semibold text-foreground">
            {isPortalConcierge ? "We submit & pay" : "Step 1: 3-Min Intake"}
          </span>
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
