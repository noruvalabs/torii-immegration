"use client";

import { FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GeneratedForm } from "./types";

type FormsStepProps = {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
  intakeAnswers?: Record<string, unknown>;
};

export function FormsStep({ forms, loading, onGenerate, intakeAnswers }: FormsStepProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Generated forms</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Government forms auto-filled from your intake data.
          </p>
        </div>
        <Button onClick={onGenerate} disabled={loading}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
          Generate forms
        </Button>
      </div>

      {forms.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No forms generated yet. Complete intake, then click generate. Stay on this step until you choose Continue.
        </p>
      ) : (
        <div className="space-y-4">
          {forms.map((form) => {
            const hasFilledFields = Object.keys(form.filled_fields).length > 0;
            const displayFields = hasFilledFields
              ? form.filled_fields
              : intakeAnswers && Object.keys(intakeAnswers).length > 0
                ? intakeAnswers
                : form.filled_fields;

            return (
              <div key={form.id} className="rounded-[var(--radius)] border p-4">
                <div className="flex items-center gap-2">
                  <FileText className="size-4 text-muted-foreground" />
                  <p className="font-mono text-sm font-semibold">{form.form_code}</p>
                  <Badge tone="muted">v{form.form_version}</Badge>
                  {form.missing_required_fields.length > 0 && (
                    <Badge tone="danger">
                      {form.missing_required_fields.length} missing fields
                    </Badge>
                  )}
                  {!hasFilledFields && Object.keys(intakeAnswers || {}).length > 0 && (
                    <Badge tone="default">intake data</Badge>
                  )}
                </div>
                {Boolean(form.citation?.authority) && (
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    Source: {String(form.citation.authority)}
                    {form.citation.title ? ` — ${String(form.citation.title)}` : ""}
                  </p>
                )}
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {Object.entries(displayFields).map(([key, val]) => (
                    <div key={key} className="text-xs">
                      <span className="text-muted-foreground">{key.replace(/_/g, " ")}: </span>
                      <span className="font-medium">{String(val)}</span>
                    </div>
                  ))}
                </div>
                {form.missing_required_fields.length > 0 && (
                  <div className="mt-3 rounded border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-3 py-2">
                    <p className="text-[11px] font-medium text-[var(--color-warning)]">
                      Missing required: {form.missing_required_fields.join(", ")}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
