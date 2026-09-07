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
  glyphTransparent: "/brand/torii-logo-glyph-transparent.png",
  glyphLightTransparent: "/brand/torii-logo-transparent-light.png",
  logoDarkSvg: "/brand/logo.svg",
  logoLightSvg: "/brand/logo-light.svg",
  logoDarkPng: "/brand/logo.png",
  logoLightPng: "/brand/logo-light.png",
} as const;

export interface ToriiLogoProps {
  className?: string;
  size?: number | string;
  height?: number | string;
  width?: number | string;
  style?: React.CSSProperties;
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
  size = 36,
  height,
  width,
  style,
  variant = "image",
  withWordmark = false,
  subtitle,
  wordmarkClassName,
}: ToriiLogoProps) {
  const h = height ?? size;
  const dimensionStyle: React.CSSProperties = {
    height: typeof h === "number" ? `${h}px` : h,
    width: width ? (typeof width === "number" ? `${width}px` : width) : "auto",
    aspectRatio: "1415 / 933",
    ...style,
  };

  const logoGraphic =
    variant === "image" ? (
      <>
        {/* Light theme: Deep navy mark */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={BRAND_ASSETS.glyphTransparent}
          alt="Torii Logo"
          className={cn("shrink-0 object-contain drop-shadow-xs dark:hidden transition-all", className)}
          style={dimensionStyle}
        />
        {/* Dark theme: Clean white mark */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={BRAND_ASSETS.glyphLightTransparent}
          alt="Torii Logo"
          className={cn("shrink-0 object-contain drop-shadow-xs hidden dark:block transition-all", className)}
          style={dimensionStyle}
        />
      </>
    ) : variant === "badge" ? (
      <div
        className={cn(
          "relative flex items-center justify-center rounded-xl bg-slate-900 p-2 shadow-md border border-white/10 shrink-0",
          className,
        )}
        style={{ width: dimensionStyle.height, height: dimensionStyle.height }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={BRAND_ASSETS.glyphLightTransparent}
          alt="Torii Logo"
          className="size-full object-contain drop-shadow-sm"
        />
      </div>
    ) : (
      <ToriiLogoSvg className={className} size={h} style={style} />
    );

  if (!withWordmark) {
    return logoGraphic;
  }

  return (
    <div className="flex items-center gap-3">
      {logoGraphic}
      <div className={cn("flex flex-col min-w-0 leading-none", wordmarkClassName)}>
        <span className="text-xl font-bold tracking-tight">Torii</span>
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
 * Scalable Vector/SVG representation of the Torii mark.
 */
export function ToriiLogoSvg({
  className,
  size = 36,
  style,
  ...props
}: React.SVGProps<SVGSVGElement> & { size?: number | string }) {
  const h = typeof size === "number" ? `${size}px` : size;
  return (
    <svg
      viewBox="0 0 1415 933"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0 object-contain", className)}
      style={{ height: h, width: "auto", aspectRatio: "1415 / 933", ...style }}
      aria-label="Torii Logo"
      {...props}
    >
      <image width="1415" height="933" href={BRAND_ASSETS.glyphTransparent} className="dark:hidden" />
      <image width="1415" height="933" href={BRAND_ASSETS.glyphLightTransparent} className="hidden dark:block" />
    </svg>
  );
}
