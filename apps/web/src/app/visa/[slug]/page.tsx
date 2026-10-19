import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/landing/site-header";
import { VisaFooter } from "@/components/visa/visa-footer";
import { VisaDetailView } from "@/components/visa/visa-detail-view";
import { LangProvider } from "@/components/landing/i18n";
import { DESTINATIONS } from "@/lib/destinations-data";

export function generateStaticParams() {
  return Object.keys(DESTINATIONS).map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const dest = DESTINATIONS[slug];
  if (!dest) return {};
  return {
    title: `${dest.name} Visa for Bangladeshi Citizens | Torii`,
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
          <VisaDetailView destination={destination} />
        </main>
        <VisaFooter />
      </div>
    </LangProvider>
  );
}
