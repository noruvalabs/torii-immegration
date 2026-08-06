"use client";

import { FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { GeneratedForm } from "./types";

type FormsStepProps = {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
};

export function FormsStep({ forms, loading, onGenerate }: FormsStepProps) {
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
          {forms.map((form) => (
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
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {Object.entries(form.filled_fields).map(([key, val]) => (
                  <div key={key} className="text-xs">
                    <span className="text-muted-foreground">{key}: </span>
                    <span className="font-medium">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
