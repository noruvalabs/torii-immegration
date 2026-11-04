"use client";

import { useState } from "react";
import {
  Bot,
  CheckCircle2,
  Clock,
  CreditCard,
  FileCheck2,
  Globe2,
  Loader2,
  ShieldCheck,
  Terminal,
  Upload,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PortalJob } from "@/lib/api/portal-bot";

type PortalBotConsoleProps = {
  isOpen: boolean;
  onClose: () => void;
  job: PortalJob | null;
  loading: boolean;
};

const STEP_ICONS: Record<string, typeof Bot> = {
  queued: Clock,
  connecting_proxy: Globe2,
  navigating: Bot,
  filling_form: Terminal,
  solving_captcha: ShieldCheck,
  uploading_docs: Upload,
  submitting_payment: CreditCard,
  succeeded: FileCheck2,
};

export function PortalBotConsole({
  isOpen,
  onClose,
  job,
  loading,
}: PortalBotConsoleProps) {
  if (!isOpen) return null;

  const isCompleted = job?.status === "succeeded" && Boolean(job.portal_reference);
  const isFailed = job?.status === "failed";
  const needsHuman = job?.status === "manual_takeover";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-950 text-slate-100 w-full max-w-2xl rounded-2xl border border-slate-800 shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
        {/* Terminal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
              <Bot className="size-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold tracking-tight text-white">
                  Vietnam eVisa worker (evisa.gov.vn)
                </h3>
                <Badge
                  tone={
                    isCompleted ? "success" : isFailed || needsHuman ? "warning" : "info"
                  }
                  className="text-[10px] px-2 py-0 uppercase tracking-wider"
                >
                  {isCompleted
                    ? "Confirmation captured"
                    : isFailed
                      ? "Failed"
                      : needsHuman
                        ? "Needs a person"
                        : "Running"}
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {job?.portal_name || "https://evisa.gov.vn"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Console Body */}
        <div className="p-6 space-y-5 max-h-[65vh] overflow-y-auto">
          {/* Target Portal Card */}
          <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between text-xs">
            <div className="space-y-0.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Target Government Portal
              </span>
              <p className="font-mono text-emerald-400">{job?.portal_url}</p>
            </div>
            {job?.jurisdiction_code && (
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  Corridor
                </span>
                <p className="font-mono text-slate-300">{job.jurisdiction_code}</p>
              </div>
            )}
          </div>

          {/* Succeeded Banner */}
          {isCompleted && job?.portal_reference && (
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-5 text-emerald-400 shrink-0" />
                <span className="text-sm font-bold text-white">
                  Portal registration code captured from evisa.gov.vn
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-black/40 border border-emerald-500/20 flex items-center justify-between">
                <span className="text-xs text-slate-400">Government Reference:</span>
                <span className="font-mono text-base font-bold text-emerald-400 tracking-wider">
                  {job.portal_reference}
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                This code was read from the official page. It is not generated by Torii.
              </p>
            </div>
          )}

          {needsHuman && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-100 space-y-1">
              <p className="text-sm font-bold text-white">Human finish required</p>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                {job?.error_message === "portal_challenge"
                  ? "The Vietnam portal showed a captcha or bot-check. Torii does not solve those."
                  : "Matching fields were filled where the page labels were found. Captcha and the government card payment still need a person on evisa.gov.vn."}
              </p>
            </div>
          )}

          {/* Live Execution Steps Log */}
          <div className="space-y-2">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
              <Terminal className="size-3 text-slate-400" />
              Worker log
            </span>
            <div className="space-y-2">
              {job?.steps_log && job.steps_log.length > 0 ? (
                job.steps_log.map((step, idx) => {
                  const Icon = STEP_ICONS[step.step] || Bot;
                  const isLast = idx === (job.steps_log.length ?? 0) - 1;
                  return (
                    <div
                      key={step.timestamp + idx}
                      className={`p-3 rounded-xl border text-xs flex items-start gap-3 transition-all ${
                        isLast && !isCompleted
                          ? "bg-slate-900 border-emerald-500/40 shadow-xs"
                          : "bg-slate-900/60 border-slate-800/80"
                      }`}
                    >
                      <div className="size-7 rounded-lg bg-slate-800 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                        <Icon className="size-3.5" />
                      </div>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-semibold text-slate-100">{step.label}</p>
                          <span className="text-[10px] font-mono text-slate-300">
                            {new Date(step.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 font-mono leading-relaxed">
                          {step.detail}
                        </p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs">
                  <Loader2 className="size-5 animate-spin mx-auto mb-2 text-emerald-500" />
                  Starting Vietnam eVisa worker…
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/60">
          <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
            <ShieldCheck className="size-3.5 text-emerald-400" />
            No captcha solver · no payment automation
          </span>
          <Button
            type="button"
            size="sm"
            onClick={onClose}
            className="cursor-pointer bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5"
          >
            {isCompleted ? "Done" : "Close"}
          </Button>
        </div>
      </div>
    </div>
  );
}

