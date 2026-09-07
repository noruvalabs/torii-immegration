"use client";

import { Landmark } from "lucide-react";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

/** Enough copies that translating the track by half its width never exposes bare track. */
const COPIES = 4;

/**
 * The slot a SaaS page fills with customer logos, filled with what Torii actually has to
 * show: the authorities its requirements come from.
 *
 * It scrolls because there are only three of them and a static row of three names reads as
 * a page waiting for more; in motion it reads as a ticker of sources. The spacing lives on
 * the items as a trailing margin rather than as a `gap` on the track — a gap leaves the
 * track half a space short of a whole period, and the loop visibly jumps once a cycle.
 * Every copy but the first is hidden from the accessibility tree, so a screen reader hears
 * each source once.
 */
export function SourceStrip() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <div className="border-y border-border/60 bg-muted/25">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-6 py-6 lg:flex-row lg:gap-8 lg:px-8">
        <p className="shrink-0 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground lg:text-left">
          {t.outcomes.sourcesLabel}
        </p>

        <div className="marquee-mask w-full overflow-hidden">
          <div className="animate-marquee-x flex w-max">
            {Array.from({ length: COPIES }, (_, copy) => (
              <div key={copy} className="flex" aria-hidden={copy > 0}>
                {t.outcomes.sources.map((source) => (
                  <span
                    key={source}
                    className="mr-10 flex shrink-0 items-center gap-2 whitespace-nowrap text-sm font-medium text-foreground/70"
                  >
                    <Landmark className="size-3.5 text-primary/70" />
                    {source}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
