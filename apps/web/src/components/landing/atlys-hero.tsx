"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ChevronDown,
  ShieldCheck,
  Clock,
  CheckCircle2,
  Search,
  Check,
} from "lucide-react";
import { POPULAR_DESTINATIONS } from "@/lib/destinations-data";
import { CountryFlag } from "./country-flag";
import { cn } from "@/lib/utils";

const PASSPORT_OPTIONS = [
  { code: "BD", name: "Bangladesh" },
  { code: "IN", name: "India" },
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "CA", name: "Canada" },
];

export function AtlysHero() {
  const router = useRouter();
  const [selectedPassport, setSelectedPassport] = useState("BD");
  const [selectedDestination, setSelectedDestination] = useState("japan");

  const [passportOpen, setPassportOpen] = useState(false);
  const [destinationOpen, setDestinationOpen] = useState(false);
  const [destinationSearch, setDestinationSearch] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);

  const activePassport =
    PASSPORT_OPTIONS.find((p) => p.code === selectedPassport) || PASSPORT_OPTIONS[0];
  const activeDestination =
    POPULAR_DESTINATIONS.find((d) => d.slug === selectedDestination) || POPULAR_DESTINATIONS[0];

  const filteredDestinations = POPULAR_DESTINATIONS.filter((d) => {
    const q = destinationSearch.toLowerCase().trim();
    if (!q) return true;
    return d.name.toLowerCase().includes(q) || d.code.toLowerCase().includes(q);
  });

  function handleApplyForVisa(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (selectedDestination) {
      router.push(`/visa/${selectedDestination}`);
    }
  }

  // Click outside listener to close dropdowns
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setPassportOpen(false);
        setDestinationOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <section className="relative overflow-hidden bg-[#0A0D18] pt-20 pb-8 lg:pt-24 lg:pb-10 text-white">
      {/* Background Ambient Glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 size-[650px] rounded-full bg-primary/20 blur-[140px]" />
        <div className="absolute top-1/3 -right-40 size-[500px] rounded-full bg-purple-600/15 blur-[130px]" />
        <div className="absolute -bottom-20 -left-20 size-[450px] rounded-full bg-blue-600/15 blur-[120px]" />
      </div>

      <div className="relative mx-auto flex w-full max-w-6xl flex-col items-center px-4 sm:px-6 lg:px-8 text-center space-y-4">
        {/* Route Selector Box */}
        <div
          ref={containerRef}
          className="relative w-full max-w-3xl rounded-2xl border border-white/20 bg-white/10 p-1.5 backdrop-blur-2xl shadow-2xl transition-all"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_auto_1fr_auto] gap-2 items-center bg-[#101424] rounded-xl py-1.5 px-2.5 sm:px-3 border border-white/10">
            {/* Passport Selector Custom Menu */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setPassportOpen(!passportOpen);
                  setDestinationOpen(false);
                }}
                className={cn(
                  "w-full flex items-center justify-between py-1 px-2 rounded-lg text-left transition-all cursor-pointer",
                  passportOpen
                    ? "bg-white/10 ring-1 ring-primary/60"
                    : "hover:bg-white/5",
                )}
              >
                <div className="flex flex-col space-y-0.5">
                  <span className="text-[10px] font-semibold text-white/50 uppercase tracking-wider leading-tight">
                    Passport Country
                  </span>
                  <div className="flex items-center gap-2">
                    <CountryFlag code={activePassport.code} className="size-4.5" />
                    <span className="font-bold text-sm text-white">
                      {activePassport.name}
                    </span>
                  </div>
                </div>
                <ChevronDown
                  className={cn(
                    "size-3.5 text-white/60 transition-transform duration-200",
                    passportOpen && "rotate-180 text-white",
                  )}
                />
              </button>

              {/* Passport Dropdown Menu */}
              {passportOpen && (
                <div className="absolute left-0 right-0 top-full mt-2 z-50 rounded-xl border border-white/15 bg-[#141829] p-1.5 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-1 duration-150 text-left">
                  <div className="px-3 py-1.5 text-[10px] font-semibold uppercase text-white/40 tracking-wider">
                    Select Your Passport
                  </div>
                  <div className="space-y-0.5">
                    {PASSPORT_OPTIONS.map((p) => {
                      const isSelected = p.code === selectedPassport;
                      return (
                        <button
                          key={p.code}
                          type="button"
                          onClick={() => {
                            setSelectedPassport(p.code);
                            setPassportOpen(false);
                          }}
                          className={cn(
                            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer",
                            isSelected
                              ? "bg-primary text-primary-foreground font-bold"
                              : "text-white/90 hover:bg-white/10",
                          )}
                        >
                          <div className="flex items-center gap-2.5">
                            <CountryFlag code={p.code} className="size-4" />
                            <span>{p.name}</span>
                          </div>
                          {isSelected && <Check className="size-3.5" />}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="hidden lg:block h-7 w-px bg-white/10" />

            {/* Destination Selector Custom Menu */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setDestinationOpen(!destinationOpen);
                  setPassportOpen(false);
                }}
                className={cn(
                  "w-full flex items-center justify-between py-1 px-2 rounded-lg text-left transition-all cursor-pointer",
                  destinationOpen
                    ? "bg-white/10 ring-1 ring-primary/60"
                    : "hover:bg-white/5",
                )}
              >
                <div className="flex flex-col space-y-0.5">
                  <span className="text-[10px] font-semibold text-white/50 uppercase tracking-wider leading-tight">
                    Destination Country
                  </span>
                  <div className="flex items-center gap-2">
                    <CountryFlag code={activeDestination.code} className="size-4.5" />
                    <span className="font-bold text-sm text-white">
                      {activeDestination.name}
                    </span>
                  </div>
                </div>
                <ChevronDown
                  className={cn(
                    "size-3.5 text-white/60 transition-transform duration-200",
                    destinationOpen && "rotate-180 text-white",
                  )}
                />
              </button>

              {/* Destination Dropdown Menu */}
              {destinationOpen && (
                <div className="absolute left-0 right-0 sm:right-auto sm:w-80 top-full mt-2 z-50 rounded-xl border border-white/15 bg-[#141829] p-2 shadow-2xl backdrop-blur-2xl animate-in fade-in slide-in-from-top-1 duration-150 text-left">
                  {/* Search filter input */}
                  <div className="relative mb-2">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-white/40" />
                    <input
                      type="text"
                      value={destinationSearch}
                      onChange={(e) => setDestinationSearch(e.target.value)}
                      placeholder="Search country..."
                      className="w-full rounded-lg bg-white/5 pl-8 pr-3 py-1.5 text-xs text-white placeholder:text-white/40 border border-white/10 outline-none focus:border-primary"
                      autoFocus
                    />
                  </div>

                  <div className="max-h-60 overflow-y-auto space-y-0.5 pr-1">
                    {filteredDestinations.map((d) => {
                      const isSelected = d.slug === selectedDestination;
                      return (
                        <button
                          key={d.slug}
                          type="button"
                          onClick={() => {
                            setSelectedDestination(d.slug);
                            setDestinationOpen(false);
                            setDestinationSearch("");
                          }}
                          className={cn(
                            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-colors cursor-pointer",
                            isSelected
                              ? "bg-primary text-primary-foreground font-bold"
                              : "text-white/90 hover:bg-white/10",
                          )}
                        >
                          <div className="flex items-center gap-2.5">
                            <CountryFlag code={d.code} className="size-4" />
                            <span>{d.name}</span>
                          </div>
                          <span className={cn("text-[11px]", isSelected ? "text-primary-foreground/90" : "text-white/50")}>
                            {d.processingDays}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Action Button */}
            <button
              type="button"
              onClick={() => handleApplyForVisa()}
              className="w-full sm:col-span-2 lg:col-span-1 lg:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs sm:text-sm font-bold text-primary-foreground shadow-lg hover:bg-primary/90 hover:shadow-primary/20 transition-all active:scale-[0.98] shrink-0 cursor-pointer"
            >
              <span>Apply for Visa</span>
              <ArrowRight className="size-4" />
            </button>
          </div>
        </div>

        {/* Feature Highlights Badges */}
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-7 text-xs sm:text-sm text-white/80 pt-0">
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
