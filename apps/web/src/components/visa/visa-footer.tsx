"use client";

import Link from "next/link";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export function VisaFooter() {
  return (
    <footer className="border-t border-border bg-card/50 text-foreground py-10 mt-12">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 pb-6 border-b border-border/60">
          <Link href="/" className="flex items-center gap-2.5">
            <ToriiLogo size={28} />
            <span className="text-base font-bold tracking-tight">Torii</span>
          </Link>

          <nav className="flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
            <Link href="/" className="hover:text-foreground transition-colors">
              Home
            </Link>
            <Link href="/#destinations" className="hover:text-foreground transition-colors">
              All Visas
            </Link>
            <Link href="/#how-it-works" className="hover:text-foreground transition-colors">
              How It Works
            </Link>
            <Link href="/pricing" className="hover:text-foreground transition-colors">
              Pricing
            </Link>
            <Link href="/about" className="hover:text-foreground transition-colors">
              About
            </Link>
            <Link href="/help" className="hover:text-foreground transition-colors">
              Help &amp; Support
            </Link>
          </nav>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} Torii. Guided visa preparation &amp; concierge platform.</p>

          <div className="flex items-center gap-4 text-xs">
            <Link href="/privacy" className="hover:text-foreground transition-colors">
              Privacy Policy
            </Link>
            <span>·</span>
            <Link href="/terms" className="hover:text-foreground transition-colors">
              Terms of Service
            </Link>
            <span>·</span>
            <Link href="/refund" className="hover:text-foreground transition-colors">
              Refund Policy
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
