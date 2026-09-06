"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LandingAuthLink } from "@/components/landing-auth-link";
import { ThemeToggle } from "@/components/admin/theme-toggle";
import { LanguageToggle } from "./language-toggle";
import { StartCaseButton } from "./start-case-button";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export function SiteHeader() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navLinks = [
    { href: "#dashboard-showcase", label: lang === "ja" ? "実際の画面" : "Live Demo" },
    { href: "#how-it-works", label: t.nav.howItWorks },
    { href: "#coverage", label: lang === "ja" ? "対応ビザ" : "Supported Visas" },
    { href: "#pricing", label: t.nav.pricing },
    { href: "#faq", label: t.nav.faq },
  ];

  return (
    <header className="fixed inset-x-0 top-3 z-40 px-4 sm:px-6">
      <div
        className={cn(
          "mx-auto flex h-16 max-w-6xl items-center gap-2 rounded-full border px-4 backdrop-blur-lg transition-all duration-300 sm:px-6",
          scrolled
            ? "border-border/60 bg-background/80 shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_8px_30px_-12px_rgba(0,0,0,0.25)] supports-[backdrop-filter]:bg-background/70"
            : "border-transparent bg-transparent shadow-none backdrop-blur-none",
        )}
      >
        <Link href="/" className="flex items-center gap-3">
          <ToriiLogo size={34} />
          <span className="text-xl font-bold tracking-tight">Torii</span>
        </Link>

        <nav className="ml-8 hidden items-center gap-0.5 lg:flex">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-full px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <LanguageToggle className="hidden sm:inline-flex" />
          <ThemeToggle className="size-9 border-transparent hover:bg-accent" />
          <LandingAuthLink />
          <StartCaseButton
            size="sm"
            signedOutLabel={t.nav.headerCta}
            showArrow={false}
            className="hidden sm:inline-flex"
          />
        </div>
      </div>
    </header>
  );
}
