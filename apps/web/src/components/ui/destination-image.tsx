"use client";

import { useState } from "react";
import Image from "next/image";

type DestinationImageProps = {
  src: string;
  alt: string;
  className?: string;
  sizes?: string;
  priority?: boolean;
};

/**
 * Destination hero photo with a graceful fallback.
 *
 * Destination cards and visa detail pages reference local photos in
 * `public/destinations/`. If one of those files is ever missing, Next/Image
 * renders an empty (gray) box — instead, swap in a branded gradient panel so
 * the layout still looks intentional while the missing asset is restored.
 */
export function DestinationImage({ src, alt, className, sizes, priority }: DestinationImageProps) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        role="img"
        aria-label={alt}
        className="absolute inset-0 bg-gradient-to-br from-slate-700 via-slate-900 to-black"
      />
    );
  }

  return (
    <Image
      src={src}
      alt={alt}
      fill
      sizes={sizes}
      priority={priority}
      className={className}
      onError={() => setFailed(true)}
    />
  );
}
