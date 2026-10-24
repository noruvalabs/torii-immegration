import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { Loader2 } from "lucide-react";
import { SiteHeader } from "@/components/landing/site-header";
import { VisaFooter } from "@/components/visa/visa-footer";
import { VisaDetailView } from "@/components/visa/visa-detail-view";
import { LangProvider } from "@/components/landing/i18n";
import { DESTINATIONS } from "@/lib/destinations-data";
import { ALL_COUNTRIES } from "@/lib/countries";

export function generateStaticParams() {
  return Object.keys(DESTINATIONS).map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ from?: string; passport?: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const resolvedSearchParams = await searchParams;
  const dest = DESTINATIONS[slug];
  if (!dest) return {};

  const originCode = resolvedSearchParams?.from || resolvedSearchParams?.passport;
  const matchedCountry = originCode
    ? ALL_COUNTRIES.find((c) => c.code.toUpperCase() === originCode.toUpperCase())
    : null;

  const title = matchedCountry
    ? `${dest.name} Visa for ${matchedCountry.name} Citizens | Torii`
    : `${dest.name} Visa Application & Concierge | Torii`;

  return {
    title,
    description: dest.shortDescription,
  };
}

export default async function VisaPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const destination = DESTINATIONS[slug];

  if (!destination) {
    notFound();
  }

  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col bg-background selection:bg-primary/20 selection:text-primary">
        <SiteHeader />
        <main className="flex-1">
          <Suspense
            fallback={
              <div className="flex min-h-[60vh] items-center justify-center">
                <Loader2 className="size-8 animate-spin text-muted-foreground" />
              </div>
            }
          >
            <VisaDetailView destination={destination} />
          </Suspense>
        </main>
        <VisaFooter />
      </div>
    </LangProvider>
  );
}
