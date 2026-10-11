"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, ChevronDown, ShieldCheck, Clock, CheckCircle2 } from "lucide-react";
import { POPULAR_DESTINATIONS } from "@/lib/destinations-data";

const PASSPORT_OPTIONS = [
  { code: "BD", name: "Bangladesh", flag: "🇧🇩" },
  { code: "IN", name: "India", flag: "🇮🇳" },
  { code: "US", name: "United States", flag: "🇺🇸" },
  { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
];

export function AtlysHero() {
  const router = useRouter();
  const [selectedPassport, setSelectedPassport] = useState("BD");
  const [selectedDestination, setSelectedDestination] = useState("japan");

  function handleApplyForVisa(e: React.FormEvent) {
    e.preventDefault();
    if (selectedDestination) {
      router.push(`/visa/${selectedDestination}`);
    }
  }

  return (
    <section className="relative overflow-hidden bg-[#0A0D18] pt-24 pb-12 lg:pt-32 lg:pb-16 text-white">
      {/* Background Ambient Glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 size-[650px] rounded-full bg-primary/20 blur-[140px]" />
        <div className="absolute top-1/3 -right-40 size-[500px] rounded-full bg-purple-600/15 blur-[130px]" />
        <div className="absolute -bottom-20 -left-20 size-[450px] rounded-full bg-blue-600/15 blur-[120px]" />
      </div>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center px-4 sm:px-6 lg:px-8 text-center space-y-6">
        {/* Passport Country & Destination Country Route Selector */}
        <form
          onSubmit={handleApplyForVisa}
          className="w-full max-w-3xl rounded-2xl border border-white/15 bg-white/10 p-2 sm:p-2.5 backdrop-blur-xl shadow-2xl transition-all"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_auto] gap-2 items-center bg-white dark:bg-[#141824] rounded-xl p-2 sm:p-2.5">
            {/* Passport Country Selector */}
            <div className="flex flex-col text-left px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Passport Country
              </span>
              <div className="relative mt-1">
                <select
                  value={selectedPassport}
                  onChange={(e) => setSelectedPassport(e.target.value)}
                  className="w-full bg-transparent font-semibold text-sm sm:text-base text-foreground outline-none cursor-pointer appearance-none pr-6"
                >
                  {PASSPORT_OPTIONS.map((p) => (
                    <option key={p.code} value={p.code} className="text-black bg-white dark:bg-gray-900 dark:text-white">
                      {p.flag} {p.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              </div>
            </div>

            {/* Divider */}
            <div className="hidden lg:block h-9 w-px bg-border/80" />

            {/* Destination Country Selector */}
            <div className="flex flex-col text-left px-3 py-2 rounded-lg hover:bg-muted/50 transition-colors">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Destination Country
              </span>
              <div className="relative mt-1">
                <select
                  value={selectedDestination}
                  onChange={(e) => setSelectedDestination(e.target.value)}
                  className="w-full bg-transparent font-semibold text-sm sm:text-base text-foreground outline-none cursor-pointer appearance-none pr-6"
                >
                  {POPULAR_DESTINATIONS.map((d) => (
                    <option key={d.slug} value={d.slug} className="text-black bg-white dark:bg-gray-900 dark:text-white">
                      {d.flag} {d.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              </div>
            </div>

            {/* Action Button */}
            <button
              type="submit"
              className="w-full sm:col-span-2 lg:col-span-1 lg:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground shadow-md hover:bg-primary/90 transition-all active:scale-[0.98] shrink-0 cursor-pointer"
            >
              <span>Apply for Visa</span>
              <ArrowRight className="size-4" />
            </button>
          </div>
        </form>

        {/* Feature Highlights Pills below Route Selector */}
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-7 text-xs sm:text-sm text-white/80 pt-1">
          <div className="flex items-center gap-2">
            <span className="flex size-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="size-3.5" />
            </span>
            <span>99.4% Form Accuracy</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex size-5 items-center justify-center rounded-full bg-blue-500/20 text-blue-400">
              <Clock className="size-3.5" />
            </span>
            <span>Instant Embassy Dossier</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex size-5 items-center justify-center rounded-full bg-purple-500/20 text-purple-400">
              <ShieldCheck className="size-3.5" />
            </span>
            <span>Direct Government Portal Links</span>
          </div>
        </div>
      </div>
    </section>
  );
}
