import type { Metadata } from "next";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { BlogIndexView } from "@/components/landing/blog-index-view";
import { LangProvider } from "@/components/landing/i18n";

export const metadata: Metadata = {
  title: "Blog",
  description: "Notes on filing it yourself, correctly — how Torii works and what trips people up in a filing.",
};

export default function BlogPage() {
  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <BlogIndexView />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
