"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Clock, Search, X } from "lucide-react";
import { POPULAR_DESTINATIONS } from "@/lib/destinations-data";
import { CountryFlag } from "./country-flag";

export function DestinationCards() {
  const [search, setSearch] = useState("");

  const filteredDestinations = POPULAR_DESTINATIONS.filter((d) => {
    const q = search.toLowerCase().trim();
    if (!q) return true;
    return d.name.toLowerCase().includes(q) || d.code.toLowerCase().includes(q);
  });

  return (
    <section id="destinations" className="py-8 sm:py-12 bg-background">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Small Country Search Bar */}
        <div className="flex items-center justify-between gap-4">
          <div className="relative w-full max-w-xs sm:max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search country (e.g. Japan, Canada)..."
              className="w-full h-9.5 rounded-xl bg-card border border-border/80 pl-9 pr-8 text-xs font-medium text-foreground placeholder:text-muted-foreground shadow-xs outline-none focus:border-primary focus:ring-1 focus:ring-primary/40 transition-all"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title="Clear"
              >
                <X className="size-3.5" />
              </button>
            )}
          </div>

          <span className="text-xs text-muted-foreground font-medium hidden sm:inline-block shrink-0">
            Showing <strong className="text-foreground">{filteredDestinations.length}</strong> of {POPULAR_DESTINATIONS.length} countries
          </span>
        </div>

        {/* Empty State */}
        {filteredDestinations.length === 0 && (
          <div className="rounded-2xl border border-dashed border-border/80 bg-muted/20 p-10 text-center space-y-2">
            <p className="text-sm font-semibold text-foreground">
              No destinations found matching &ldquo;{search}&rdquo;
            </p>
            <button
              type="button"
              onClick={() => setSearch("")}
              className="text-xs text-primary font-bold hover:underline cursor-pointer"
            >
              Clear search filter
            </button>
          </div>
        )}

        {/* Destination Cards Grid */}
        {filteredDestinations.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-7">
            {filteredDestinations.map((destination) => {
              const defaultVisa = destination.visas[0];
              const govtFeeDisplay = defaultVisa?.governmentFee.split("—")[0]?.trim() || "Standard";

              return (
                <Link
                  key={destination.slug}
                  href={`/visa/${destination.slug}`}
                  className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border/80 bg-card shadow-md hover:shadow-2xl hover:border-primary/50 transition-all duration-300 h-[380px] sm:h-[400px]"
                >
                  {/* Full Background Country Photo */}
                  <div className="absolute inset-0 z-0">
                    <Image
                      src={destination.heroImage}
                      alt={destination.name}
                      fill
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                      className="object-cover transition-transform duration-700 ease-out group-hover:scale-105"
                      priority
                    />
                    {/* High contrast gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/50 to-black/20 group-hover:from-black transition-colors" />
                  </div>

                  {/* Top Badges */}
                  <div className="relative z-10 flex items-center justify-between p-4 sm:p-5">
                    <span className="inline-flex items-center gap-2 rounded-full bg-black/40 px-3 py-1.5 text-xs font-bold text-white backdrop-blur-md shadow-xs border border-white/20">
                      <CountryFlag code={destination.code} className="size-4" />
                      <span>{destination.name}</span>
                    </span>

                    <span className="inline-flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-semibold text-white/95 backdrop-blur-md border border-white/10">
                      <Clock className="size-3 text-emerald-400" />
                      <span>{destination.processingDays}</span>
                    </span>
                  </div>

                  {/* Bottom Card Content - Simplified & Clean */}
                  <div className="relative z-10 p-5 sm:p-6 space-y-3.5 text-white">
                    <div className="space-y-1">
                      <h3 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white drop-shadow-md">
                        {destination.name} Visa
                      </h3>
                      <p className="text-xs font-medium text-white/75">
                        {defaultVisa?.duration} · {defaultVisa?.entries}
                      </p>
                    </div>

                    {/* Pricing & Call to Action Bar */}
                    <div className="flex items-center justify-between pt-3 border-t border-white/15">
                      <div className="flex flex-col">
                        <span className="text-[10px] text-white/60 uppercase font-semibold tracking-wider">
                          Govt Fee
                        </span>
                        <span className="text-sm font-bold text-white">
                          {govtFeeDisplay}
                        </span>
                      </div>

                      <span className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2.5 text-xs font-bold text-black shadow-lg group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                        <span>Apply for Visa</span>
                        <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
