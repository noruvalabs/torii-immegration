"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight, Clock } from "lucide-react";
import { POPULAR_DESTINATIONS } from "@/lib/destinations-data";

export function DestinationCards() {
  return (
    <section id="destinations" className="py-12 sm:py-16 lg:py-20 bg-background">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        {/* 3 Large Destination Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-7">
          {POPULAR_DESTINATIONS.map((destination) => (
            <Link
              key={destination.slug}
              href={`/visa/${destination.slug}`}
              className="group relative flex flex-col justify-end overflow-hidden rounded-2xl border border-border/80 bg-card shadow-lg hover:shadow-2xl hover:border-primary/50 transition-all duration-300 h-[420px] sm:h-[450px]"
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
                {/* Gradient Overlays for readable text */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/45 to-black/20 group-hover:from-black/98 transition-colors" />
              </div>

              {/* Top Badges */}
              <div className="relative z-10 flex items-center justify-between p-4 mb-auto">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1 text-xs font-bold text-white backdrop-blur-md shadow-xs border border-white/20">
                  <span className="text-base">{destination.flag}</span>
                  <span>{destination.name}</span>
                </span>

                <span className="inline-flex items-center gap-1.5 rounded-full bg-black/50 px-2.5 py-1 text-[11px] font-medium text-white/95 backdrop-blur-md border border-white/10">
                  <Clock className="size-3 text-emerald-400" />
                  <span>{destination.processingDays}</span>
                </span>
              </div>

              {/* Bottom Card Content */}
              <div className="relative z-10 p-5 sm:p-6 space-y-3 text-white">
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold tracking-wider uppercase text-primary-foreground/90 bg-primary/80 px-2 py-0.5 rounded-sm inline-block">
                    {destination.bannerTag}
                  </span>
                  <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-white group-hover:text-primary-foreground transition-colors">
                    {destination.name} Visa
                  </h3>
                  <p className="text-xs sm:text-[13px] text-white/80 line-clamp-2 leading-relaxed">
                    {destination.shortDescription}
                  </p>
                </div>

                {/* Pricing & Call to Action Bar */}
                <div className="flex items-center justify-between pt-3 border-t border-white/15">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-white/60 uppercase font-medium">Government Fee</span>
                    <span className="text-xs sm:text-sm font-bold text-white">
                      {destination.visas[0]?.governmentFee.split("—")[0] || "Standard"}
                    </span>
                  </div>

                  <span className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-2 text-xs font-bold text-black shadow-md group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                    <span>View Requirements</span>
                    <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
