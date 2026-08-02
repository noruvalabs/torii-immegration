"use client";

import { useEffect, useRef, useState } from "react";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { IntakeState, User } from "./types";

type IntakeStepProps = {
  state: IntakeState;
  profile: User | null;
  onAnswer: (key: string, value: unknown) => void;
};

export function IntakeStep({ state, profile, onAnswer }: IntakeStepProps) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;
  const autoSubmittedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!profile) return;
    const profileMap: Record<string, string | null> = {
      full_name: profile.full_name,
      nationality: profile.nationality,
      passport_number: profile.passport_number,
      passport_expiry: profile.passport_expiry,
    };
    const toAutoFill: Record<string, unknown> = {};
    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined || autoSubmittedRef.current.has(q.key)) continue;
      const val = profileMap[q.key];
      if (val) toAutoFill[q.key] = val;
    }
    if (Object.keys(toAutoFill).length > 0) {
      setDrafts((prev) => ({ ...prev, ...toAutoFill }));
      for (const [key, val] of Object.entries(toAutoFill)) {
        if (val !== undefined) {
          autoSubmittedRef.current.add(key);
          onAnswerRef.current(key, val);
        }
      }
    }
  }, [profile, state.questions, state.answers]);

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(key: string) {
    if (drafts[key] !== undefined) {
      const raw = drafts[key];
      const q = state.questions.find((item) => item.key === key);
      if (q?.type === "integer" && typeof raw === "string") {
        onAnswer(key, Number.parseInt(raw, 10));
      } else {
        onAnswer(key, raw);
      }
    }
  }

  const pct = state.progress.total > 0
    ? Math.round((state.progress.answered / state.progress.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-muted-foreground">Intake questionnaire</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          {state.progress.answered} of {state.progress.total} questions answered ({pct}%)
          {state.progress.complete ? " · Complete — continue to eligibility" : ""}
        </p>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {state.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No questions available for this scope.</p>
      ) : (
        <div className="space-y-4">
          {state.questions.map((q) => {
            const current = (state.answers[q.key] ?? drafts[q.key]) as string | number | boolean | undefined;
            return (
              <div key={q.key} className="space-y-1.5">
                <label className="text-sm font-medium">
                  {q.prompt}
                  {q.required !== false && <span className="ml-1 text-[var(--color-danger)]">*</span>}
                </label>
                {q.type === "enum" && q.options ? (
                  <div className="flex flex-wrap gap-2">
                    {q.options.map((opt) => (
                      <button
                        key={opt}
                        onClick={() => onAnswer(q.key, opt)}
                        className={`rounded-[var(--radius)] border px-3 py-2 text-sm transition-colors ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {opt.replaceAll("_", " ")}
                      </button>
                    ))}
                  </div>
                ) : q.type === "boolean" ? (
                  <div className="flex gap-2">
                    {[true, false].map((v) => (
                      <button
                        key={String(v)}
                        onClick={() => onAnswer(q.key, v)}
                        className={`rounded-[var(--radius)] border px-4 py-2 text-sm transition-colors ${
                          current === v
                            ? "border-primary bg-primary/10 text-primary"
                            : "hover:bg-accent"
                        }`}
                      >
                        {v ? "Yes" : "No"}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type={q.type === "integer" ? "number" : "text"}
                      value={String(current ?? "")}
                      onChange={(e) => handleChange(q.key, e.target.value)}
                      className="h-9 flex-1 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                    <Button onClick={() => handleSubmit(q.key)}>Save</Button>
                  </div>
                )}
                {state.answers[q.key] !== undefined && (
                  <p className="text-xs text-[var(--color-success)]">
                    <Check className="mr-1 inline size-3" />
                    Saved
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
