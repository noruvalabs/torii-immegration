"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Plus } from "lucide-react";
import { FAQ_ORDER, type FaqId } from "./data";
import { Reveal } from "./reveal";
import { Section } from "./section";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

/**
 * These were `<details>` elements, which open instantly: the answer appears fully formed
 * and shoves everything below it down the page in one frame. A controlled panel can
 * animate its own height (see `.accordion-panel`), so the list settles instead of
 * snapping — and one open answer at a time keeps the section from unrolling into a wall
 * of text.
 */
export function Faq() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const [open, setOpen] = useState<FaqId | null>(FAQ_ORDER[0]);
  const baseId = useId();

  return (
    <Section id="faq" className="border-t border-border/60">
      <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        {/* The heading column used to be the heading and then several hundred pixels of
            nothing, which on a wide screen is the emptiest part of the page. The card
            gives it a floor and answers the question the accordion cannot: what to read
            if none of these six is your question. */}
        <Reveal className="lg:sticky lg:top-28 lg:self-start">
          <h2 className="text-display text-3xl font-semibold sm:text-4xl lg:text-[2.75rem] lg:leading-[1.1]">
            {t.faq.titleBefore}
            <em className="font-serif italic text-primary">{t.faq.titleAccent}</em>
          </h2>

          <div className="mt-8 rounded-2xl border border-border/70 bg-card p-5 shadow-panel">
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <BookOpen className="size-4" />
              </span>
              <p className="text-sm font-semibold">{t.faq.help.title}</p>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{t.faq.help.body}</p>
            <Link
              href="/blog"
              className="group mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-primary"
            >
              {t.faq.help.cta}
              <ArrowRight className="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>
          </div>
        </Reveal>

        <div className="divide-y divide-border/60">
          {FAQ_ORDER.map((id, i) => {
            const copy = t.faq.items[id];
            const isOpen = open === id;
            const panelId = `${baseId}-${id}`;

            return (
              <Reveal key={id} delay={Math.min(i * 60, 300)}>
                <h3>
                  <button
                    type="button"
                    onClick={() => setOpen(isOpen ? null : id)}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    className="group flex w-full cursor-pointer items-center justify-between gap-6 py-5 text-left"
                  >
                    <span
                      className={cn(
                        "text-base font-medium transition-colors duration-200",
                        isOpen ? "text-foreground" : "text-foreground/85 group-hover:text-foreground",
                      )}
                    >
                      {copy.question}
                    </span>
                    <span
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-full border transition-all duration-300 ease-out-expo",
                        isOpen
                          ? "rotate-45 border-primary/40 bg-primary/10 text-primary"
                          : "border-border/70 text-muted-foreground group-hover:border-foreground/25 group-hover:text-foreground",
                      )}
                    >
                      <Plus className="size-3.5" />
                    </span>
                  </button>
                </h3>

                <div id={panelId} role="region" className="accordion-panel" data-open={isOpen}>
                  <div>
                    <p
                      className={cn(
                        "pb-5 pr-12 text-sm leading-relaxed text-muted-foreground transition-opacity duration-300",
                        isOpen ? "opacity-100" : "opacity-0",
                      )}
                    >
                      {copy.answer}
                    </p>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </Section>
  );
}
