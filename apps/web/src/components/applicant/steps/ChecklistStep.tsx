"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Upload, Loader2, Camera, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { registerDocument } from "@/lib/api/cases";
import { extractFromFile, type OCRResult, type DocumentType } from "@/lib/api/ocr";
import { getWallet, uploadDocument, type WalletDocument } from "@/lib/api/wallet";
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
  if (code.includes("passport")) return "passport";
  if (code.includes("residence") || code.includes("card")) return "residence_card";
  return "employment_contract";
}

function matchWalletToChecklist(walletDoc: WalletDocument, checklistCode: string): boolean {
  const docType = walletDoc.doc_type.toLowerCase();
  const code = checklistCode.toLowerCase();
  if (code.includes("passport") && docType.includes("passport")) return true;
  if ((code.includes("residence") || code.includes("card")) && docType.includes("residence")) return true;
  if (code.includes("employment") && docType.includes("employment")) return true;
  return docType === code;
}

export function ChecklistStep({
  items,
  caseId,
  loading,
  onRefresh,
  onStatusChange,
}: ChecklistStepProps) {
  const { token } = useAuth();
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [attaching, setAttaching] = useState<number | null>(null);
  const [showPicker, setShowPicker] = useState<number | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingItemRef = useRef<ChecklistItem | null>(null);

  useEffect(() => {
    if (!token) return;
    getWallet().then(setWalletDocs).catch(() => {});
  }, [token]);

  function getMatchingWalletDocs(checklistCode: string): WalletDocument[] {
    return walletDocs.filter((d) => d.status === "active" && matchWalletToChecklist(d, checklistCode));
  }

  async function handleAttachWallet(itemId: number, walletDoc: WalletDocument) {
    if (!token) return;
    setAttaching(itemId);
    try {
      await registerDocument(token, caseId, {
        doc_type: walletDoc.doc_type,
        filename: walletDoc.filename,
        storage_key: `wallet/${walletDoc.id}`,
        extracted_fields: {},
        content_type: walletDoc.content_type,
      });
      await onStatusChange(itemId, "gathered");
      setShowPicker(null);
    } catch {
    } finally {
      setAttaching(null);
    }
  }

  function handleUploadClick(item: ChecklistItem) {
    pendingItemRef.current = item;
    setOcrResult(null);
    setOcrError(null);
    fileInputRef.current?.click();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const item = pendingItemRef.current;
    if (!file || !item || !token) return;

    setOcrLoading(true);
    setOcrError(null);
    setUploading(item.id);

    try {
      const docType = mapDocType(item.code);
      const result = await extractFromFile(file, docType);
      setOcrResult(result);

      if (result.needs_recapture) {
        setOcrError("Could not extract fields. Try a clearer image or mark gathered manually.");
      }
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "OCR failed");
    } finally {
      setOcrLoading(false);
      setUploading(null);
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
        await uploadDocument(file, mapDocType(item.code), item.name);
      } catch {
        // Wallet upload is optional
      }

      await onStatusChange(item.id, "gathered");
      setOcrResult(null);
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="space-y-6">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">Document checklist</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {items.filter((i) => i.status !== "needed").length} of {items.length} gathered — reuse
            uploaded docs or scan new ones.
          </p>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={loading}>
          {items.length === 0 ? "Generate checklist" : "Refresh"}
        </Button>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No checklist items yet. Generate your personalized list after eligibility.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const url = citationUrl(item.citation);
            const version = citationVersion(item.citation);
            const matchingDocs = getMatchingWalletDocs(item.code);
            const isGathered = item.status !== "needed";

            return (
              <div
                key={item.id}
                className="rounded-[var(--radius)] border p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {isGathered ? (
                      <Check className="size-4 text-[var(--color-success)]" />
                    ) : (
                      <div className="size-4 rounded border border-muted-foreground/30" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">{item.name}</p>
                      {item.is_required && <Badge tone="danger">Required</Badge>}
                      {isGathered && <Badge tone="success">Gathered</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">How: </span>
                      {item.how_to_obtain}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">Why: </span>
                      {item.why_required}
                    </p>
                    {url && (
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        Official source{version ? ` (${version})` : ""} <ExternalLink className="size-3" />
                      </a>
                    )}
                  </div>
                  <div className="flex flex-col gap-1">
                    {!isGathered && matchingDocs.length > 0 && (
                      <button
                        onClick={() => setShowPicker(showPicker === item.id ? null : item.id)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-accent"
                      >
                        <Upload className="size-3" />
                        Reuse ({matchingDocs.length})
                      </button>
                    )}
                    {!isGathered && (
                      <>
                        <button
                          onClick={() => handleUploadClick(item)}
                          disabled={ocrLoading && uploading === item.id}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-accent disabled:opacity-50"
                        >
                          {ocrLoading && uploading === item.id ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Camera className="size-3" />
                          )}
                          Scan
                        </button>
                        <button
                          onClick={() => onStatusChange(item.id, "gathered")}
                          className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                        >
                          Mark gathered
                        </button>
                      </>
                    )}
                    {isGathered && (
                      <button
                        onClick={() => setShowPicker(showPicker === item.id ? null : item.id)}
                        className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
                      >
                        Change
                      </button>
                    )}
                  </div>
                </div>

                {showPicker === item.id && (
                  <div className="mt-3 rounded-[var(--radius)] border border-dashed bg-muted/30 p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">
                      {isGathered ? "Replace with:" : "Select from your documents:"}
                    </p>
                    {matchingDocs.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        No matching documents in your wallet. Upload a new one.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {matchingDocs.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex items-center justify-between rounded border bg-background px-3 py-2"
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
                      className="mt-2 text-[10px] text-muted-foreground hover:underline"
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
    </div>
  );
}
