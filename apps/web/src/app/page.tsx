import { SiteHeader } from "@/components/landing/site-header";
import { AtlysHero } from "@/components/landing/atlys-hero";
import { DestinationCards } from "@/components/landing/destination-cards";
import { AtlysSteps } from "@/components/landing/atlys-steps";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";

export default function Home() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col bg-background selection:bg-primary/20 selection:text-primary">
        <SiteHeader />
        <main className="flex-1">
          <AtlysHero />
          <DestinationCards />
          <AtlysSteps />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
