"use client";

import { useState } from "react";
import {
  Bell,
  CheckCircle2,
  Clock,
  FileText,
  Rocket,
  ShieldCheck,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { MatchedProduct } from "@/lib/api/concierge";
import type { ChecklistItem } from "./steps/types";

type ConciergeModalProps = {
  isOpen: boolean;
  onClose: () => void;
  item: ChecklistItem | null;
  product: MatchedProduct | null;
  onConfirm?: (item: ChecklistItem, product: MatchedProduct) => Promise<void>;
};

export function ConciergeModal({
  isOpen,
  onClose,
  item,
  product,
}: ConciergeModalProps) {
  const [waitlistJoined, setWaitlistJoined] = useState(false);

  if (!isOpen || !item || !product) return null;

  const priceLabel =
    product.price_cents === 0 ? "Free" : `$${(product.price_cents / 100).toFixed(0)}`;

  function handleJoinWaitlist() {
    setWaitlistJoined(true);
  }

  function handleClose() {
    setWaitlistJoined(false);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/20">
          <div className="flex items-center gap-2.5">
            <div className="size-9 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center justify-center">
              <Rocket className="size-4.5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-foreground">Document Concierge</h3>
                <Badge tone="warning" className="text-[10px] px-2 py-0">
                  Coming Soon
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">Automated Document Procurement</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors cursor-pointer"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Product Banner */}
          <div className="p-4 rounded-xl border border-border/80 bg-muted/30 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-base font-semibold text-foreground">{product.name}</h4>
                <p className="text-xs text-muted-foreground mt-0.5">{product.description}</p>
              </div>
              <Badge tone="info" className="text-xs px-2.5 py-0.5 font-bold shrink-0">
                {priceLabel}
              </Badge>
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-border/60 text-xs text-muted-foreground">
              <span>Required for:</span>
              <span className="font-semibold text-foreground flex items-center gap-1">
                <FileText className="size-3 text-primary" />
                {item.name}
              </span>
            </div>
          </div>

          {/* Coming Soon Notice */}
          <div className="p-4 rounded-xl bg-gradient-to-br from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/20 space-y-2.5 text-xs">
            <div className="font-semibold text-amber-700 dark:text-amber-300 flex items-center gap-2">
              <Clock className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />
              Automated Document Procurement Coming Soon
            </div>
            <p className="text-muted-foreground leading-relaxed">
              We are currently integrating direct partnerships with accredited airline booking networks,
              consulate-approved insurance underwriters, and medical referral providers to generate 100%
              embassy-compliant documents automatically.
            </p>
            <ul className="space-y-1.5 text-muted-foreground pt-1">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Instant verifiable PDF downloads directly to your application</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>100% consulate-compliant &amp; accepted by visa authorities</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Zero manual paperwork or costly agency fees</span>
              </li>
            </ul>
          </div>

          {/* Waitlist feedback state */}
          {waitlistJoined ? (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs flex items-center gap-2.5 text-emerald-800 dark:text-emerald-300 animate-in fade-in slide-in-from-bottom-2 duration-200">
              <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <div>
                <p className="font-semibold">You&apos;re on the early-access list!</p>
                <p className="text-[11px] text-muted-foreground">
                  We&apos;ll notify you as soon as one-click document procurement goes live for your route.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-muted/40 border border-border/60 text-xs flex items-center justify-between gap-3">
              <div className="text-muted-foreground">
                Want to be notified when this goes live?
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleJoinWaitlist}
                className="h-7 text-xs gap-1.5 shrink-0 border-amber-500/30 text-amber-700 dark:text-amber-400 hover:bg-amber-500/10 cursor-pointer"
              >
                <Bell className="size-3" />
                <span>Notify Me</span>
              </Button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-border bg-muted/10">
          <span className="text-[11px] text-muted-foreground flex items-center gap-1.5">
            <ShieldCheck className="size-3.5 text-primary" />
            Torii Verified Partner Network
          </span>
          <Button
            type="button"
            size="sm"
            onClick={handleClose}
            className="cursor-pointer bg-primary text-primary-foreground hover:bg-primary/90 px-4"
          >
            Got It
          </Button>
        </div>
      </div>
    </div>
  );
}
