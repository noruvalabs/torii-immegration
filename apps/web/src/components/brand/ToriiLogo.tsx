import React from "react";
import { cn } from "@/lib/utils";

/**
 * Canonical Global Brand Assets
 * Single source of truth for all brand graphics across Torii.
 * To change the logo globally, simply replace the files in /public/brand/
 * or customize the SVG definitions below.
 */
export const BRAND_ASSETS = {
  iconPng: "/brand/logo-icon.png",
  logoDarkSvg: "/brand/logo.svg",
  logoLightSvg: "/brand/logo-light.svg",
  logoDarkPng: "/brand/logo.png",
  logoLightPng: "/brand/logo-light.png",
} as const;

export interface ToriiLogoProps {
  className?: string;
  size?: number | string;
  variant?: "image" | "vector" | "badge";
  withWordmark?: boolean;
  subtitle?: string;
  wordmarkClassName?: string;
}

/**
 * Global Torii Brand Logo
 * Reused across all navigation bars, sidebars, footers, auth cards, and admin screens.
 */
export function ToriiLogo({
  className,
  size = 26,
  variant = "image",
  withWordmark = false,
  subtitle,
  wordmarkClassName,
}: ToriiLogoProps) {
  const logoGraphic =
    variant === "image" ? (
      <img
        src={BRAND_ASSETS.iconPng}
        alt="Torii Logo"
        className={cn("shrink-0 object-contain drop-shadow-xs", className)}
        style={{ width: size, height: size }}
      />
    ) : variant === "badge" ? (
      <div
        className={cn(
          "relative flex items-center justify-center rounded-xl bg-[#111420] p-1.5 shadow-md border border-white/10 shrink-0",
          className,
        )}
        style={{ width: size, height: size }}
      >
        <ToriiLogoSvg className="size-full drop-shadow-sm" />
      </div>
    ) : (
      <ToriiLogoSvg className={cn("shrink-0", className)} style={{ width: size, height: size }} />
    );

  if (!withWordmark) {
    return logoGraphic;
  }

  return (
    <div className="flex items-center gap-2.5">
      {logoGraphic}
      <div className={cn("flex flex-col min-w-0 leading-none", wordmarkClassName)}>
        <span className="text-lg font-bold tracking-tight">Torii</span>
        {subtitle && (
          <span className="text-[10px] font-medium text-muted-foreground tracking-wider uppercase mt-0.5">
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Pure scalable Vector SVG representation of the Torii ribbon glyph.
 */
export function ToriiLogoSvg({ className, ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("size-6", className)}
      aria-label="Torii Logo"
      {...props}
    >
      <defs>
        <linearGradient id="g-kasagi" x1="10%" y1="0%" x2="90%" y2="100%">
          <stop offset="0%" stopColor="#FFA048" />
          <stop offset="35%" stopColor="#FF6B35" />
          <stop offset="70%" stopColor="#FF3823" />
          <stop offset="100%" stopColor="#D82510" />
        </linearGradient>

        <linearGradient id="g-ribbon" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#FFA048" />
          <stop offset="30%" stopColor="#FF5722" />
          <stop offset="60%" stopColor="#E11D48" />
          <stop offset="85%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#312E81" />
        </linearGradient>

        <linearGradient id="g-center" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#FFB366" />
          <stop offset="40%" stopColor="#FF4A2A" />
          <stop offset="75%" stopColor="#9333EA" />
          <stop offset="100%" stopColor="#4338CA" />
        </linearGradient>

        <linearGradient id="g-lintel" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#E11D48" />
          <stop offset="50%" stopColor="#FF4520" />
          <stop offset="100%" stopColor="#E11D48" />
        </linearGradient>

        <linearGradient id="g-foot" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#3730A3" />
          <stop offset="100%" stopColor="#1E1B4B" />
        </linearGradient>
      </defs>

      {/* Sub-lintel crossbar */}
      <rect x="20" y="37" width="60" height="6.5" rx="3.25" fill="url(#g-lintel)" />

      {/* Rear upright pillars */}
      <rect x="25" y="37" width="6.5" height="42" rx="3.25" fill="url(#g-foot)" opacity="0.55" />
      <rect x="68.5" y="37" width="6.5" height="42" rx="3.25" fill="url(#g-foot)" opacity="0.55" />

      {/* Left flowing ribbon pillar */}
      <path
        d="M32 40C32 37 36 34 42 34H47V56C47 62 43 65 38 68C33 71 27 75 27 82C27 88 33 91 38 88C43 85 45 79 45 74V48"
        stroke="url(#g-ribbon)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Right flowing ribbon pillar */}
      <path
        d="M68 40C68 37 64 34 58 34H53V56C53 62 57 65 62 68C67 71 73 75 73 82C73 88 67 91 62 88C57 85 55 79 55 74V48"
        stroke="url(#g-ribbon)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Center continuous "T" monogram connector */}
      <path
        d="M50 26V58C50 64 47 68 42 74"
        stroke="url(#g-center)"
        strokeWidth="7.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Top curved Kasagi roof beam */}
      <path
        d="M10 23C24 21 38 24 50 25C62 24 76 21 90 23C91 25 89.5 28 85 30C75 31.5 62 31 50 31.5C38 31 25 31.5 15 30C10.5 28 9 25 10 23Z"
        fill="url(#g-kasagi)"
      />
    </svg>
  );
}
