"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

export interface UserAvatarProps {
  src?: string | null;
  alt?: string;
  initials: string;
  sizeClassName?: string;
  textClassName?: string;
  gradientClassName?: string;
  className?: string;
}

export function UserAvatar({
  src,
  alt = "User Avatar",
  initials,
  sizeClassName = "size-8",
  textClassName = "text-xs",
  gradientClassName = "bg-gradient-to-br from-amber-600 to-orange-500 text-white",
  className,
}: UserAvatarProps) {
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    setImageError(false);
  }, [src]);

  if (src && !imageError) {
    return (
      /* eslint-disable-next-line @next/next/no-img-element */
      <img
        src={src}
        alt={alt}
        onError={() => setImageError(true)}
        className={cn(
          "shrink-0 rounded-full object-cover border border-border/40 shadow-xs",
          sizeClassName,
          className,
        )}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-full font-bold shadow-xs",
        sizeClassName,
        textClassName,
        gradientClassName,
        className,
      )}
    >
      {initials}
    </div>
  );
}
