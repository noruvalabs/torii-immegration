import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { LegalPageView } from "@/components/legal/legal-page-view";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "Torii Terms of Service. Guided Japanese immigration form preparation software agreement and legal notices.",
};

export default function TermsPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <LegalPageView policyKey="terms" />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
