"use client";

import { useState } from "react";
import {
  AlertCircle,
  Bot,
  CheckCircle2,
  Clock,
  CreditCard,
  FileCheck2,
  Globe2,
  KeyRound,
  Loader2,
  RotateCcw,
  ShieldCheck,
  Terminal,
  Upload,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { submitPortalOtp, type PortalJob } from "@/lib/api/portal-bot";

type PortalBotConsoleProps = {
  isOpen: boolean;
  onClose: () => void;
  job: PortalJob | null;
  loading: boolean;
  caseId?: number;
  onJobUpdated?: (updatedJob: PortalJob) => void;
  onRetry?: () => void;
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
  awaiting_otp: KeyRound,
  submitting_otp: KeyRound,
};

export function PortalBotConsole({
  isOpen,
  onClose,
  job,
  loading: _loading,
  caseId,
  onJobUpdated,
  onRetry,
}: PortalBotConsoleProps) {
  const { token } = useAuth();
  const [otp, setOtp] = useState("");
  const [submittingOtp, setSubmittingOtp] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);

  if (!isOpen) return null;

  const isCompleted = job?.status === "succeeded" && Boolean(job.portal_reference);
  const isFailed = job?.status === "failed";
  const needsHuman = job?.status === "manual_takeover" || job?.status === "awaiting_otp";

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    if (!caseId || !otp.trim()) return;
    setSubmittingOtp(true);
    setOtpError(null);
    try {
      const updated = await submitPortalOtp(token, caseId, otp.trim());
      onJobUpdated?.(updated);
      setOtp("");
    } catch (err: unknown) {
      setOtpError(err instanceof Error ? err.message : "Failed to verify OTP code with portal");
    } finally {
      setSubmittingOtp(false);
    }
  }

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
                  {job?.portal_name || "Official Portal Submission Worker"}
                </h3>
                <Badge
                  tone={
                    isCompleted ? "success" : isFailed ? "warning" : needsHuman ? "warning" : "info"
                  }
                  className="text-[10px] px-2 py-0 uppercase tracking-wider"
                >
                  {isCompleted
                    ? "Confirmation captured"
                    : isFailed
                      ? "Failed"
                      : needsHuman
                        ? "OTP / Verification Required"
                        : "Running"}
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {job?.portal_url || "https://ksavisa.sa"}
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
                  Official Government Registration Code Captured
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-black/40 border border-emerald-500/20 flex items-center justify-between">
                <span className="text-xs text-slate-400">Government Reference:</span>
                <span className="font-mono text-base font-bold text-emerald-400 tracking-wider">
                  {job.portal_reference}
                </span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                This confirmation code was verified and read directly from the official portal.
              </p>
            </div>
          )}

          {/* Failed Banner with Retry */}
          {isFailed && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-2.5 animate-in fade-in duration-200">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <AlertCircle className="size-5 text-rose-400 shrink-0" />
                  <span className="text-sm font-bold text-white">Bot Worker Encountered an Error</span>
                </div>
                {onRetry && (
                  <Button
                    size="sm"
                    type="button"
                    disabled={_loading}
                    onClick={onRetry}
                    className="bg-rose-600 hover:bg-rose-500 text-white text-xs h-7 px-3 font-semibold gap-1.5 cursor-pointer rounded-lg shadow-xs"
                  >
                    {_loading ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <RotateCcw className="size-3" />
                    )}
                    <span>Retry Bot</span>
                  </Button>
                )}
              </div>
              <p className="text-xs text-rose-200 font-mono leading-relaxed bg-black/30 p-2.5 rounded-lg border border-rose-500/20">
                {job?.error_message || "The automated portal worker encountered an error."}
              </p>
            </div>
          )}

          {/* Interactive Live Verification Code (OTP) Form */}
          {needsHuman && !isCompleted && (
            <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-100 space-y-4 animate-in fade-in duration-200">
              <div className="flex items-start gap-3">
                <div className="size-9 rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
                  <KeyRound className="size-5" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold text-white">
                    Government Verification Code (OTP) Required
                  </p>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    The government portal sent a verification code to your phone or email. Enter it below to resume the session and complete your filing.
                  </p>
                </div>
              </div>

              {caseId ? (
                <form onSubmit={handleSendOtp} className="pt-1 flex flex-col sm:flex-row items-stretch gap-2.5">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/[^0-9a-zA-Z]/g, "").slice(0, 10))}
                      placeholder="Enter 4 to 8 digit code"
                      maxLength={10}
                      className="w-full h-10 px-4 rounded-xl bg-black/60 border border-amber-500/40 text-center font-mono text-base font-bold tracking-widest text-white placeholder:text-slate-500 placeholder:tracking-normal placeholder:font-sans placeholder:text-xs focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                      autoFocus
                      disabled={submittingOtp}
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={submittingOtp || otp.trim().length < 4}
                    className="h-10 px-5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 cursor-pointer shadow-sm transition-all shrink-0"
                  >
                    {submittingOtp ? (
                      <>
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>Verifying with Portal…</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="size-3.5" />
                        <span>Submit Code & Finish</span>
                      </>
                    )}
                  </Button>
                </form>
              ) : null}

              {otpError && (
                <p className="text-xs font-medium text-rose-400 bg-rose-950/40 border border-rose-800/50 rounded-lg p-2.5">
                  {otpError}
                </p>
              )}
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
                  Starting portal worker…
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/60">
          <span className="text-[11px] text-slate-300 flex items-center gap-1.5">
            <ShieldCheck className="size-3.5 text-emerald-400" />
            Encrypted session · Official government gateway
          </span>
          <div className="flex items-center gap-2">
            {isFailed && onRetry && (
              <Button
                type="button"
                size="sm"
                disabled={_loading}
                onClick={onRetry}
                className="cursor-pointer bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 font-semibold px-4 text-xs gap-1.5"
              >
                {_loading ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <RotateCcw className="size-3.5" />
                )}
                <span>Retry Bot</span>
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              onClick={onClose}
              className="cursor-pointer bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-5 text-xs"
            >
              {isCompleted ? "Done" : "Close"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

