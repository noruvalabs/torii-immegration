import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { AboutView } from "@/components/landing/about-view";

export const metadata: Metadata = {
  title: "About Torii",
  description:
    "Torii's mission, story, and core principles. Making Japanese immigration transparent, accessible, and sourced to official statutory standards.",
};

export default function AboutPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <AboutView />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
