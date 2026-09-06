"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { Reveal } from "./reveal";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export function SiteFooter() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <footer
      // pb-24 on a phone clears the sticky call to action, which would otherwise sit on
      // top of the last row of footer links.
      className="relative overflow-hidden rounded-t-[2.5rem] border-t border-border/60 bg-muted/40 pb-24 sm:rounded-t-[3.5rem] sm:pb-0"
    >
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -top-24 left-1/2 size-[28rem] -translate-x-1/2 rounded-full bg-primary/10 blur-[100px]"
      />

      <div className="relative mx-auto max-w-6xl px-6 pb-10 pt-16 sm:pt-20">
        <Reveal>
          <div className="flex items-center gap-3">
            <ToriiLogo size={36} />
            <span className="text-xl font-bold tracking-tight">Torii</span>
          </div>

          <h2 className="mt-6 max-w-2xl text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            {t.footer.title}
          </h2>

          <Link
            href="/scope"
            className="group mt-8 inline-flex items-center gap-2 rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow-xs transition-colors hover:bg-primary/90"
          >
            {t.footer.cta}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </Reveal>

        <div className="mt-14 flex flex-col gap-6 border-t border-border/60 pt-8 sm:flex-row sm:items-start sm:justify-between">
          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
            <a href="#dashboard-showcase" className="hover:text-foreground">
              {lang === "ja" ? "実際の画面" : "Live Demo"}
            </a>
            <a href="#how-it-works" className="hover:text-foreground">
              {t.nav.howItWorks}
            </a>
            <a href="#coverage" className="hover:text-foreground">
              {lang === "ja" ? "対応ビザ" : "Supported Visas"}
            </a>
            <a href="#pricing" className="hover:text-foreground">
              {t.nav.pricing}
            </a>
            <a href="#faq" className="hover:text-foreground">
              {t.nav.faq}
            </a>
            <Link href="/login" className="hover:text-foreground">
              {t.nav.signIn}
            </Link>
          </nav>
          <p className="max-w-md text-xs leading-relaxed text-muted-foreground">{t.footer.disclaimer}</p>
        </div>
      </div>
    </footer>
  );
}
