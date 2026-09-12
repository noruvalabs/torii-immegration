import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { LangProvider } from "@/components/landing/i18n";
import { LegalPageView } from "@/components/legal/legal-page-view";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Torii Privacy Policy. How we collect, safeguard, and process personal identification and Japanese immigration documents.",
};

export default function PrivacyPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <LegalPageView policyKey="privacy" />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
