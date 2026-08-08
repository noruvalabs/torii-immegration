"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FileText,
  Upload,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Plus,
  Loader2,
  FolderOpen,
  ShieldCheck,
  Calendar,
  ImageIcon,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { formatErrorMessage } from "@/lib/api/errors";
import {
  getWallet,
  uploadDocument,
  deleteDocument,
  getDocumentTypes,
  getWalletSummary,
  type WalletDocument,
  type WalletSummary,
  type DocumentType,
} from "@/lib/api/wallet";

const DEFAULT_DOC_TYPES: DocumentType[] = [
  { code: "passport", name: "Valid Passport", category: "identity" },
  { code: "photo", name: "Photograph / Passport Photo", category: "identity" },
  { code: "bank_statement", name: "Bank Statement", category: "financial" },
  { code: "proof_of_funds", name: "Proof of Funds / Bank Statement", category: "financial" },
  { code: "flight_itinerary", name: "Flight Itinerary", category: "travel" },
  { code: "travel_itinerary", name: "Travel Itinerary", category: "travel" },
  { code: "employment_letter", name: "Employment Letter", category: "employment" },
  { code: "employment_contract", name: "Employment Contract / Job Letter", category: "employment" },
  { code: "residence_card", name: "Residence Card / National ID", category: "immigration" },
  { code: "tax_return", name: "Tax Return / Financial Declaration", category: "financial" },
  { code: "other", name: "Other Supporting Document", category: "support" },
];

export default function DocumentVaultPage() {
  const { token } = useAuth();
  const [documents, setDocuments] = useState<WalletDocument[]>([]);
  const [summary, setSummary] = useState<WalletSummary | null>(null);
  const [docTypes, setDocTypes] = useState<DocumentType[]>(DEFAULT_DOC_TYPES);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload Form state
  const [selectedType, setSelectedType] = useState("passport");
  const [docName, setDocName] = useState("");
  const [issuedDate, setIssuedDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const loadVault = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [docs, sumRes, typesRes] = await Promise.all([
        getWallet(token).catch(() => []),
        getWalletSummary(token).catch(() => null),
        getDocumentTypes(token).catch(() => ({ document_types: DEFAULT_DOC_TYPES })),
      ]);
      setDocuments(docs);
      setSummary(sumRes);
      if (typesRes?.document_types?.length) {
        setDocTypes(typesRes.document_types);
      }
    } catch {
      setError("Failed to load documents.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadVault();
  }, [loadVault]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }
    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const matchedType = docTypes.find((t) => t.code === selectedType);
      const nameToUse = docName.trim() || matchedType?.name || selectedType;
      await uploadDocument(
        token,
        file,
        selectedType,
        nameToUse,
        issuedDate || undefined,
        expiryDate || undefined
      );
      setSuccessMsg(`"${nameToUse}" saved to Document Vault successfully.`);
      setFile(null);
      setDocName("");
      setIssuedDate("");
      setExpiryDate("");
      await loadVault();
    } catch (err) {
      setError(formatErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId: number, name: string) {
    if (!confirm(`Remove "${name}" from your Document Vault?`)) return;
    setError(null);
    try {
      await deleteDocument(docId, token);
      setSuccessMsg(`Document "${name}" removed.`);
      await loadVault();
    } catch (err) {
      setError(formatErrorMessage(err));
    }
  }

  const categories = ["All", ...Array.from(new Set(docTypes.map((t) => t.category)))];

  const filteredDocs = documents.filter((doc) => {
    if (activeCategory === "All") return true;
    const typeObj = docTypes.find((t) => t.code === doc.doc_type);
    return typeObj?.category === activeCategory;
  });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Document Vault</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Store common visa documents once. Torii automatically reuses them across all present and future applications.
          </p>
        </div>
        <Badge tone="success" className="w-fit">
          <ShieldCheck className="mr-1 size-3.5" /> Reusable Profile Storage
        </Badge>
      </div>

      {error && (
        <div className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/10 px-4 py-3 text-sm text-[var(--color-success)] flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-xs font-semibold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="flex items-center gap-4 pt-5">
            <div className="flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
              <FolderOpen className="size-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Total Documents</p>
              <p className="text-2xl font-bold">{summary?.total_documents ?? documents.length}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 pt-5">
            <div className="flex size-10 items-center justify-center rounded-full bg-[var(--color-success)]/10 text-[var(--color-success)]">
              <CheckCircle2 className="size-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Active &amp; Ready</p>
              <p className="text-2xl font-bold">
                {documents.filter((d) => d.status === "active").length}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4 pt-5">
            <div className="flex size-10 items-center justify-center rounded-full bg-[var(--color-warning)]/10 text-[var(--color-warning)]">
              <Clock className="size-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Expiring Soon</p>
              <p className="text-2xl font-bold">{summary?.expiring_soon?.length ?? 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Upload Form */}
      <Card>
        <CardContent className="pt-6">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <Plus className="size-4 text-primary" /> Add New Document to Vault
          </h2>
          <form onSubmit={handleUpload} className="mt-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Document Type *
                </label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {docTypes.map((t) => (
                    <option key={t.code} value={t.code}>
                      {t.name} ({t.category})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Display Name / Label
                </label>
                <input
                  type="text"
                  placeholder="e.g. Primary Passport (2024-2034)"
                  value={docName}
                  onChange={(e) => setDocName(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Issue Date (Optional)
                </label>
                <input
                  type="date"
                  value={issuedDate}
                  onChange={(e) => setIssuedDate(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Expiry Date (Optional)
                </label>
                <input
                  type="date"
                  value={expiryDate}
                  onChange={(e) => setExpiryDate(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">
                Select File (PNG, JPG, WEBP, PDF, DOC, DOCX) *
              </label>
              <input
                type="file"
                accept="image/*,.pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full rounded-[var(--radius)] border bg-background px-3 py-1.5 text-sm file:mr-4 file:rounded file:border-0 file:bg-accent file:px-3 file:py-1 file:text-xs file:font-medium hover:file:bg-accent/80"
              />
              {file && file.type.startsWith("image/") && (
                <div className="mt-2 flex items-center gap-2 rounded border bg-muted/40 p-2 text-xs">
                  <ImageIcon className="size-4 text-primary shrink-0" />
                  <span className="font-medium text-foreground truncate">{file.name}</span>
                  <Badge tone="success" className="ml-auto text-[10px]">Image file detected</Badge>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={uploading}>
                {uploading ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" /> Saving...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 size-4" /> Save to Vault
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Vault Document List */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Your Saved Documents</h2>
          <div className="flex flex-wrap gap-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`rounded-[var(--radius)] px-3 py-1 text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? "bg-primary text-primary-foreground"
                    : "bg-accent/50 text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex py-12 justify-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredDocs.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FolderOpen className="mx-auto size-10 text-muted-foreground/40 mb-3" />
              <p className="text-sm font-medium">No documents in vault yet</p>
              <p className="text-xs text-muted-foreground mt-1">
                Upload your passport photo, passport scan, bank statements, or itinerary above to auto-satisfy visa requirements.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {filteredDocs.map((doc) => {
              const matchedType = docTypes.find((t) => t.code === doc.doc_type);
              const category = matchedType?.category || "Document";
              const isImage =
                doc.content_type?.startsWith("image/") ||
                /\.(png|jpg|jpeg|webp|gif)$/i.test(doc.filename);

              return (
                <Card key={doc.id} className="relative transition-all hover:border-primary/40">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                          {isImage ? <ImageIcon className="size-5" /> : <FileText className="size-5" />}
                        </div>
                        <div>
                          <p className="text-sm font-semibold tracking-tight">{doc.name}</p>
                          <p className="text-[11px] text-muted-foreground">
                            {doc.doc_type} · v{doc.version} {isImage ? "· Image" : ""}
                          </p>
                        </div>
                      </div>
                      <Badge tone="muted" className="text-[10px]">
                        {category}
                      </Badge>
                    </div>

                    <div className="rounded border bg-muted/30 p-2.5 space-y-1 text-xs">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Filename:</span>
                        <span className="font-mono text-foreground truncate max-w-[180px]">
                          {doc.filename}
                        </span>
                      </div>
                      {doc.expiry_date && (
                        <div className="flex items-center justify-between text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3" /> Expiry:
                          </span>
                          <span className="font-medium text-foreground">{doc.expiry_date}</span>
                        </div>
                      )}
                      {doc.created_at && (
                        <div className="flex items-center justify-between text-muted-foreground">
                          <span>Added:</span>
                          <span className="text-muted-foreground">
                            {new Date(doc.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <Badge tone="success" className="text-[10px]">
                        <CheckCircle2 className="mr-1 size-3" /> Ready for reuse
                      </Badge>
                      <Button
                        variant="ghost"
                        onClick={() => handleDelete(doc.id, doc.name)}
                        className="h-7 text-xs text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 px-2"
                      >
                        <Trash2 className="size-3.5 mr-1" /> Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
