"use client";

import Link from "next/link";
import { ArrowRight, Landmark } from "lucide-react";
import { JP_ROUTE_ORDER, BLOG_POST_ORDER } from "./data";
import { BLOG_POSTS } from "./blog-posts";
import { useSectionNav } from "./nav";
import { useLang } from "./i18n";
import { dictionary } from "./dictionary";
import { Reveal } from "./reveal";
import { ToriiLogo } from "@/components/brand/ToriiLogo";
import { cn } from "@/lib/utils";

type FooterLink = { href: string; label: string };

type FooterGroup = {
  heading: string;
  links: FooterLink[];
  /**
   * Clamp labels to two lines. Blog headlines are written to be read in a list of three,
   * not in a footer column, and at full length they run to five lines and leave the
   * column visibly ragged next to its neighbours.
   */
  clamp?: boolean;
};

/**
 * The site footer.
 *
 * Every column is derived rather than typed out: the section anchors come from the shared
 * nav, the visa routes from the same `JP_ROUTE_ORDER` the coverage section renders, and the
 * reading list from the same `BLOG_POST_ORDER` that generates `/blog`. Adding a route or a
 * post puts it in the footer with no edit here — and, more to the point, removing one
 * cannot leave a dead link behind.
 *
 * Deliberately absent: privacy, terms, contact, careers. Those pages do not exist yet, and
 * a footer full of links to nothing is worse than a short honest one.
 */
export function SiteFooter() {
  const { lang } = useLang();
  const t = dictionary[lang];
  const sectionNav = useSectionNav();

  const groups: FooterGroup[] = [
    {
      heading: t.footer.groups.product,
      links: sectionNav.map((link) => ({ href: link.href, label: link.label })),
    },
    {
      // The routes the scope picker actually offers, named the way it names them.
      heading: t.footer.groups.routes,
      links: JP_ROUTE_ORDER.map((route) => ({
        href: "#coverage",
        label: t.coverage.routes[route.id].name,
      })),
    },
    {
      heading: t.footer.groups.resources,
      clamp: true,
      links: [
        ...BLOG_POST_ORDER.map((post) => ({
          href: `/blog/${post.slug}`,
          label: BLOG_POSTS[post.slug][lang].title,
        })),
        { href: "/blog", label: t.blog.viewAll },
      ],
    },
  ];

  return (
    <footer
      // pb-24 on a phone clears the sticky call to action, which would otherwise sit on
      // top of the last row of footer links.
      className="relative overflow-hidden rounded-t-[2.5rem] border-t border-border/60 bg-muted/40 pb-24 sm:rounded-t-[3.5rem] sm:pb-0"
    >
      <div
        aria-hidden
        className="animate-blob-drift-slow pointer-events-none absolute -top-32 left-1/2 size-112 -translate-x-1/2 rounded-full bg-primary/10 blur-[110px]"
      />

      <div className="relative mx-auto max-w-6xl px-6 pb-10 pt-16 sm:pt-20 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
          <Reveal>
            <div className="flex items-center gap-3">
              <ToriiLogo size={34} />
              <span className="text-xl font-semibold tracking-tight">Torii</span>
            </div>

            <h2 className="text-display mt-6 max-w-sm text-3xl font-semibold leading-[1.08] sm:text-4xl">
              {t.footer.title}
            </h2>

            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              {t.footer.tagline}
            </p>

            <Link
              href="/scope"
              className="group mt-7 inline-flex h-12 items-center gap-2 rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground transition-all duration-200 hover:bg-primary/90 active:scale-[0.98]"
            >
              {t.footer.cta}
              <ArrowRight className="size-4 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Link>

            <p className="mt-5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
              <Link href="/login" className="transition-colors hover:text-foreground">
                {t.nav.signIn}
              </Link>
              <span aria-hidden className="text-muted-foreground/50">·</span>
              <Link href="/register" className="transition-colors hover:text-foreground">
                {t.footer.createAccount}
              </Link>
            </p>
          </Reveal>

          <Reveal delay={120} className="grid grid-cols-2 gap-x-8 gap-y-10 sm:grid-cols-3">
            {groups.map((group) => (
              <nav key={group.heading} aria-label={group.heading}>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.heading}
                </p>
                <ul className="mt-4 space-y-3 text-sm">
                  {group.links.map((link) => {
                    const linkClass = cn(
                      "block leading-snug text-muted-foreground transition-colors hover:text-foreground",
                      group.clamp && "line-clamp-2",
                    );
                    return (
                      <li key={`${group.heading}-${link.href}-${link.label}`}>
                        {/* On-page anchors stay plain anchors; Link would treat them as
                            route pushes. */}
                        {link.href.startsWith("#") ? (
                          <a href={link.href} className={linkClass}>
                            {link.label}
                          </a>
                        ) : (
                          <Link href={link.href} className={linkClass} title={link.label}>
                            {link.label}
                          </Link>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ))}
          </Reveal>
        </div>

        {/* Where the requirements come from, restated at the bottom of the page. It is the
            claim the whole product rests on, and the footer is where a sceptical reader
            goes looking for it. */}
        <div className="mt-14 border-t border-border/60 pt-8">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t.outcomes.sourcesLabel}
          </p>
          <ul className="mt-4 flex flex-wrap gap-x-8 gap-y-2">
            {t.outcomes.sources.map((source) => (
              <li key={source} className="flex items-center gap-2 text-sm text-foreground/70">
                <Landmark className="size-3.5 shrink-0 text-primary/70" />
                {source}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-border/60 pt-8 sm:flex-row sm:items-start sm:justify-between">
          <p className="shrink-0 text-xs text-muted-foreground">© {new Date().getFullYear()} Torii</p>
          <p className="max-w-lg text-xs leading-relaxed text-muted-foreground">{t.footer.disclaimer}</p>
        </div>
      </div>
    </footer>
  );
}
