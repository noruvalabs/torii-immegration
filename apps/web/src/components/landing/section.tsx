import type { ReactNode } from "react";
import { Reveal } from "./reveal";
import { cn } from "@/lib/utils";

/**
 * The landing page's vertical rhythm and heading scale, in one place.
 *
 * Every section used to set its own container width, padding and heading size — one was
 * `max-w-6xl` with `text-4xl sm:text-5xl`, the next `max-w-7xl` with
 * `text-3xl sm:text-4xl lg:text-5xl`, a third was `font-black` where its neighbours were
 * `font-semibold`. None of it is wrong in isolation and all of it together is what makes a
 * page look assembled rather than designed. These two components are the whole scale.
 */

export function Section({
  id,
  children,
  className,
  size = "default",
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  /** `default` for a full section, `tight` for a band that only carries one idea. */
  size?: "default" | "tight";
}) {
  return (
    <section id={id} className={cn("relative", className)}>
      <div
        className={cn(
          "mx-auto max-w-6xl px-6 lg:px-8",
          size === "tight" ? "py-16 sm:py-20" : "py-20 sm:py-28",
        )}
      >
        {children}
      </div>
    </section>
  );
}

/** A small capsule above a section heading. Carries the section's one-line framing. */
export function Eyebrow({
  children,
  icon,
  className,
}: {
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/60 px-3 py-1 text-xs font-medium text-muted-foreground shadow-panel backdrop-blur-sm",
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  eyebrowIcon,
  title,
  body,
  align = "center",
  className,
}: {
  eyebrow?: ReactNode;
  eyebrowIcon?: ReactNode;
  title: ReactNode;
  body?: ReactNode;
  align?: "center" | "left";
  className?: string;
}) {
  const centered = align === "center";

  return (
    <div className={cn(centered && "mx-auto max-w-2xl text-center", !centered && "max-w-2xl", className)}>
      {eyebrow && (
        <Reveal>
          <Eyebrow icon={eyebrowIcon}>{eyebrow}</Eyebrow>
        </Reveal>
      )}
      <Reveal delay={eyebrow ? 60 : 0}>
        <h2
          className={cn(
            "text-display text-3xl font-semibold sm:text-4xl lg:text-[2.75rem] lg:leading-[1.1]",
            eyebrow && "mt-5",
          )}
        >
          {title}
        </h2>
      </Reveal>
      {body && (
        <Reveal delay={120}>
          <p
            className={cn(
              "mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg",
              centered && "mx-auto max-w-xl",
            )}
          >
            {body}
          </p>
        </Reveal>
      )}
    </div>
  );
}
