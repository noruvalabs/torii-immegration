import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/landing/site-header";
import { SiteFooter } from "@/components/landing/site-footer";
import { BlogPostView } from "@/components/landing/blog-post-view";
import { LangProvider } from "@/components/landing/i18n";
import { BLOG_POST_ORDER } from "@/components/landing/data";
import { BLOG_POSTS } from "@/components/landing/blog-posts";

export function generateStaticParams() {
  return BLOG_POST_ORDER.map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = BLOG_POSTS[slug]?.en;
  if (!post) return {};
  return { title: post.title, description: post.excerpt };
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  if (!BLOG_POSTS[slug]) notFound();

  return (
    <LangProvider>
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main className="flex-1">
          <BlogPostView slug={slug} />
        </main>
        <SiteFooter />
      </div>
    </LangProvider>
  );
}
