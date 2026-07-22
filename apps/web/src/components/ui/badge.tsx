import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

type Tone = "default" | "success" | "warning" | "danger" | "muted";

const tones: Record<Tone, string> = {
  default: "bg-accent text-accent-foreground",
  success: "bg-[var(--color-success)]/15 text-[var(--color-success)]",
  warning: "bg-[var(--color-warning)]/15 text-[var(--color-warning)]",
  danger: "bg-[var(--color-danger)]/15 text-[var(--color-danger)]",
  muted: "bg-muted text-muted-foreground",
};

export function Badge({
  className,
  tone = "default",
  ...props
}: ComponentProps<"span"> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
