import { SiteHeader } from "@/components/landing/site-header";
import { Hero } from "@/components/landing/hero";
import { Outcomes } from "@/components/landing/outcomes";
import { Jurisdictions } from "@/components/landing/jurisdictions";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Features } from "@/components/landing/features";
import { Trust } from "@/components/landing/trust";
import { Pricing } from "@/components/landing/pricing";
import { Blog } from "@/components/landing/blog";
import { Faq } from "@/components/landing/faq";
import { CtaBand } from "@/components/landing/cta-band";
import { SiteFooter } from "@/components/landing/site-footer";
import { StickyCta } from "@/components/landing/sticky-cta";
import { LangProvider } from "@/components/landing/i18n";

export default function Home() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <Hero />
          <Outcomes />
          <Jurisdictions />
          <HowItWorks />
          <Features />
          <Trust />
          <Pricing />
          <Blog />
          <Faq />
          <CtaBand />
        </main>
        <SiteFooter />
        <StickyCta />
      </div>
    </LangProvider>
  );
}
