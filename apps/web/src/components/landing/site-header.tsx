"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { LandingAuthLink } from "@/components/landing-auth-link";
import { ThemeToggle } from "@/components/admin/theme-toggle";
import { LanguageToggle } from "./language-toggle";
import { StartCaseButton } from "./start-case-button";
import { useActiveSection } from "./use-active-section";
import { SECTION_IDS, useHeaderNav, type NavLink } from "./nav";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { cn } from "@/lib/utils";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export function SiteHeader() {
  const pathname = usePathname();
  const { lang } = useLang();
  const t = dictionary[lang];
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const active = useActiveSection(SECTION_IDS);
  const navLinks = useHeaderNav();

  const isLinkActive = (link: NavLink) => {
    if (link.href === pathname) return true;
    if (pathname === "/" && link.href === `/#${active}`) return true;
    return false;
  };

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // A menu left open behind a closed overlay is a trap on a phone; Escape must always
  // reach it, and the page underneath must not scroll while it is up.
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-3 sm:px-6 sm:pt-4">
      <div
        className={cn(
          "relative mx-auto flex h-14 max-w-6xl items-center gap-2 rounded-full border px-3 transition-[background-color,border-color,box-shadow,backdrop-filter] duration-500 ease-out-expo sm:h-16 sm:px-4",
          scrolled
            ? "border-border/60 bg-background/70 shadow-panel backdrop-blur-xl"
            : "border-transparent bg-transparent shadow-none",
        )}
      >
        {/* A single hairline of light along the top edge once the bar docks — the one cue
            that the header has changed state, in place of a jump in size. */}
        {scrolled && (
          <span aria-hidden className="pointer-events-none absolute inset-x-8 top-0 h-px overflow-hidden">
            <span className="animate-trace-x block h-px w-1/3 bg-linear-to-r from-transparent via-primary/70 to-transparent" />
          </span>
        )}

        <Link href="/" className="flex shrink-0 items-center gap-2.5 rounded-full px-1 py-1">
          <ToriiLogo size={30} />
          <span className="text-lg font-semibold tracking-tight sm:text-xl">Torii</span>
        </Link>

        <nav className="ml-6 hidden items-center lg:flex">
          {navLinks.map((link) => {
            const activeMatch = isLinkActive(link);
            return (
              <Link
                key={link.id}
                href={link.href}
                aria-current={activeMatch ? "true" : undefined}
                className={cn(
                  "relative rounded-full px-3 py-2 text-sm font-medium transition-colors duration-200",
                  activeMatch ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {/* The highlight is a sibling rather than a background so it can fade
                    between links instead of snapping. */}
                <span
                  aria-hidden
                  className={cn(
                    "absolute inset-0 rounded-full bg-accent transition-opacity duration-300",
                    activeMatch ? "opacity-100" : "opacity-0",
                  )}
                />
                <span className="relative">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <LanguageToggle className="hidden border-border/70 sm:inline-flex" />
          <ThemeToggle className="size-9 rounded-full border-transparent transition-colors hover:bg-accent" />
          <LandingAuthLink className="hidden sm:inline-flex" />
          <StartCaseButton
            size="sm"
            signedOutLabel={t.nav.headerCta}
            showArrow={false}
            className="hidden rounded-full sm:inline-flex"
          />

          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            className="inline-flex size-9 items-center justify-center rounded-full border border-border/70 bg-card/60 text-foreground transition-colors hover:bg-accent lg:hidden"
          >
            {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </div>

      {/* Mobile navigation. Below `lg` the page previously had no navigation at all — the
          links were simply hidden and nothing replaced them. */}
      <div
        className={cn(
          "mx-auto mt-2 max-w-6xl overflow-hidden rounded-3xl border border-border/60 bg-background/95 shadow-panel-lg backdrop-blur-xl transition-all duration-300 ease-out-expo lg:hidden",
          menuOpen ? "max-h-128 opacity-100" : "pointer-events-none max-h-0 border-transparent opacity-0",
        )}
        // Closed, the panel is still laid out (so it can animate) but must not be
        // reachable by tab or read aloud — `inert` takes its whole subtree out of both,
        // including the toggles and the button at the bottom.
        inert={!menuOpen}
      >
        <nav className="flex flex-col p-3">
          {navLinks.map((link, i) => {
            const activeMatch = isLinkActive(link);
            return (
              <Link
                key={link.id}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                style={{ transitionDelay: menuOpen ? `${60 + i * 40}ms` : "0ms" }}
                className={cn(
                  "rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-300 ease-out-expo",
                  menuOpen ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0",
                  activeMatch ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/60",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center justify-between gap-3 border-t border-border/60 p-3">
          <LanguageToggle className="border-border/70" />
          <LandingAuthLink />
        </div>

        <div className="p-3 pt-0">
          <StartCaseButton
            signedOutLabel={t.nav.headerCta}
            className="w-full rounded-2xl"
          />
        </div>
      </div>
    </header>
  );
}
