"use client";

import { CalendarClock, ExternalLink, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { CaseDeadlines } from "./types";

// Format an ISO-8601 date (YYYY-MM-DD) for display in the applicant's locale.
// Trailing "Z" pins it to UTC so it never shifts a day due to local timezones.
function fmt(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-JP", { year: "numeric", month: "short", day: "numeric" });
}

type DeadlineRow = {
  label: string;
  value: string | null;
  highlight?: "urgent" | "warning" | "ok";
};

export function DeadlinesCard({ deadlines }: { deadlines: CaseDeadlines | null }) {
  // Nothing meaningful to show until the residence-card expiry is known.
  if (!deadlines || !deadlines.residence_expiry) return null;

  const rows: DeadlineRow[] = [
    {
      label: "Filing window opens",
      value: fmt(deadlines.filing_window_opens),
      highlight: "ok",
    },
    {
      label: "Online filing cut-off",
      value: fmt(deadlines.online_cutoff),
      highlight: "urgent",
    },
    ...(deadlines.has_grace_period
      ? [
          {
            label: "Grace period ends",
            value: fmt(deadlines.grace_period_end),
            highlight: "warning" as const,
          },
        ]
      : []),
    {
      label: "Residence card expiry",
      value: fmt(deadlines.residence_expiry),
      highlight: "warning" as const,
    },
    {
      label: "My Number card expiry",
      value: fmt(deadlines.my_number_expiry),
    },
  ];

  return (
    <Card className="bg-muted/30">
      <CardContent className="pt-5">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CalendarClock className="size-4 text-primary" />
            <h3 className="text-sm font-semibold">Filing deadlines</h3>
          </div>
          <Badge tone={deadlines.has_grace_period ? "warning" : "default"}>
            {deadlines.has_grace_period ? "Grace period applies" : "No grace period"}
          </Badge>
        </div>
        <dl className="space-y-2 text-sm">
          {rows.map((row) => (
            <div key={row.label} className="flex items-center justify-between gap-3">
              <dt className="text-muted-foreground">{row.label}</dt>
              <dd className="text-right font-medium">
                {row.value ?? "—"}
              </dd>
            </div>
          ))}
        </dl>
        {deadlines.has_grace_period && (
          <p className="mt-3 flex items-start gap-2 rounded-[var(--radius)] bg-[var(--color-warning)]/10 px-3 py-2 text-xs text-muted-foreground">
            <ShieldAlert className="mt-0.5 size-3.5 shrink-0 text-[var(--color-warning)]" />
            <span>
              Filing on or before the expiry date lets you remain lawfully in Japan while the
              application is pending. File well before the online cut-off — the online system
              stops accepting filings close to the expiry date.
            </span>
          </p>
        )}
        {!deadlines.has_grace_period && (
          <p className="mt-3 flex items-start gap-2 rounded-[var(--radius)] bg-[var(--color-warning)]/10 px-3 py-2 text-xs text-muted-foreground">
            <ShieldAlert className="mt-0.5 size-3.5 shrink-0 text-[var(--color-warning)]" />
            <span>
              This procedure does not qualify for the grace period. Do not remain in Japan
              past the residence-card expiry while the application is pending.
            </span>
          </p>
        )}
        <p className="mt-3 flex items-center gap-1 text-xs text-muted-foreground">
          <ExternalLink className="size-3" />
          Deadlines are computed from your residence card expiry and may vary by regional
          bureau business calendar.
        </p>
      </CardContent>
    </Card>
  );
}
