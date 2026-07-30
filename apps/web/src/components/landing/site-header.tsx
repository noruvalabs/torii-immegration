"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LandingAuthLink } from "@/components/landing-auth-link";
import { ThemeToggle } from "@/components/admin/theme-toggle";
import { LanguageToggle } from "./language-toggle";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";

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
          "mx-auto flex h-16 max-w-6xl items-center gap-2 rounded-full border px-4 backdrop-blur-lg transition-all duration-300 sm:px-6",
          scrolled
            ? "border-border/60 bg-background/80 shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_8px_30px_-12px_rgba(0,0,0,0.25)] supports-[backdrop-filter]:bg-background/70"
            : "border-transparent bg-transparent shadow-none backdrop-blur-none",
        )}
      >
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl" aria-hidden>
            ⛩️
          </span>
          <span className="text-lg font-semibold tracking-tight">Torii</span>
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
          <Link
            href="/scope"
            className="hidden items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-transform hover:-translate-y-0.5 sm:inline-flex"
          >
            {t.nav.startCase}
          </Link>
        </div>
      </div>
    </header>
  );
}
