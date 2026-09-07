"use client";

import { useEffect, useState } from "react";

/**
 * Which of the given sections the reader is currently looking at.
 *
 * Used to light up the matching link in the header. An IntersectionObserver alone is
 * ambiguous here — on a tall viewport several sections are on screen at once — so the
 * winner is the section straddling the header line, which is the one the reader is
 * actually reading.
 *
 * `ids` is a dependency of the listener, so pass a stable array — a literal defined at
 * module scope, not one built inside the render.
 */
export function useActiveSection(ids: readonly string[]) {
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    let ticking = false;

    const measure = () => {
      // The line the header floats over; a section counts as current once it crosses it.
      const line = 120;
      let current: string | null = null;

      for (const id of ids) {
        const node = document.getElementById(id);
        if (!node) continue;
        const { top, bottom } = node.getBoundingClientRect();
        if (top <= line && bottom > line) {
          current = id;
          break;
        }
      }

      setActive(current);
      ticking = false;
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [ids]);

  return active;
}
