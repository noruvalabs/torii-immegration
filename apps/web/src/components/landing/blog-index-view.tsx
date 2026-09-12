"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ArrowLeft, BookOpen, Clock, Sparkles } from "lucide-react";
import { BLOG_POST_ORDER } from "./data";
import { BLOG_POSTS } from "./blog-posts";
import { Reveal } from "./reveal";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { StartCaseButton } from "./start-case-button";
import { cn } from "@/lib/utils";

export function BlogIndexView() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const categories = [
    { id: "all", label: lang === "ja" ? "すべての記事" : "All Articles" },
    ...Array.from(
      new Map(
        BLOG_POST_ORDER.map((p) => [
          p.category.en.toLowerCase(),
          p.category[lang],
        ]),
      ).entries(),
    ).map(([id, label]) => ({ id, label })),
  ];

  const filteredPosts =
    activeCategory === "all"
      ? BLOG_POST_ORDER
      : BLOG_POST_ORDER.filter(
          (p) => p.category.en.toLowerCase() === activeCategory,
        );

  const [featuredPost, ...regularPosts] = filteredPosts;

  return (
    <div className="relative overflow-hidden pt-28 pb-20 sm:pt-32 sm:pb-28">
      {/* Background glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 -z-10 size-144 -translate-x-1/2 rounded-full bg-primary/8 blur-[130px]"
      />

      <div className="mx-auto max-w-4xl px-6 sm:px-8">
        {/* Breadcrumb */}
        <Reveal>
          <div className="flex items-center justify-between border-b border-border/60 pb-5">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
              {lang === "ja" ? "ホームに戻る" : "Back to Home"}
            </Link>

            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              <BookOpen className="size-3.5" />
              {t.blog.eyebrow}
            </span>
          </div>
        </Reveal>

        {/* Hero */}
        <Reveal delay={80} className="mt-8">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-5xl">
            {t.blog.title}
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
            {t.blog.body}
          </p>
        </Reveal>

        {/* Category Tabs */}
        <Reveal delay={120} className="mt-8">
          <div className="flex flex-wrap gap-2 border-b border-border/60 pb-4">
            {categories.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setActiveCategory(cat.id)}
                className={cn(
                  "rounded-full px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer",
                  activeCategory === cat.id
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </Reveal>

        {/* Featured Post Card (if available) */}
        {featuredPost && (
          <Reveal delay={160} className="mt-8">
            {(() => {
              const post = BLOG_POSTS[featuredPost.slug][lang];
              return (
                <Link
                  href={`/blog/${featuredPost.slug}`}
                  className="group relative block rounded-3xl border border-primary/30 bg-gradient-to-br from-card via-card to-primary/5 p-7 sm:p-9 shadow-panel transition-all hover:border-primary/60 hover:shadow-panel-lg"
                >
                  <div className="flex items-center gap-3 text-xs">
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-3 py-1 font-semibold text-primary">
                      <Sparkles className="size-3" />
                      {lang === "ja" ? "おすすめ記事" : "Featured Article"}
                    </span>
                    <span className="rounded-full bg-muted px-2.5 py-1 font-medium text-muted-foreground">
                      {featuredPost.category[lang]}
                    </span>
                    <span className="flex items-center gap-1 text-muted-foreground">
                      <Clock className="size-3" />
                      {featuredPost.readTime} {t.blog.readTime}
                    </span>
                  </div>

                  <h2 className="mt-5 flex items-center justify-between text-2xl font-bold tracking-tight text-foreground group-hover:text-primary transition-colors sm:text-3xl">
                    <span>{post.title}</span>
                    <ArrowUpRight className="size-6 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:text-primary" />
                  </h2>

                  <p className="mt-3 text-base leading-relaxed text-muted-foreground">
                    {post.excerpt}
                  </p>
                </Link>
              );
            })()}
          </Reveal>
        )}

        {/* Regular Posts List */}
        {regularPosts.length > 0 && (
          <div className="mt-8 divide-y divide-border/60 border-t border-border/60">
            {regularPosts.map((meta, i) => {
              const post = BLOG_POSTS[meta.slug][lang];
              return (
                <Reveal key={meta.slug} delay={i * 80}>
                  <Link
                    href={`/blog/${meta.slug}`}
                    className="group flex flex-col gap-2.5 py-7 transition-colors"
                  >
                    <div className="flex items-center gap-3 text-xs">
                      <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                        {meta.category[lang]}
                      </span>
                      <span className="text-muted-foreground">
                        {meta.readTime} {t.blog.readTime}
                      </span>
                    </div>

                    <h3 className="flex items-center gap-2 text-xl font-semibold tracking-tight transition-colors group-hover:text-primary">
                      {post.title}
                      <ArrowUpRight className="size-4 shrink-0 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </h3>

                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {post.excerpt}
                    </p>
                  </Link>
                </Reveal>
              );
            })}
          </div>
        )}

        {/* Newsletter / Eligibility Check CTA Banner */}
        <Reveal delay={240} className="mt-16 sm:mt-20">
          <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border border-border/70 bg-card p-8 text-center sm:flex-row sm:text-left sm:p-10 shadow-panel">
            <div>
              <h3 className="text-xl font-bold tracking-tight text-foreground">
                {lang === "ja" ? "ビザ申請の準備をはじめましょう" : "Start your Japan visa filing with Torii"}
              </h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {lang === "ja"
                  ? "公表されている公的基準に基づき、あなたの申請要件と必要書類を2分で自動判定。"
                  : "Check your requirements and statutory document checklist in 2 minutes. Free passes included."}
              </p>
            </div>
            <div className="shrink-0">
              <StartCaseButton
                size="default"
                signedOutLabel={t.nav.headerCta}
                className="h-11 px-5"
              />
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}
