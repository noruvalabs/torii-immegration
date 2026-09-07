"use client";

import { useEffect, useRef, useState, type ElementType, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Direction = "up" | "left" | "right" | "scale" | "fade";

const DIRECTION_CLASS: Record<Direction, string> = {
  up: "",
  left: "reveal-left",
  right: "reveal-right",
  scale: "reveal-scale",
  fade: "reveal-fade",
};

type Props = {
  children: ReactNode;
  className?: string;
  /** Milliseconds to hold the reveal back, for staggering a row or grid. */
  delay?: number;
  /**
   * Which way the element travels in from. `up` is the page default; `fade` moves not at
   * all, which is what a row of peer cards wants — staggering a *transform* across a row
   * leaves the cards at different heights for the length of the animation, so a row that
   * is aligned when it settles looks broken on the way in.
   */
  direction?: Direction;
  /** Adds a short defocus to the entrance. Reserve it for large surfaces. */
  blur?: boolean;
  /** Renders as something other than a div, so a reveal can also be the semantic element. */
  as?: ElementType;
};

/**
 * Reveals its children once they scroll into view.
 *
 * The transition itself lives in `globals.css` so every reveal on the page shares one
 * duration and one curve — a page where each section eases differently reads as unfinished
 * however good the individual animations are. This component only decides *when*.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  direction = "up",
  blur = false,
  as: Tag = "div",
}: Props) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      // Fires a little before the element is fully in frame, so the motion is finishing
      // as the reader arrives rather than starting under their eyes.
      { threshold: 0.1, rootMargin: "0px 0px -12% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
      className={cn(
        "reveal",
        DIRECTION_CLASS[direction],
        blur && "reveal-blur",
        visible && "reveal-visible",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
