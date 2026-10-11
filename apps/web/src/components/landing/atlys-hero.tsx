"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  ArrowRight,
  ShieldCheck,
  Clock,
  CheckCircle2,
  X,
  ChevronRight,
} from "lucide-react";
import { POPULAR_DESTINATIONS } from "@/lib/destinations-data";
import { cn } from "@/lib/utils";

export function AtlysHero() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredDestinations = POPULAR_DESTINATIONS.filter((d) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      d.name.toLowerCase().includes(q) ||
      d.code.toLowerCase().includes(q) ||
      d.tagline.toLowerCase().includes(q)
    );
  });

  function handleSelectCountry(slug: string) {
    router.push(`/visa/${slug}`);
  }

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (filteredDestinations.length > 0) {
      router.push(`/visa/${filteredDestinations[0].slug}`);
    } else if (query.trim()) {
      // Default fallback if query typed
      const first = POPULAR_DESTINATIONS[0];
      router.push(`/visa/${first.slug}`);
    }
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <section className="relative overflow-hidden bg-[#0A0D18] pt-28 pb-16 lg:pt-36 lg:pb-24 text-white">
      {/* Background Ambient Glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 size-[650px] rounded-full bg-primary/20 blur-[140px]" />
        <div className="absolute top-1/3 -right-40 size-[500px] rounded-full bg-purple-600/15 blur-[130px]" />
        <div className="absolute -bottom-20 -left-20 size-[450px] rounded-full bg-blue-600/15 blur-[120px]" />
      </div>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center px-4 sm:px-6 lg:px-8 text-center space-y-7">
        {/* Top Trust Badge */}
        <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3.5 py-1.5 backdrop-blur-md transition-all hover:bg-white/10">
          <span className="flex size-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-white/90">
            Smart Embassy Dossier &amp; Visa Application Preparation
          </span>
          <span className="text-xs text-white/40">·</span>
          <span className="text-xs font-semibold text-primary-foreground/90">Fast &amp; Guaranteed</span>
        </div>

        {/* Main Headline */}
        <div className="space-y-4 max-w-3xl">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl text-white leading-[1.08]">
            Your Visa Dossier.{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              On Time. Guaranteed.
            </span>
          </h1>
          <p className="mx-auto max-w-2xl text-sm sm:text-base lg:text-lg text-white/70 leading-relaxed">
            Select your destination. We prepare your official embassy application form, verified cover letter, and complete filing kit in minutes.
          </p>
        </div>

        {/* Simple Search Country Option */}
        <div ref={containerRef} className="relative w-full max-w-2xl text-left">
          <form
            onSubmit={handleSearchSubmit}
            className={cn(
              "relative flex items-center w-full rounded-2xl border border-white/20 bg-white/10 p-2 sm:p-2.5 backdrop-blur-xl shadow-2xl transition-all duration-200",
              isFocused ? "border-primary/80 ring-2 ring-primary/30 bg-white/15" : "hover:border-white/30",
            )}
          >
            <div className="flex items-center justify-center pl-3 sm:pl-4 text-white/60">
              <Search className="size-5 sm:size-6" />
            </div>

            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsFocused(true);
              }}
              onFocus={() => setIsFocused(true)}
              placeholder="Search destination country (e.g. Japan, India, Saudi Arabia)..."
              className="w-full bg-transparent px-3.5 py-2.5 text-sm sm:text-base font-medium text-white placeholder:text-white/50 outline-none"
            />

            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="p-1.5 text-white/60 hover:text-white transition-colors mr-1 cursor-pointer"
                title="Clear"
              >
                <X className="size-4" />
              </button>
            )}

            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 sm:px-6 py-3 text-xs sm:text-sm font-bold text-primary-foreground shadow-lg hover:bg-primary/90 transition-all active:scale-[0.98] shrink-0 cursor-pointer"
            >
              <span>Search</span>
              <ArrowRight className="size-4" />
            </button>
          </form>

          {/* Autocomplete Dropdown */}
          {isFocused && (
            <div className="absolute left-0 right-0 top-full mt-2 z-50 rounded-2xl border border-white/15 bg-[#121626]/95 backdrop-blur-2xl shadow-2xl overflow-hidden p-2 space-y-1 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">
                {filteredDestinations.length > 0 ? "Available Visa Destinations" : "No matching country found"}
              </div>

              {filteredDestinations.map((d) => (
                <button
                  key={d.slug}
                  type="button"
                  onClick={() => handleSelectCountry(d.slug)}
                  className="w-full flex items-center justify-between p-3 rounded-xl hover:bg-white/10 transition-colors text-left group cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{d.flag}</span>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white group-hover:text-primary-foreground">
                          {d.name} Visa
                        </span>
                        <span className="text-[10px] bg-primary/20 text-primary-foreground px-2 py-0.5 rounded-full font-medium">
                          {d.bannerTag}
                        </span>
                      </div>
                      <span className="text-xs text-white/60">
                        Processing time: {d.processingDays} · {d.visas[0]?.name}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs font-semibold text-white/70 group-hover:text-white">
                    <span>Apply for visa</span>
                    <ChevronRight className="size-4 text-white/40 group-hover:translate-x-0.5 group-hover:text-white transition-all" />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Quick Select Popular Country Badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-3 text-xs text-white/70">
            <span className="text-white/40 font-medium mr-1">Popular:</span>
            {POPULAR_DESTINATIONS.map((d) => (
              <button
                key={d.slug}
                type="button"
                onClick={() => handleSelectCountry(d.slug)}
                className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-white/90 hover:bg-white/15 hover:border-white/30 transition-all cursor-pointer"
              >
                <span>{d.flag}</span>
                <span>{d.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Feature Highlights Pills */}
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-7 text-xs sm:text-sm text-white/80 pt-2">
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
