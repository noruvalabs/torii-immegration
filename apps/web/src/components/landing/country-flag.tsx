"use client";

import { cn } from "@/lib/utils";

export function CountryFlag({ code, className }: { code: string; className?: string }) {
  const c = code.toUpperCase();

  switch (c) {
    case "BD":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#006A4E" />
          <circle cx="14" cy="16" r="7.5" fill="#F42A41" />
        </svg>
      );
    case "JP":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full border border-black/10 overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#FFFFFF" />
          <circle cx="16" cy="16" r="7.5" fill="#BC002D" />
        </svg>
      );
    case "IN":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect y="0" width="32" height="10.6" fill="#FF9933" />
          <rect y="10.6" width="32" height="10.6" fill="#FFFFFF" />
          <rect y="21.2" width="32" height="10.8" fill="#138808" />
          <circle cx="16" cy="16" r="3.2" fill="#000080" />
        </svg>
      );
    case "SA":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#006C35" />
          <rect x="8" y="19" width="16" height="2" fill="#FFFFFF" rx="1" />
          <path d="M10 13h12v4H10z" fill="#FFFFFF" opacity="0.9" />
        </svg>
      );
    case "US":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#B22234" />
          <rect y="5" width="32" height="4.5" fill="#FFFFFF" />
          <rect y="14" width="32" height="4.5" fill="#FFFFFF" />
          <rect y="23" width="32" height="4.5" fill="#FFFFFF" />
          <rect width="14" height="16" fill="#3C3B6E" />
          <circle cx="5" cy="5" r="1.2" fill="#FFFFFF" />
          <circle cx="9" cy="5" r="1.2" fill="#FFFFFF" />
          <circle cx="7" cy="9" r="1.2" fill="#FFFFFF" />
          <circle cx="5" cy="13" r="1.2" fill="#FFFFFF" />
          <circle cx="9" cy="13" r="1.2" fill="#FFFFFF" />
        </svg>
      );
    case "CA":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect width="8" height="32" fill="#D80027" />
          <rect x="8" width="16" height="32" fill="#FFFFFF" />
          <rect x="24" width="8" height="32" fill="#D80027" />
          <path d="M16 8l1.5 4 4-1.5-2 3.5 3.5 2-4 1 1 5-4-3-4 3 1-5-4-1 3.5-2-2-3.5 4 1.5z" fill="#D80027" />
        </svg>
      );
    case "FR":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect x="0" width="10.6" height="32" fill="#0055A4" />
          <rect x="10.6" width="10.6" height="32" fill="#FFFFFF" />
          <rect x="21.2" width="10.8" height="32" fill="#EF4135" />
        </svg>
      );
    case "ES":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect y="0" width="32" height="8" fill="#AA151B" />
          <rect y="8" width="32" height="16" fill="#F1BF00" />
          <rect y="24" width="32" height="8" fill="#AA151B" />
          <circle cx="10" cy="16" r="3" fill="#AA151B" />
        </svg>
      );
    case "DE":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect y="0" width="32" height="10.6" fill="#000000" />
          <rect y="10.6" width="32" height="10.6" fill="#DD0000" />
          <rect y="21.2" width="32" height="10.8" fill="#FFCE00" />
        </svg>
      );
    case "KR":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full border border-black/10 overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#FFFFFF" />
          <circle cx="16" cy="16" r="7" fill="#CD2E3A" />
          <path d="M16 9a7 7 0 0 0 0 14c2.5 0 3.5-2 3.5-3.5S18.5 16 16 16s-3.5-2-3.5-3.5S13.5 9 16 9z" fill="#0047A0" />
        </svg>
      );
    case "GB":
      return (
        <svg viewBox="0 0 32 32" className={cn("size-5 shrink-0 rounded-full overflow-hidden shadow-xs", className)}>
          <rect width="32" height="32" fill="#012169" />
          <path d="M0 0l32 32M32 0L0 32" stroke="#FFFFFF" strokeWidth="4" />
          <path d="M0 0l32 32M32 0L0 32" stroke="#C8102E" strokeWidth="2" />
          <path d="M16 0v32M0 16h32" stroke="#FFFFFF" strokeWidth="6" />
          <path d="M16 0v32M0 16h32" stroke="#C8102E" strokeWidth="3.5" />
        </svg>
      );
    default:
      return (
        <div className={cn("size-5 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold text-primary", className)}>
          {c.slice(0, 2)}
        </div>
      );
  }
}
