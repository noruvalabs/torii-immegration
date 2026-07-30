"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { BLOG_POSTS, getBlogPostMeta } from "./blog-posts";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function BlogPostView({ slug }: { slug: string }) {
  const { lang } = useLang();
  const t = dictionary[lang];
  const meta = getBlogPostMeta(slug);
  const post = BLOG_POSTS[slug]?.[lang];

  if (!meta || !post) return null;

  return (
    <article className="mx-auto max-w-2xl px-6 pb-20 pt-28 sm:pb-28 sm:pt-32">
      <Reveal>
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> {t.blog.viewAll}
        </Link>

        <div className="mt-6 flex items-center gap-3 text-xs">
          <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
            {meta.category[lang]}
          </span>
          <span className="text-muted-foreground">
            {meta.readTime} {t.blog.readTime}
          </span>
        </div>

        <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">{post.title}</h1>
      </Reveal>

      <div className="mt-10 space-y-5 text-base leading-relaxed text-muted-foreground">
        {post.body.map((paragraph, i) => (
          <Reveal key={i} delay={Math.min(i * 60, 240)}>
            <p>{paragraph}</p>
          </Reveal>
        ))}
      </div>
    </article>
  );
}
