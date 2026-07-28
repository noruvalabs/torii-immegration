"use client";

import Link from "next/link";
import { ArrowRight, ArrowUpRight } from "lucide-react";
import { BLOG_POST_ORDER } from "./data";
import { BLOG_POSTS } from "./blog-posts";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";

export function Blog() {
  const { lang } = useLang();
  const t = dictionary[lang];

  return (
    <section id="blog" className="border-t border-border/60 bg-muted/30">
      <div className="mx-auto max-w-6xl px-6 py-24 sm:py-32">
        <Reveal className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-xl">
            <p className="text-sm font-medium text-primary">{t.blog.eyebrow}</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{t.blog.title}</h2>
            <p className="mt-4 text-lg text-muted-foreground">{t.blog.body}</p>
          </div>
          <Link
            href="/blog"
            className="group inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            {t.blog.viewAll} <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </Reveal>

        <div className="mt-14 grid gap-5 lg:grid-cols-3">
          {BLOG_POST_ORDER.map((meta, i) => {
            const post = BLOG_POSTS[meta.slug][lang];
            return (
              <Reveal key={meta.slug} delay={i * 100}>
                <Link
                  href={`/blog/${meta.slug}`}
                  className="group flex h-full flex-col rounded-[var(--radius-lg)] border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                      {meta.category[lang]}
                    </span>
                    <span className="text-muted-foreground">
                      {meta.readTime} {t.blog.readTime}
                    </span>
                  </div>
                  <h3 className="mt-4 text-base font-semibold leading-snug">{post.title}</h3>
                  <p className="mt-2.5 flex-1 text-sm leading-relaxed text-muted-foreground">{post.excerpt}</p>
                  <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                    {t.blog.readMore}
                    <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </span>
                </Link>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
