import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { PricingPageView } from "@/components/landing/pricing-page-view";

export const metadata: Metadata = {
  title: "Pricing — Pay Per Case, No Subscriptions",
  description:
    "Simple, transparent pricing for Japanese visa preparation. Pay per case filing pass with 3 free passes included. 30-day money-back guarantee.",
};

export default function PricingPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <PricingPageView />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
