"use client";

import { Check, Download, Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Case } from "./types";

type PacketStepProps = {
  packet: Record<string, unknown> | null;
  caseData: Case;
  loading: boolean;
  onBuild: () => void;
  onSubmit: () => void;
};

function packetSummaryText(source: Record<string, unknown>, caseData: Case): string {
  const forms = Array.isArray(source.forms)
    ? (source.forms as { form_code?: string; form_version?: string }[])
    : [];
  const checklist = Array.isArray(source.checklist)
    ? (source.checklist as { name?: string; status?: string; is_required?: boolean }[])
    : [];
  const requiredTotal = checklist.filter((i) => i.is_required).length;
  const requiredDone = checklist.filter(
    (i) => i.is_required && i.status && i.status !== "needed",
  ).length;
  const lines = [
    "Torii Application Packet Summary",
    `Reference: ${String(source.reference ?? caseData.reference)}`,
    `Scope: ${caseData.scope_label ?? caseData.locale.toUpperCase()}`,
    `Generated at: ${new Date().toISOString()}`,
    "",
    "Forms",
    forms.length === 0
      ? "- No generated forms listed in this packet."
      : forms
        .map((form) => `- ${String(form.form_code ?? "form")} (v${String(form.form_version ?? "n/a")})`)
        .join("\n"),
    "",
    "Checklist",
    `- Required gathered: ${requiredDone}/${requiredTotal}`,
    ...checklist.map(
      (item) => `- ${String(item.name ?? "Document")}: ${String(item.status ?? "needed")}`,
    ),
    "",
    "Submission",
    "- This jurisdiction may require mail/in-person submission if e-file is unavailable.",
  ];
  return lines.join("\n");
}

export function PacketStep({ packet, caseData, loading, onBuild, onSubmit }: PacketStepProps) {
  function downloadPacket() {
    if (!packet) return;
    const filename = `${caseData.reference}-packet-summary.txt`;
    const blob = new Blob([packetSummaryText(packet, caseData)], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Submission packet</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Your assembled forms and checklist, ready for submission.
        </p>
      </div>

      {!packet ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Download className="mb-3 size-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">Packet not yet assembled.</p>
          <Button onClick={onBuild} disabled={loading} className="mt-4">
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
            Build packet
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
            <div className="flex items-center gap-2">
              <Check className="size-4 text-[var(--color-success)]" />
              <p className="text-sm font-medium">Packet assembled</p>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Reference: {String(packet.reference ?? caseData.reference)}
            </p>
          </div>

          <Button variant="outline" onClick={downloadPacket}>
            <Download className="size-4" />
            Download summary
          </Button>

          {caseData.status !== "submitted" && (
            <Button onClick={onSubmit} disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Submit application
            </Button>
          )}

          {caseData.status === "submitted" && (
            <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/5 p-4">
              <p className="text-sm font-medium">Submitted</p>
              {caseData.submission_reference && (
                <p className="mt-1 font-mono text-xs">{caseData.submission_reference}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
