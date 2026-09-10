import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { LegalPageView } from "@/components/legal/legal-page-view";

export const metadata: Metadata = {
  title: "Refund Policy",
  description:
    "Torii Refund Policy. 30-day money-back guarantee for unused filing passes and technical failure protections.",
};

export default function RefundPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <LegalPageView policyKey="refund" />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
