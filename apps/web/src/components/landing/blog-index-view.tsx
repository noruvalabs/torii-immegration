"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { BLOG_POST_ORDER } from "./data";
import { BLOG_POSTS } from "./blog-posts";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function BlogIndexView() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <div className="mx-auto max-w-3xl px-6 pb-20 pt-28 sm:pb-28 sm:pt-32">
      <Reveal>
        <p className="text-sm font-medium text-primary">{t.blog.eyebrow}</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t.blog.title}</h1>
        <p className="mt-4 text-lg text-muted-foreground">{t.blog.body}</p>
      </Reveal>

      <div className="mt-14 divide-y divide-border/60 border-t border-border/60">
        {BLOG_POST_ORDER.map((meta, i) => {
          const post = BLOG_POSTS[meta.slug][lang];
          return (
            <Reveal key={meta.slug} delay={i * 90}>
              <Link href={`/blog/${meta.slug}`} className="group flex flex-col gap-2 py-8">
                <div className="flex items-center gap-3 text-xs">
                  <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                    {meta.category[lang]}
                  </span>
                  <span className="text-muted-foreground">
                    {meta.readTime} {t.blog.readTime}
                  </span>
                </div>
                <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight transition-colors group-hover:text-primary">
                  {post.title}
                  <ArrowUpRight className="size-4 shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </h2>
                <p className="text-sm leading-relaxed text-muted-foreground">{post.excerpt}</p>
              </Link>
            </Reveal>
          );
        })}
      </div>
    </div>
  );
}
