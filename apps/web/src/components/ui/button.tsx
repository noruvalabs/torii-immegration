import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "outline" | "ghost";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:opacity-90",
  outline: "border bg-transparent hover:bg-accent",
  ghost: "bg-transparent hover:bg-accent",
};

export function Button({
  className,
  variant = "primary",
  ...props
}: ComponentProps<"button"> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius)] px-4 py-2 text-sm font-medium",
        "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
