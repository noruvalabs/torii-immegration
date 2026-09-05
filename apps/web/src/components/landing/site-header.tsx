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
    { href: "#outcomes", label: t.nav.outcomes },
    { href: "#how-it-works", label: t.nav.howItWorks },
    { href: "#features", label: t.nav.features },
    { href: "#pricing", label: t.nav.pricing },
    { href: "#blog", label: t.nav.blog },
    { href: "#faq", label: t.nav.faq },
  ];

  return (
    <header className="fixed inset-x-0 top-3 z-40 px-4 sm:px-6">
      <div
        className={cn(
          // The bar keeps its own background at every scroll position now. It used to be
          // transparent until the page moved, which worked over a pale hero and fails over
          // the dark one: every control in here paints with `foreground`, so at rest they
          // were dark ink on dark ink. Scrolling deepens the shadow instead.
          "mx-auto flex h-16 max-w-6xl items-center gap-2 rounded-full border border-border/60 bg-background/80 px-4 backdrop-blur-lg transition-shadow duration-300 supports-[backdrop-filter]:bg-background/70 sm:px-6",
          scrolled
            ? "shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_8px_30px_-12px_rgba(0,0,0,0.25)]"
            : "shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset,0_2px_12px_-8px_rgba(0,0,0,0.2)]",
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

        <div className="ml-auto flex items-center gap-2.5">
          <LanguageToggle className="hidden sm:inline-flex" />
          <ThemeToggle className="size-9 border-transparent hover:bg-accent" />
          <LandingAuthLink />
          <StartCaseButton showArrow={false} className="hidden px-4 py-2 shadow-sm sm:inline-flex" />
        </div>
      </div>
    </header>
  );
}
