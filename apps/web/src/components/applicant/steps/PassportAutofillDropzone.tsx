"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import {
  Sparkles,
  UploadCloud,
  FileCheck2,
  Loader2,
  CheckCircle2,
  FileText,
  AlertCircle,
  Camera,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { uploadDocument, type WalletUploadResponse } from "@/lib/api/wallet";
import { extractFromFile } from "@/lib/api/ocr";

export type PassportAutofillDropzoneProps = {
  token?: string | null;
  caseId?: number;
  onFieldsExtracted: (fields: Record<string, string>, docName: string) => void;
  onRefresh?: () => void;
  autofilledCount?: number;
};

export function PassportAutofillDropzone({
  token,
  caseId: _caseId,
  onFieldsExtracted,
  onRefresh,
  autofilledCount = 0,
}: PassportAutofillDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanSuccess, setScanSuccess] = useState<{
    docName: string;
    extracted: Record<string, string>;
  } | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  async function processPassportFile(file: File) {
    if (!file) return;

    // Validate size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File size exceeds 10MB. Please upload a smaller photo or PDF.");
      return;
    }

    setIsScanning(true);
    setScanError(null);

    const docName = file.name.replace(/\.[^/.]+$/, "");
    const extractedMap: Record<string, string> = {};

    try {
      // 1. Try uploading to wallet vault (which parses OCR and syncs to active case on backend)
      let rawFields: Record<string, unknown> | null = null;
      try {
        const walletRes: WalletUploadResponse = await uploadDocument(
          token,
          file,
          "passport",
          file.name,
        );
        if (walletRes.extracted_fields && typeof walletRes.extracted_fields === "object") {
          rawFields = walletRes.extracted_fields as Record<string, unknown>;
        }
      } catch (walletErr) {
        console.warn("Wallet upload notice:", walletErr);
      }

      // 2. If wallet OCR didn't yield fields, try direct AI OCR endpoint
      if (!rawFields || Object.keys(rawFields).length === 0) {
        try {
          const aiOcr = await extractFromFile(file, "passport");
          if (aiOcr.fields && Object.keys(aiOcr.fields).length > 0) {
            rawFields = aiOcr.fields as Record<string, unknown>;
          }
        } catch (aiErr) {
          console.warn("Direct AI OCR fallback notice:", aiErr);
        }
      }

      // 3. Normalize extracted fields into key-value strings
      if (rawFields) {
        for (const [key, val] of Object.entries(rawFields)) {
          if (!val) continue;
          if (typeof val === "object" && val !== null && "value" in val) {
            const v = (val as { value: unknown }).value;
            if (v !== undefined && v !== null && String(v).trim()) {
              extractedMap[key] = String(v).trim();
            }
          } else if (typeof val === "string" && val.trim()) {
            extractedMap[key] = val.trim();
          }
        }
      }

      const count = Object.keys(extractedMap).length;
      if (count > 0) {
        setScanSuccess({ docName: file.name, extracted: extractedMap });
        onFieldsExtracted(extractedMap, file.name);
        if (onRefresh) onRefresh();
        toast.success(`Passport verified! Extracted ${count} field${count === 1 ? "" : "s"} into your form.`);
      } else {
        // Fallback: If no structured fields could be parsed, let the user know
        setScanError(
          "We could not read clear text from this file. Please make sure the photo is well-lit, non-blurry, and the passport MRZ lines are visible.",
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to scan passport.";
      setScanError(msg);
      toast.error(msg);
    } finally {
      setIsScanning(false);
    }
  }

  function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      void processPassportFile(file);
    }
    // Reset input so same file can be selected again if needed
    e.target.value = "";
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      void processPassportFile(file);
    }
  }

  return (
    <div className="space-y-3">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Dropzone Card */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isScanning && fileInputRef.current?.click()}
        className={`relative overflow-hidden rounded-2xl border-2 border-dashed p-4 sm:p-5 transition-all cursor-pointer select-none ${
          isDragging
            ? "border-emerald-500 bg-emerald-500/15 scale-[1.008] ring-4 ring-emerald-500/20 shadow-lg"
            : isScanning
              ? "border-emerald-500/50 bg-emerald-500/5 cursor-wait"
              : scanSuccess
                ? "border-emerald-500/40 bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent hover:border-emerald-500/60"
                : "border-emerald-500/35 bg-gradient-to-r from-emerald-500/[0.08] via-emerald-500/[0.03] to-sky-500/[0.04] hover:border-emerald-500/60 hover:bg-emerald-500/[0.10] shadow-xs"
        }`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            {/* Icon */}
            <div
              className={`size-11 rounded-xl flex items-center justify-center shrink-0 shadow-sm border transition-all ${
                isScanning
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400"
                  : scanSuccess
                    ? "bg-emerald-500 text-white border-emerald-400 shadow-emerald-500/20"
                    : "bg-emerald-500/15 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
              }`}
            >
              {isScanning ? (
                <Loader2 className="size-5 animate-spin" />
              ) : scanSuccess ? (
                <CheckCircle2 className="size-5" />
              ) : (
                <Camera className="size-5" />
              )}
            </div>

            {/* Headline and Copy */}
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-foreground tracking-tight">
                  {isScanning
                    ? "Scanning & Extracting Passport Data…"
                    : scanSuccess
                      ? "Passport Verified & Fields Extracted"
                      : "Fast-Track Application: Auto-Fill with Passport"}
                </span>
                <Badge
                  tone="success"
                  className="text-[10px] font-bold px-2 py-0 uppercase tracking-wider flex items-center gap-1"
                >
                  <Sparkles className="size-2.5" />
                  AI OCR Fast-Fill
                </Badge>
                {autofilledCount > 0 && !scanSuccess && (
                  <Badge tone="default" className="text-[10px] font-medium border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10">
                    {autofilledCount} fields filled
                  </Badge>
                )}
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed max-w-xl">
                {isScanning
                  ? "Our AI is reading your photo, passport number, birth date, and MRZ lines to populate the questionnaire…"
                  : scanSuccess
                    ? `Extracted from ${scanSuccess.docName}. You can click below to scan an additional document (national ID, ticket, or hotel).`
                    : "Drag & drop your passport bio page or national ID (JPG, PNG, PDF). Torii will instantly extract and populate your personal details so you don't have to type them."}
              </p>
            </div>
          </div>

          {/* Action Button */}
          <div className="shrink-0 self-end sm:self-center flex items-center gap-2">
            {scanSuccess ? (
              <Button
                size="sm"
                variant="outline"
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="text-xs h-8 font-semibold border-emerald-500/40 hover:bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 gap-1.5 cursor-pointer rounded-xl"
              >
                <RotateCcw className="size-3" />
                Scan Another File
              </Button>
            ) : (
              <Button
                size="sm"
                type="button"
                disabled={isScanning}
                className="text-xs h-8.5 font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs gap-1.5 px-4 cursor-pointer rounded-xl"
              >
                {isScanning ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Scanning…</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="size-3.5" />
                    <span>Upload Passport</span>
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Extracted pills preview if scanSuccess */}
        {scanSuccess && Object.keys(scanSuccess.extracted).length > 0 && (
          <div className="mt-3 pt-3 border-t border-emerald-500/20 flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 mr-1">
              <FileCheck2 className="size-3" /> Extracted:
            </span>
            {Object.entries(scanSuccess.extracted)
              .slice(0, 6)
              .map(([key, val]) => (
                <span
                  key={key}
                  className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-foreground font-mono"
                >
                  <strong className="font-sans font-medium text-muted-foreground mr-1">
                    {key.replace(/_/g, " ")}:
                  </strong>
                  {val}
                </span>
              ))}
            {Object.keys(scanSuccess.extracted).length > 6 && (
              <span className="text-muted-foreground text-[10px] pl-1">
                +{Object.keys(scanSuccess.extracted).length - 6} more
              </span>
            )}
          </div>
        )}

        {/* Error message */}
        {scanError && (
          <div className="mt-3 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="size-4 shrink-0 text-rose-400" />
            <span>{scanError}</span>
          </div>
        )}
      </div>
    </div>
  );
}
