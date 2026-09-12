import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { LegalPageView } from "@/components/legal/legal-page-view";

export const metadata: Metadata = {
  title: "Cookie Policy",
  description:
    "Torii Cookie Policy. Essential authentication, functional cookies, and privacy-preserving storage practices.",
};

export default function CookiesPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <LegalPageView policyKey="cookies" />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
