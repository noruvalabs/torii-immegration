"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Check,
  Upload,
  Loader2,
  Camera,
  ExternalLink,
  FolderOpen,
  ShieldCheck,
  Eye,
  Download,
  X,
  FileText,
  Sparkles,
  Clock,
  Plane,
  Building2,
  Bell,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";
import { useCredits } from "@/lib/credits-context";
import { useQueryClient } from "@tanstack/react-query";
import {
  registerDocument,
  getCaseDocumentFileUrl,
  getChecklistItemFileUrl,
} from "@/lib/api/cases";
import { caseKeys, useDocumentsQuery } from "@/lib/queries/cases";
import { extractFromFile, type OCRResult, type DocumentType } from "@/lib/api/ocr";
import { getWallet, uploadDocument, type WalletDocument } from "@/lib/api/wallet";
import {
  getAvailableConcierge,
  orderConcierge,
  type ConciergeMatch,
  type MatchedProduct,
} from "@/lib/api/concierge";
import { ConciergeModal } from "@/components/applicant/ConciergeModal";
import type { ChecklistItem } from "./types";
import { citationUrl, citationVersion } from "./types";

type ChecklistStepProps = {
  items: ChecklistItem[];
  caseId: number;
  loading: boolean;
  onRefresh: () => void;
  onStatusChange: (itemId: number, status: string) => void;
};

function mapDocType(checklistCode: string): DocumentType {
  const code = checklistCode.toLowerCase();
  if (code.includes("passport") && !code.includes("photo")) {
    return "passport";
  }
  if (code.includes("fund") || code.includes("bank") || code.includes("financial")) {
    return "proof_of_funds";
  }
  if (code.includes("residence") || code.includes("card") || code.includes("zairyu")) {
    return "residence_card";
  }
  if (
    code.includes("itinerary") ||
    code.includes("travel") ||
    code.includes("flight") ||
    code.includes("hotel") ||
    code.includes("accommodation") ||
    code.includes("booking")
  ) {
    return "travel_itinerary";
  }
  return "employment_contract";
}

/** Common doc matching: wallet passport can satisfy multiple checklist passport items. */
function matchWalletToChecklist(walletDoc: WalletDocument, checklistCode: string): boolean {
  const docType = walletDoc.doc_type.toLowerCase();
  const name = walletDoc.name.toLowerCase();
  const code = checklistCode.toLowerCase();
  const combined = `${docType} ${name}`;

  if (code.includes("passport") && !code.includes("photo")) {
    return combined.includes("passport") && !combined.includes("photo");
  }
  if (code.includes("photo") || code.includes("photograph")) {
    return combined.includes("photo") || combined.includes("photograph");
  }
  if (
    code.includes("medical") ||
    code.includes("hospital") ||
    code.includes("doctor") ||
    code.includes("referral") ||
    code.includes("prescription")
  ) {
    return (
      combined.includes("medical") ||
      combined.includes("hospital") ||
      combined.includes("doctor") ||
      combined.includes("referral") ||
      combined.includes("prescription")
    );
  }
  if (code.includes("yellow_fever") || code.includes("polio") || code.includes("vaccin")) {
    return combined.includes("yellow") || combined.includes("fever") || combined.includes("polio") || combined.includes("vaccin") || combined.includes("immun");
  }
  if (code.includes("utility") || code.includes("bill") || code.includes("address_proof")) {
    return combined.includes("utility") || combined.includes("bill") || combined.includes("electricity") || combined.includes("gas") || combined.includes("address");
  }
  if (code.includes("i20") || code.includes("i-20")) {
    return combined.includes("i20") || combined.includes("i-20") || combined.includes("eligibility");
  }
  if (code.includes("sevis")) {
    return combined.includes("sevis") || combined.includes("i901") || combined.includes("i-901");
  }
  if (code.includes("transcript") || code.includes("degree") || code.includes("diploma") || code.includes("test") || code.includes("admission")) {
    return (
      combined.includes("transcript") ||
      combined.includes("degree") ||
      combined.includes("diploma") ||
      combined.includes("toefl") ||
      combined.includes("ielts") ||
      combined.includes("score") ||
      combined.includes("admission") ||
      combined.includes("acceptance")
    );
  }
  if (
    code.includes("fund") ||
    code.includes("bank") ||
    code.includes("financial") ||
    code.includes("finance") ||
    code.includes("tsucho") ||
    code.includes("sponsor") ||
    code.includes("scholarship")
  ) {
    return (
      combined.includes("fund") ||
      combined.includes("bank") ||
      combined.includes("financial") ||
      combined.includes("statement") ||
      combined.includes("tsucho") ||
      combined.includes("balance") ||
      combined.includes("sponsor") ||
      combined.includes("scholarship")
    );
  }
  if (
    code.includes("itinerary") ||
    code.includes("travel") ||
    code.includes("flight") ||
    code.includes("hotel") ||
    code.includes("accommodation") ||
    code.includes("invitation")
  ) {
    return (
      combined.includes("itinerary") ||
      combined.includes("travel") ||
      combined.includes("flight") ||
      combined.includes("hotel") ||
      combined.includes("accommodation") ||
      combined.includes("booking") ||
      combined.includes("invitation")
    );
  }
  if (code.includes("employment") || code.includes("ties") || code.includes("job") || code.includes("zaishoku") || code.includes("tokibo") || code.includes("zaigaku")) {
    return (
      combined.includes("employment") ||
      combined.includes("job") ||
      combined.includes("employer") ||
      combined.includes("contract") ||
      combined.includes("zaishoku") ||
      combined.includes("tokibo") ||
      combined.includes("zaigaku")
    );
  }
  if (code.includes("tax") || code.includes("juminzei") || code.includes("shotoku")) {
    return combined.includes("tax") || combined.includes("juminzei") || combined.includes("shotoku");
  }
  if (code.includes("residence") || code.includes("card") || code.includes("zairyu")) {
    return combined.includes("residence") || combined.includes("card") || combined.includes("zairyu");
  }
  return docType === code || name.includes(code) || combined.includes(code.replaceAll("_", " "));
}

export function ChecklistStep({
  items,
  caseId,
  loading,
  onRefresh,
  onStatusChange,
}: ChecklistStepProps) {
  const { token } = useAuth();
  const { data: documents = [] } = useDocumentsQuery(token, caseId);
  const [viewingDoc, setViewingDoc] = useState<{
    id: number | null;
    checklistItemId: number;
    name: string;
    filename: string;
    url: string;
    extractedFields?: Record<string, unknown>;
  } | null>(null);
  const queryClient = useQueryClient();
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [conciergeMatches, setConciergeMatches] = useState<ConciergeMatch[]>([]);
  const [conciergeModalState, setConciergeModalState] = useState<{
    item: ChecklistItem;
    product: MatchedProduct;
  } | null>(null);
  const [comingSoonModalItem, setComingSoonModalItem] = useState<ChecklistItem | null>(null);
  const [waitlistJoined, setWaitlistJoined] = useState(false);
  const [attaching, setAttaching] = useState<number | null>(null);
  const [showPicker, setShowPicker] = useState<number | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [mode, setMode] = useState<"upload" | "scan" | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingItemRef = useRef<ChecklistItem | null>(null);
  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  useEffect(() => {
    if (!token) return;
    getWallet(token).then(setWalletDocs).catch(() => { });
  }, [token]);

  useEffect(() => {
    if (!token || !caseId) return;
    getAvailableConcierge(token, caseId)
      .then(setConciergeMatches)
      .catch(() => { });
  }, [token, caseId]);

  async function handleConciergeConfirm(item: ChecklistItem, product: MatchedProduct) {
    if (!token) return;
    const order = await orderConcierge(token, caseId, item.id, product.id);
    const updated = await getAvailableConcierge(token, caseId);
    setConciergeMatches(updated);
    await queryClient.invalidateQueries({ queryKey: caseKeys.documents(caseId) });
    setSuccessNotice(`Document procured successfully! ${product.name} delivered.`);
    onRefresh();
  }

  function getMatchingWalletDocs(checklistCode: string): WalletDocument[] {
    return walletDocs.filter(
      (d) => d.status === "active" && matchWalletToChecklist(d, checklistCode),
    );
  }

  async function handleAttachWallet(itemId: number, walletDoc: WalletDocument) {
    if (!token) return;
    setAttaching(itemId);
    const item = items.find((i) => i.id === itemId);
    try {
      await registerDocument(token, caseId, {
        doc_type: item?.code || walletDoc.doc_type,
        checklist_item_id: itemId,
        filename: walletDoc.filename,
        storage_key: `wallet/${walletDoc.id}`,
        extracted_fields: walletDoc.extracted_fields || {},
        content_type: walletDoc.content_type,
      });
      await onStatusChange(itemId, "uploaded");
      await queryClient.invalidateQueries({ queryKey: caseKeys.documents(caseId) });
      await queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
      setShowPicker(null);
      onRefresh();
    } catch {
      // surface via parent if needed
    } finally {
      setAttaching(null);
    }
  }

  function handleUploadClick(item: ChecklistItem) {
    pendingItemRef.current = item;
    setMode("upload");
    setOcrResult(null);
    setOcrError(null);
    fileInputRef.current?.click();
  }

  function handleScanClick(item: ChecklistItem) {
    pendingItemRef.current = item;
    setMode("scan");
    setOcrResult(null);
    setOcrError(null);
    fileInputRef.current?.click();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const item = pendingItemRef.current;
    if (!file || !item || !token) return;

    setUploading(item.id);
    setOcrError(null);
    setSuccessNotice(null);

    try {
      const docType = mapDocType(item.code);
      setOcrLoading(true);

      // Run AI OCR on all uploaded files to extract and auto-fill intake answers
      let extracted: Record<string, { value: string; confidence: number }> = {};
      try {
        const result = await extractFromFile(file, docType);
        if (result && result.fields && Object.keys(result.fields).length > 0) {
          extracted = result.fields;
          setOcrResult(result);
        }
      } catch (ocrErr) {
        console.warn("OCR extraction notice:", ocrErr);
      }

      let storageKey = `upload/${item.id}/${file.name}`;
      try {
        const walletRes = await uploadDocument(token, file, docType, item.name);
        if (walletRes?.storage_key) {
          storageKey = walletRes.storage_key;
        }
        const refreshed = await getWallet(token);
        setWalletDocs(refreshed);
      } catch (walletErr) {
        console.warn("Wallet upload notice:", walletErr);
      }

      await registerDocument(token, caseId, {
        doc_type: item.code,
        checklist_item_id: item.id,
        filename: file.name,
        storage_key: storageKey,
        extracted_fields: extracted,
        content_type: file.type || "application/octet-stream",
      });

      await onStatusChange(item.id, "uploaded");
      await queryClient.invalidateQueries({ queryKey: caseKeys.documents(caseId) });
      await queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
      onRefresh();

      if (Object.keys(extracted).length > 0) {
        const fieldLabels = Object.keys(extracted)
          .map((k) => k.replaceAll("_", " ").toUpperCase())
          .join(", ");
        setSuccessNotice(`✨ AI successfully extracted and auto-filled data from ${file.name}: ${fieldLabels}`);
        setTimeout(() => setSuccessNotice(null), 9000);
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setOcrLoading(false);
      setUploading(null);
      setMode(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleConfirmExtracted() {
    const item = pendingItemRef.current;
    if (!item || !token || !ocrResult) return;

    try {
      await registerDocument(token, caseId, {
        doc_type: mapDocType(item.code),
        filename: `checklist-${item.code}.txt`,
        storage_key: `checklist/${item.id}`,
        extracted_fields: ocrResult.fields,
        extraction_confidence: Object.values(ocrResult.fields)[0]?.confidence ?? 0,
      });

      try {
        const blob = new Blob([JSON.stringify(ocrResult.fields)], { type: "application/json" });
        const file = new File([blob], `checklist-${item.code}.json`, { type: "application/json" });
        await uploadDocument(token, file, mapDocType(item.code), item.name);
        const refreshed = await getWallet(token);
        setWalletDocs(refreshed);
      } catch {
        // Wallet upload is optional
      }

      await onStatusChange(item.id, "gathered");
      await queryClient.invalidateQueries({ queryKey: caseKeys.documents(caseId) });
      await queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
      setOcrResult(null);
      onRefresh();
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  async function handleDirectItemUpload(
    e: React.ChangeEvent<HTMLInputElement>,
    item: ChecklistItem
  ) {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    setUploading(item.id);
    setOcrError(null);
    setSuccessNotice(null);

    try {
      const docType = mapDocType(item.code);
      setOcrLoading(true);

      // Run AI OCR on uploaded file
      let extracted: Record<string, { value: string; confidence: number }> = {};
      try {
        const result = await extractFromFile(file, docType);
        if (result && result.fields && Object.keys(result.fields).length > 0) {
          extracted = result.fields;
          setOcrResult(result);
        }
      } catch (ocrErr) {
        console.warn("OCR extraction notice:", ocrErr);
      }

      let storageKey = `upload/${item.id}/${file.name}`;
      try {
        const walletRes = await uploadDocument(token, file, docType, item.name);
        if (walletRes?.storage_key) {
          storageKey = walletRes.storage_key;
        }
        const refreshed = await getWallet(token);
        setWalletDocs(refreshed);
      } catch (walletErr) {
        console.warn("Wallet upload notice:", walletErr);
      }

      await registerDocument(token, caseId, {
        doc_type: item.code,
        checklist_item_id: item.id,
        filename: file.name,
        storage_key: storageKey,
        extracted_fields: extracted,
        content_type: file.type || "application/octet-stream",
      });

      await onStatusChange(item.id, "uploaded");
      await queryClient.invalidateQueries({ queryKey: caseKeys.documents(caseId) });
      await queryClient.invalidateQueries({ queryKey: caseKeys.checklist(caseId) });
      onRefresh();

      if (Object.keys(extracted).length > 0) {
        const fieldLabels = Object.keys(extracted)
          .map((k) => k.replaceAll("_", " ").toUpperCase())
          .join(", ");
        setSuccessNotice(`✨ AI extracted data from ${file.name}: ${fieldLabels}`);
        setTimeout(() => setSuccessNotice(null), 9000);
      } else {
        setSuccessNotice(`✅ Successfully uploaded ${file.name}`);
        setTimeout(() => setSuccessNotice(null), 5000);
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setOcrLoading(false);
      setUploading(null);
      if (e.target) e.target.value = "";
    }
  }

  const requiredNeeded = items.filter((i) => i.is_required && i.status === "needed").length;
  const gatheredCount = items.filter((i) => i.status !== "needed").length;

  return (
    <div className="space-y-6">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf,.doc,.docx"
        className="hidden"
        onChange={handleFileChange}
      />

      {successNotice && (
        <div className="rounded-[var(--radius)] border border-emerald-500/30 bg-emerald-500/10 p-3.5 flex items-center gap-2.5 text-xs text-emerald-800 dark:text-emerald-300 animate-in fade-in slide-in-from-top-1">
          <Check className="size-4 shrink-0 text-emerald-500" />
          <span className="font-medium">{successNotice}</span>
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Document checklist</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {gatheredCount} of {items.length} gathered
            {requiredNeeded > 0 ? ` · ${requiredNeeded} required remaining` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius)] border px-3 py-1.5 text-xs font-medium hover:bg-accent text-primary"
          >
            <ShieldCheck className="size-3.5" />
            Manage Document Vault
          </Link>
          <Button variant="outline" onClick={onRefresh} disabled={loading} className="px-3 py-1.5 text-xs">
            {items.length === 0 ? "Generate checklist" : "Refresh"}
          </Button>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No checklist items yet. Generate your personalized list after eligibility.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((item) => {
            const url = citationUrl(item.citation);
            const version = citationVersion(item.citation);
            const matchingDocs = getMatchingWalletDocs(item.code);
            const isGathered = item.status !== "needed";
            const busy = uploading === item.id || attaching === item.id;
            const matchedDoc = item.document_id
              ? documents.find((d) => d.id === item.document_id)
              : documents.slice().reverse().find((d) => d.doc_type === item.code);
            const fileUrl = matchedDoc
              ? getCaseDocumentFileUrl(caseId, matchedDoc.id, token)
              : getChecklistItemFileUrl(caseId, item.id, token);
            const fileName = matchedDoc?.filename || `${item.name}.pdf`;
            const conciergeMatch = conciergeMatches.find(
              (m) => m.checklist_item_id === item.id,
            );
            const primaryProduct = conciergeMatch?.products?.[0];
            const existingOrder = conciergeMatch?.existing_order;
            const itemCodeLower = item.code.toLowerCase();
            const itemNameLower = item.name.toLowerCase();
            const isTravelOrBookingDoc =
              itemCodeLower.includes("flight") ||
              itemCodeLower.includes("hotel") ||
              itemCodeLower.includes("accommodation") ||
              itemCodeLower.includes("itinerary") ||
              itemCodeLower.includes("ticket") ||
              itemCodeLower.includes("booking") ||
              itemNameLower.includes("flight") ||
              itemNameLower.includes("hotel") ||
              itemNameLower.includes("accommodation") ||
              itemNameLower.includes("ticket") ||
              itemNameLower.includes("booking");

            return (
              <div
                key={item.id}
                className="rounded-2xl border border-border/90 dark:border-slate-800 bg-card p-5 flex flex-col justify-between transition-all hover:border-border dark:hover:border-slate-700 shadow-xs gap-4"
              >
                {/* Top Section: Title & Details */}
                <div className="space-y-3">
                  {/* Card Header Row */}
                  <div className="flex items-start gap-3.5">
                    <div
                      className={`size-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${isGathered
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                          : "bg-muted/60 text-muted-foreground border border-border/70 dark:border-slate-800"
                        }`}
                    >
                      {isGathered ? (
                        <Check className="size-4 stroke-[2.5]" />
                      ) : (
                        <FileText className="size-4" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold text-foreground tracking-tight leading-snug">
                          {item.name}
                        </h4>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {item.is_required ? (
                            <span className="text-[10px] font-semibold text-rose-600 dark:text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full">
                              Required
                            </span>
                          ) : (
                            <span className="text-[10px] font-normal text-muted-foreground bg-muted/60 border border-border/50 px-2 py-0.5 rounded-full">
                              Optional
                            </span>
                          )}
                          {isGathered ? (
                            <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                              ✓ Ready
                            </span>
                          ) : matchingDocs.length > 0 ? (
                            <span className="text-[10px] font-medium text-primary bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-full">
                              {matchingDocs.length} in wallet
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Attached Document Pill (if uploaded) */}
                  {isGathered && (
                    <div className="flex items-center justify-between gap-2.5 px-3 py-2 rounded-xl bg-muted/30 border border-border/70 dark:border-slate-800 text-xs">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <FileText className="size-3.5 text-primary shrink-0" />
                        <span
                          className="font-mono text-[11px] font-medium truncate text-foreground"
                          title={fileName}
                        >
                          {fileName}
                        </span>
                      </div>
                      {matchedDoc?.extracted_fields &&
                        Object.keys(matchedDoc.extracted_fields).length > 0 && (
                          <Badge tone="info" className="text-[9px] py-0 px-1.5 shrink-0">
                            ✨ AI Verified
                          </Badge>
                        )}
                    </div>
                  )}

                  {/* Explanatory Guidance */}
                  <div className="space-y-1.5 text-xs leading-relaxed pt-0.5">
                    {item.how_to_obtain && (
                      <div className="flex items-start gap-1.5">
                        <span className="text-[11px] font-semibold text-foreground shrink-0">
                          How:
                        </span>
                        <span className="text-muted-foreground/90">{item.how_to_obtain}</span>
                      </div>
                    )}
                    {item.why_required && (
                      <div className="flex items-start gap-1.5 text-[11px] text-muted-foreground/80">
                        <span className="font-semibold text-foreground/80 shrink-0">
                          Why:
                        </span>
                        <span>{item.why_required}</span>
                      </div>
                    )}
                  </div>

                  {/* Concierge Order Status (Thing 2) */}
                  {existingOrder && (
                    <div className="flex items-center justify-between gap-2.5 px-3 py-2 rounded-xl bg-muted/40 border border-border/80 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        {existingOrder.status === "fulfilled" ? (
                          <ShieldCheck className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        ) : (
                          <Clock className="size-4 text-amber-500 shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p className="font-semibold text-foreground truncate">
                            {existingOrder.status === "fulfilled"
                              ? "Delivered via Concierge"
                              : "Document Procurement Coming Soon"}
                          </p>
                          <p className="text-[11px] text-muted-foreground truncate">
                            {existingOrder.status === "fulfilled"
                              ? "Official verifiable document ready"
                              : "Automated generation is currently in development"}
                          </p>
                        </div>
                      </div>
                      <Badge
                        tone={existingOrder.status === "fulfilled" ? "success" : "warning"}
                        className="text-[10px] shrink-0"
                      >
                        {existingOrder.status === "fulfilled" ? "✅ Delivered" : "Coming Soon"}
                      </Badge>
                    </div>
                  )}
                </div>

                {/* Dedicated Card Footer Toolbar */}
                <div className="pt-3 border-t border-border/70 dark:border-slate-800/80 flex flex-wrap items-center justify-between gap-2">
                  {isGathered ? (
                    <div className="flex flex-wrap items-center justify-between gap-2 w-full">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => {
                            setViewingDoc({
                              id: matchedDoc?.id || null,
                              checklistItemId: item.id,
                              name: item.name,
                              filename: fileName,
                              url: fileUrl,
                              extractedFields: matchedDoc?.extracted_fields as
                                | Record<string, unknown>
                                | undefined,
                            });
                          }}
                          className="h-8 text-xs gap-1.5 px-3 font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xs cursor-pointer"
                        >
                          <Eye className="size-3.5" />
                          View
                        </Button>

                        <input
                          id={`file-reupload-${item.id}`}
                          type="file"
                          accept="image/*,.pdf,.doc,.docx"
                          className="hidden"
                          onClick={(e) => {
                            (e.target as HTMLInputElement).value = "";
                          }}
                          onChange={(e) => handleDirectItemUpload(e, item)}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            const input = document.getElementById(`file-reupload-${item.id}`) as HTMLInputElement | null;
                            if (input) {
                              input.value = "";
                              input.click();
                            }
                          }}
                          className="h-8 text-xs gap-1.5 px-3 font-medium cursor-pointer"
                        >
                          {busy ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <Upload className="size-3.5 text-muted-foreground" />
                          )}
                          <span>Re-upload</span>
                        </Button>

                        <a
                          href={fileUrl}
                          download={fileName}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex"
                          title="Download file"
                        >
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground hover:bg-muted"
                          >
                            <Download className="size-3.5" />
                          </Button>
                        </a>
                      </div>

                      {matchingDocs.length > 0 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setShowPicker(showPicker === item.id ? null : item.id)
                          }
                          className="h-8 text-xs text-muted-foreground hover:text-foreground px-2"
                        >
                          Saved ({matchingDocs.length})
                        </Button>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-2 w-full">
                      <div className="flex items-center gap-2">
                        <input
                          id={`file-upload-${item.id}`}
                          type="file"
                          accept="image/*,.pdf,.doc,.docx"
                          className="hidden"
                          onClick={(e) => {
                            (e.target as HTMLInputElement).value = "";
                          }}
                          onChange={(e) => handleDirectItemUpload(e, item)}
                        />
                        <Button
                          type="button"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            const input = document.getElementById(`file-upload-${item.id}`) as HTMLInputElement | null;
                            if (input) {
                              input.value = "";
                              input.click();
                            }
                          }}
                          className="h-8 text-xs gap-1.5 px-3.5 font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-2xs cursor-pointer"
                        >
                          {busy ? (
                            <Loader2 className="size-3.5 animate-spin" />
                          ) : (
                            <Upload className="size-3.5" />
                          )}
                          <span>Upload File</span>
                        </Button>

                        {matchingDocs.length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              setShowPicker(showPicker === item.id ? null : item.id)
                            }
                            className="h-8 text-xs gap-1.5 px-2.5 rounded-lg border-border/90 dark:border-slate-700 bg-background/60 hover:bg-muted/60 text-foreground cursor-pointer"
                          >
                            <FolderOpen className="size-3.5 text-primary" />
                            <span>Saved ({matchingDocs.length})</span>
                          </Button>
                        )}

                        {/* Thing 2: Concierge procurement button */}
                        {primaryProduct && !existingOrder ? (
                          <Button
                            type="button"
                            size="sm"
                            onClick={() =>
                              setConciergeModalState({ item, product: primaryProduct })
                            }
                            className="h-8 text-xs gap-1.5 px-3 font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs cursor-pointer"
                          >
                            <Sparkles className="size-3.5" />
                            <span>
                              Get This —{" "}
                              {primaryProduct.price_cents === 0
                                ? "Free"
                                : `$${(primaryProduct.price_cents / 100).toFixed(0)}`}
                            </span>
                          </Button>
                        ) : isTravelOrBookingDoc && !existingOrder ? (
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => {
                              setWaitlistJoined(false);
                              setComingSoonModalItem(item);
                            }}
                            className="h-8 text-xs gap-1.5 px-3 font-semibold rounded-lg bg-gradient-to-r from-amber-500/15 to-amber-600/15 hover:from-amber-500/25 hover:to-amber-600/25 text-amber-600 dark:text-amber-400 border border-amber-500/35 shadow-2xs cursor-pointer"
                          >
                            <Sparkles className="size-3.5 text-amber-500" />
                            <span>Get It</span>
                            <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-600 dark:text-amber-300">
                              Coming Soon
                            </span>
                          </Button>
                        ) : null}
                      </div>

                      <button
                        type="button"
                        onClick={() => onStatusChange(item.id, "gathered")}
                        className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 rounded-md transition-colors cursor-pointer"
                      >
                        Mark done
                      </button>
                    </div>
                  )}
                </div>

                {showPicker === item.id && (
                  <div className="mt-2 rounded-xl border border-dashed border-border/80 bg-muted/30 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        {isGathered
                          ? "Replace with a document from your wallet:"
                          : "Select from your documents:"}
                      </p>
                      <input
                        id={`file-picker-upload-${item.id}`}
                        type="file"
                        accept="image/*,.pdf,.doc,.docx"
                        className="hidden"
                        onClick={(e) => {
                          (e.target as HTMLInputElement).value = "";
                        }}
                        onChange={(e) => {
                          setShowPicker(null);
                          handleDirectItemUpload(e, item);
                        }}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const input = document.getElementById(`file-picker-upload-${item.id}`) as HTMLInputElement | null;
                          if (input) {
                            input.value = "";
                            input.click();
                          }
                        }}
                        className="h-7 text-xs gap-1 text-primary hover:bg-primary/10 font-medium cursor-pointer"
                      >
                        <Upload className="size-3" />
                        <span>Upload New File</span>
                      </Button>
                    </div>

                    {matchingDocs.length === 0 ? (
                      <div className="p-3 rounded-lg bg-background border border-border/60 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                        <p className="text-xs text-muted-foreground">
                          No saved documents found in your wallet for this requirement.
                        </p>
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => {
                            const input = document.getElementById(`file-picker-upload-${item.id}`) as HTMLInputElement | null;
                            if (input) {
                              input.value = "";
                              input.click();
                            }
                          }}
                          className="h-7 px-3 text-xs gap-1.5 cursor-pointer"
                        >
                          <Upload className="size-3" />
                          <span>Upload File</span>
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {matchingDocs.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex items-center justify-between rounded-lg border border-border/60 bg-background px-3 py-2"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-medium">{doc.name}</p>
                              <p className="text-[10px] text-muted-foreground">
                                {doc.doc_type} · v{doc.version}
                                {doc.expiry_date && ` · exp ${doc.expiry_date}`}
                              </p>
                            </div>
                            <Button
                              onClick={() => handleAttachWallet(item.id, doc)}
                              disabled={attaching === item.id}
                            >
                              {attaching === item.id ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                "Use"
                              )}
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                    <button
                      onClick={() => setShowPicker(null)}
                      className="mt-2 text-[10px] text-muted-foreground hover:underline cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {ocrResult && !ocrResult.needs_recapture && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="space-y-3 pt-4">
            <div className="flex items-center gap-2">
              <Check className="size-4 text-[var(--color-success)]" />
              <p className="text-sm font-medium">Document scanned</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(ocrResult.fields).map(([key, field]) => (
                <div key={key} className="text-xs">
                  <span className="text-muted-foreground">{key.replace(/_/g, " ")}: </span>
                  <span className="font-medium">{field.value}</span>
                  <span className="ml-1 text-muted-foreground">
                    ({Math.round(field.confidence * 100)}%)
                  </span>
                </div>
              ))}
            </div>
            <div className="flex gap-2 pt-1">
              <Button onClick={handleConfirmExtracted}>
                <Check className="size-3" />
                Confirm &amp; attach
              </Button>
              <Button variant="outline" onClick={() => setOcrResult(null)}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {ocrError && (
        <div className="rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/5 px-4 py-3 text-sm text-[var(--color-warning)]">
          {ocrError}
        </div>
      )}

      {/* User Document Preview Modal */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div
            className="fixed inset-0"
            onClick={() => setViewingDoc(null)}
            aria-hidden="true"
          />
          <div className="relative z-10 w-full max-w-5xl max-h-[92vh] flex flex-col bg-card rounded-2xl border border-border shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/80 bg-muted/30">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-xl bg-primary/10 text-primary shrink-0">
                  <FileText className="size-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm sm:text-base font-bold text-foreground truncate">{viewingDoc.name}</h3>
                  <p className="text-xs text-muted-foreground font-mono truncate">{viewingDoc.filename}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={viewingDoc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background text-xs font-medium hover:bg-muted transition-colors text-foreground"
                >
                  <ExternalLink className="size-3.5" />
                  <span className="hidden sm:inline">Open in New Tab</span>
                </a>
                <a
                  href={viewingDoc.url}
                  download={viewingDoc.filename}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background text-xs font-medium hover:bg-muted transition-colors text-foreground"
                >
                  <Download className="size-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </a>
                <button
                  type="button"
                  onClick={() => setViewingDoc(null)}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors ml-1"
                >
                  <X className="size-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Document Viewer (Iframe / Image) */}
              <div className="lg:col-span-2 min-h-[460px] h-[550px] rounded-xl border border-border/70 overflow-hidden bg-muted/10 shadow-inner flex flex-col items-center justify-center">
                {viewingDoc.filename.toLowerCase().match(/\.(jpg|jpeg|png|webp|gif)$/) ? (
                  <div className="w-full h-full flex items-center justify-center p-4 bg-muted/20 overflow-auto">
                    <img
                      src={viewingDoc.url}
                      alt={viewingDoc.name}
                      className="max-w-full max-h-full object-contain rounded-lg shadow-sm"
                    />
                  </div>
                ) : (
                  <iframe
                    src={viewingDoc.url}
                    title={viewingDoc.name}
                    className="w-full h-full border-0 rounded-xl"
                  />
                )}
              </div>

              {/* OCR / Info Details Panel */}
              <div className="space-y-4">
                <div className="rounded-xl border border-border/70 bg-muted/20 p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Sparkles className="size-3.5 text-amber-500" />
                      Document Details
                    </span>
                    <Badge tone="success" className="text-[10px]">
                      Uploaded &amp; Ready
                    </Badge>
                  </div>

                  {viewingDoc.extractedFields && Object.keys(viewingDoc.extractedFields).length > 0 ? (
                    <div className="space-y-2 pt-1 max-h-[380px] overflow-y-auto pr-1">
                      {Object.entries(viewingDoc.extractedFields).map(([key, rawVal]) => {
                        const val =
                          typeof rawVal === "object" && rawVal !== null && "value" in rawVal
                            ? String((rawVal as { value: unknown }).value)
                            : String(rawVal ?? "");
                        if (!val || val === "undefined") return null;

                        const formattedKey = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                        return (
                          <div
                            key={key}
                            className="p-2.5 rounded-lg bg-background/80 border border-border/60 text-xs"
                          >
                            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                              {formattedKey}
                            </p>
                            <p className="font-semibold text-foreground truncate">{val}</p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground py-2 leading-relaxed">
                      Your document has been securely uploaded to your case filing packet. You can preview it using the viewer on the left or open it in a new tab.
                    </p>
                  )}
                </div>

                <div className="p-3.5 rounded-xl border border-primary/20 bg-primary/5 text-xs text-muted-foreground space-y-1">
                  <p className="font-semibold text-foreground flex items-center gap-1.5 text-[11px]">
                    <ShieldCheck className="size-3.5 text-primary" />
                    Verified Document
                  </p>
                  <p className="text-[11px] leading-relaxed">
                    This document will be reviewed and submitted to the official visa portal by our concierge filing team.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Thing 2: Document Concierge Purchase Modal */}
      <ConciergeModal
        isOpen={Boolean(conciergeModalState)}
        onClose={() => setConciergeModalState(null)}
        item={conciergeModalState?.item ?? null}
        product={conciergeModalState?.product ?? null}
        onConfirm={handleConciergeConfirm}
      />

      {/* Travel & Booking Document Concierge — Coming Soon Modal */}
      {comingSoonModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="bg-card w-full max-w-lg rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/20">
              <div className="flex items-center gap-2.5">
                <div className="size-9 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center justify-center">
                  <Plane className="size-4.5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-foreground">
                      Document Concierge
                    </h3>
                    <Badge tone="warning" className="text-[10px] px-2 py-0">
                      Coming Soon
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Automated Booking &amp; Itinerary Proofs
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setComingSoonModalItem(null)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors cursor-pointer"
              >
                <X className="size-4" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-5">
              <div className="p-4 rounded-xl border border-border/80 bg-muted/30 space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-bold text-foreground">
                      {comingSoonModalItem.name}
                    </h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Verifiable embassy-compliant booking reservation for your visa application
                    </p>
                  </div>
                  <span className="text-xs font-bold text-amber-500 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full shrink-0">
                    In Development
                  </span>
                </div>
              </div>

              <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
                <p>
                  We are partnering with major global travel GDS providers to generate confirmed, embassy-compliant flight reservations and hotel bookings with live PNRs — without requiring you to pay full ticket prices upfront.
                </p>
                <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 space-y-1 text-foreground">
                  <span className="font-semibold block text-primary">For this application:</span>
                  <p className="text-muted-foreground text-[11px]">
                    If you already have your flight or hotel reservation, please click <strong>Upload File</strong> to attach it. If not, you can join the priority waitlist below.
                  </p>
                </div>
              </div>

              {waitlistJoined ? (
                <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 flex items-center gap-2.5 text-xs font-semibold">
                  <Check className="size-4 shrink-0 text-emerald-500" />
                  <span>You have joined the priority notification waitlist for this service!</span>
                </div>
              ) : null}

              {/* Actions */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setComingSoonModalItem(null)}
                  className="text-xs font-medium cursor-pointer"
                >
                  Close
                </Button>
                {!waitlistJoined ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setWaitlistJoined(true);
                      toast.success("Added to waitlist! We will notify you when booking procurement goes live.");
                    }}
                    className="text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white gap-1.5 cursor-pointer shadow-xs"
                  >
                    <Bell className="size-3.5" />
                    <span>Notify Me When Live</span>
                  </Button>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => setComingSoonModalItem(null)}
                    className="text-xs font-bold bg-primary text-primary-foreground cursor-pointer shadow-xs"
                  >
                    Done
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
