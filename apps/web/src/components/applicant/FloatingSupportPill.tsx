"use client";

import { useState } from "react";
import { Phone, MessageCircle, X, Clock, ShieldCheck, ChevronUp } from "lucide-react";
import { SUPPORT_CONFIG } from "@/lib/support";

export function FloatingSupportPill() {
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="fixed bottom-[74px] right-6 z-40 hidden sm:block">
      {/* Expanded Quick Call Modal */}
      {open && (
        <div className="absolute bottom-12 right-0 w-72 rounded-2xl border-2 border-primary/30 bg-card/95 p-4 shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-bottom-2 duration-150 space-y-3">
          <div className="flex items-center justify-between border-b pb-2.5">
            <div className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <Phone className="size-3.5" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-foreground">Direct Visa Helpline</h4>
                <p className="text-[10px] text-muted-foreground">{SUPPORT_CONFIG.hours}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="size-3.5" />
            </button>
          </div>

          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Have any question about visa fees, medical invitations, or case status? Call our dedicated staff directly:
          </p>

          <div className="space-y-2 pt-1">
            <a
              href={SUPPORT_CONFIG.telLink}
              className="flex items-center justify-center gap-2 w-full py-2.5 px-3 rounded-xl bg-primary text-primary-foreground text-xs font-bold shadow-sm hover:bg-primary/90 transition-all"
            >
              <Phone className="size-3.5" />
              <span>Call: {SUPPORT_CONFIG.phoneDisplay}</span>
            </a>

            <a
              href={SUPPORT_CONFIG.whatsappLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 px-3 rounded-xl bg-[#25D366] hover:bg-[#20ba5a] text-white text-xs font-bold shadow-sm transition-all"
            >
              <MessageCircle className="size-3.5" />
              <span>WhatsApp Message</span>
            </a>
          </div>

          <div className="pt-1 flex items-center justify-center gap-1.5 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
            <ShieldCheck className="size-3" />
            <span>Official Torii Operations Support</span>
          </div>
        </div>
      )}

      {/* Floating Trigger Pill */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-card/90 hover:bg-card px-3.5 py-2 text-xs font-bold text-foreground shadow-xl backdrop-blur-md transition-all hover:scale-105 hover:border-emerald-500 focus:outline-none"
          title="Direct Support Call / WhatsApp"
        >
          <div className="flex size-5 items-center justify-center rounded-full bg-emerald-500 text-white">
            <Phone className="size-3" />
          </div>
          <span className="text-emerald-700 dark:text-emerald-300 font-bold">Helpline: {SUPPORT_CONFIG.phoneDisplay}</span>
          <ChevronUp className={`size-3 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          className="flex size-6 items-center justify-center rounded-full bg-card/90 hover:bg-muted border border-border/60 text-muted-foreground hover:text-foreground shadow-sm transition-colors"
          title="Dismiss helpline widget"
        >
          <X className="size-3" />
        </button>
      </div>
    </div>
  );
}
