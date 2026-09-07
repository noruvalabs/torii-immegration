import { SiteHeader } from "@/components/landing/site-header";
import { Hero } from "@/components/landing/hero";
import { SourceStrip } from "@/components/landing/source-strip";
import { DashboardShowcase } from "@/components/landing/dashboard-showcase";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Coverage } from "@/components/landing/coverage";
import { Pricing } from "@/components/landing/pricing";
import { Faq } from "@/components/landing/faq";
import { CtaBand } from "@/components/landing/cta-band";
import { SiteFooter } from "@/components/landing/site-footer";
import { StickyCta } from "@/components/landing/sticky-cta";
import { ScrollProgress } from "@/components/landing/scroll-progress";
import { LangProvider } from "@/components/landing/i18n";

export default function Home() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <ScrollProgress />
        <SiteHeader />
        <main className="flex-1">
          <Hero />
          <SourceStrip />
          <DashboardShowcase />
          <HowItWorks />
          <Coverage />
          <Pricing />
          <Faq />
          <CtaBand />
        </main>
        <SiteFooter />
        <StickyCta />
      </div>
    </LangProvider>
  );
}
