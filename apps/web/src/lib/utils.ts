import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, resolving Tailwind conflicts (last wins). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Shorten verbose scope labels for clean, concise, meaningful display.
 * E.g. "Japan · Work Visa - 技術・人文知識・国際業務 (Engineer / Specialist...) · New Visa"
 *   -> "Japan · Work Visa · New Visa"
 */
export function formatScopeLabel(label?: string | null): string {
  if (!label) return "";
  return label
    .split(" · ")
    .map((part) => {
      let cleaned = part.replace(/\s*\([^)]*\)/g, "").trim();
      if (cleaned.includes(" - ")) {
        cleaned = cleaned.split(" - ")[0].trim();
      }
      return cleaned;
    })
    .filter(Boolean)
    .join(" · ");
}
