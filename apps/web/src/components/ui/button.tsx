import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "outline" | "ghost";
type Size = "default" | "sm" | "lg" | "icon";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  outline: "border bg-transparent hover:bg-accent",
  ghost: "bg-transparent hover:bg-accent",
};

const sizes: Record<Size, string> = {
  default: "px-4 py-2 text-sm",
  sm: "px-2.5 py-1 text-xs",
  lg: "px-6 py-2.5 text-base",
  icon: "size-9 p-0",
};

export function Button({
  className,
  variant = "primary",
  size = "default",
  ...props
}: ComponentProps<"button"> & { variant?: Variant; size?: Size }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
