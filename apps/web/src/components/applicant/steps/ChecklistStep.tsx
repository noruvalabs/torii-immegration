"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Check, Upload, Loader2, Camera, ExternalLink, FolderOpen, ShieldCheck } from "lucide-react";
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
  if (code.includes("passport") && !code.includes("photo")) return "passport";
  if (code.includes("residence") || code.includes("card")) return "residence_card";
  if (
    code.includes("fund") ||
    code.includes("bank") ||
    code.includes("financial") ||
    code.includes("finance") ||
    code.includes("sponsor")
  ) {
    return "proof_of_funds";
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
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [attaching, setAttaching] = useState<number | null>(null);
  const [showPicker, setShowPicker] = useState<number | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [autoAttached, setAutoAttached] = useState(false);
  const [mode, setMode] = useState<"upload" | "scan" | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingItemRef = useRef<ChecklistItem | null>(null);
  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  useEffect(() => {
    if (!token) return;
    getWallet(token).then(setWalletDocs).catch(() => {});
  }, [token]);

  // Auto-attach matching wallet docs once when checklist + wallet are ready.
  useEffect(() => {
    if (!token || autoAttached || items.length === 0 || walletDocs.length === 0) return;

    const snapshot = items.filter((i) => i.status === "needed");
    if (snapshot.length === 0) {
      setAutoAttached(true);
      return;
    }

    let cancelled = false;
    void (async () => {
      for (const item of snapshot) {
        if (cancelled) return;
        const matches = walletDocs.filter(
          (d) => d.status === "active" && matchWalletToChecklist(d, item.code),
        );
        const match = matches[0];
        if (!match) continue;
        try {
          await registerDocument(token, caseId, {
            doc_type: match.doc_type,
            filename: match.filename,
            storage_key: `wallet/${match.id}`,
            extracted_fields: {},
            content_type: match.content_type,
          });
          if (!cancelled) await onStatusChangeRef.current(item.id, "gathered");
        } catch {
          // Skip individual failures; user can attach manually.
        }
      }
      if (!cancelled) setAutoAttached(true);
    })();

    return () => {
      cancelled = true;
    };
  }, [token, caseId, walletDocs, items, autoAttached]);

  // Reset auto-attach when checklist is regenerated (item ids change).
  const itemKey = items.map((i) => i.id).join(",");
  const prevItemKey = useRef(itemKey);
  useEffect(() => {
    if (prevItemKey.current !== itemKey) {
      prevItemKey.current = itemKey;
      setAutoAttached(false);
    }
  }, [itemKey]);

  function getMatchingWalletDocs(checklistCode: string): WalletDocument[] {
    return walletDocs.filter(
      (d) => d.status === "active" && matchWalletToChecklist(d, checklistCode),
    );
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

    try {
      if (mode === "upload") {
        // Direct upload: store in case + wallet without requiring OCR success.
        await registerDocument(token, caseId, {
          doc_type: mapDocType(item.code),
          filename: file.name,
          storage_key: `upload/${item.id}/${file.name}`,
          extracted_fields: {},
          content_type: file.type || "application/octet-stream",
        });
        try {
          await uploadDocument(token, file, mapDocType(item.code), item.name);
          const refreshed = await getWallet(token);
          setWalletDocs(refreshed);
        } catch {
          // Wallet is optional
        }
        await onStatusChange(item.id, "gathered");
      } else {
        // Scan path: OCR then confirm extracted fields.
        setOcrLoading(true);
        const docType = mapDocType(item.code);
        const result = await extractFromFile(file, docType);
        setOcrResult(result);
        if (result.needs_recapture) {
          setOcrError("Could not extract fields. Try a clearer image, use Upload, or mark gathered.");
        }
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
      setOcrResult(null);
    } catch (err) {
      setOcrError(err instanceof Error ? err.message : "Registration failed");
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
        <div className="space-y-3">
          {items.map((item) => {
            const url = citationUrl(item.citation);
            const version = citationVersion(item.citation);
            const matchingDocs = getMatchingWalletDocs(item.code);
            const isGathered = item.status !== "needed";
            const busy = uploading === item.id || attaching === item.id;

            return (
              <div
                key={item.id}
                className="rounded-[var(--radius)] border p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    {isGathered ? (
                      <Check className="size-4 text-[var(--color-success)]" />
                    ) : matchingDocs.length > 0 ? (
                      <div className="size-4 rounded-full border-2 border-primary bg-primary/20" />
                    ) : (
                      <div className="size-4 rounded border border-muted-foreground/30" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">{item.name}</p>
                      {item.is_required && <Badge tone="danger">Required</Badge>}
                      {isGathered && <Badge tone="success">Gathered</Badge>}
                      {!isGathered && matchingDocs.length > 0 && (
                        <Badge tone="default">In your documents</Badge>
                      )}
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
                        <FolderOpen className="size-3" />
                        Use saved ({matchingDocs.length})
                      </button>
                    )}
                    {!isGathered && (
                      <>
                        <button
                          onClick={() => handleUploadClick(item)}
                          disabled={busy}
                          className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-primary hover:bg-accent disabled:opacity-50"
                        >
                          {busy && mode === "upload" ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <Upload className="size-3" />
                          )}
                          Upload
                        </button>
                        <button
                          onClick={() => handleScanClick(item)}
                          disabled={busy || ocrLoading}
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
                      {isGathered ? "Replace with a document from your wallet:" : "Select from your documents:"}
                    </p>
                    {matchingDocs.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        No matching documents yet. Use Upload or Scan, or add docs under Documents.
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
