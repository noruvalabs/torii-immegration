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
  Eye,
  Edit2,
  RefreshCw,
  X,
  History,
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
  getDocumentVersions,
  patchWalletDocument,
  type WalletDocument,
  type WalletSummary,
  type DocumentType,
  type DocumentVersion,
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

function formatBytes(bytes?: number | null) {
  if (!bytes) return "Unknown size";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

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

  // Interactive Modals state
  const [viewingDoc, setViewingDoc] = useState<WalletDocument | null>(null);
  const [docVersions, setDocVersions] = useState<DocumentVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);

  const [updatingDoc, setUpdatingDoc] = useState<WalletDocument | null>(null);
  const [updateFile, setUpdateFile] = useState<File | null>(null);
  const [updateName, setUpdateName] = useState("");
  const [updateIssuedDate, setUpdateIssuedDate] = useState("");
  const [updateExpiryDate, setUpdateExpiryDate] = useState("");
  const [updateNotes, setUpdateNotes] = useState("");
  const [savingUpdate, setSavingUpdate] = useState(false);

  const [editingDoc, setEditingDoc] = useState<WalletDocument | null>(null);
  const [editName, setEditName] = useState("");
  const [editIssuedDate, setEditIssuedDate] = useState("");
  const [editExpiryDate, setEditExpiryDate] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  const loadVault = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [docs, sumRes, typesRes] = await Promise.all([
        getWallet(token).catch((err) => {
          console.error("Failed to load wallet docs:", err);
          return [] as WalletDocument[];
        }),
        getWalletSummary(token).catch(() => null),
        getDocumentTypes(token).catch(() => ({ document_types: DEFAULT_DOC_TYPES })),
      ]);

      let resolvedDocs = docs;
      if ((!resolvedDocs || resolvedDocs.length === 0) && sumRes?.documents_by_category) {
        resolvedDocs = Object.values(sumRes.documents_by_category).flat() as WalletDocument[];
      }

      setDocuments(resolvedDocs || []);
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

  // Open View Modal & fetch version history
  async function handleOpenView(doc: WalletDocument) {
    setViewingDoc(doc);
    setLoadingVersions(true);
    try {
      const versions = await getDocumentVersions(doc.id, token);
      setDocVersions(versions);
    } catch {
      setDocVersions([]);
    } finally {
      setLoadingVersions(false);
    }
  }

  // Open Update Modal
  function handleOpenUpdate(doc: WalletDocument) {
    setUpdatingDoc(doc);
    setUpdateFile(null);
    setUpdateName(doc.name);
    setUpdateIssuedDate(doc.issued_date || "");
    setUpdateExpiryDate(doc.expiry_date || "");
    setUpdateNotes("");
  }

  // Open Edit Metadata Modal
  function handleOpenEdit(doc: WalletDocument) {
    setEditingDoc(doc);
    setEditName(doc.name);
    setEditIssuedDate(doc.issued_date || "");
    setEditExpiryDate(doc.expiry_date || "");
  }

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

  async function handleSaveNewVersion(e: React.FormEvent) {
    e.preventDefault();
    if (!updatingDoc) return;
    if (!updateFile) {
      setError("Please select a replacement file to upload as a new version.");
      return;
    }
    setSavingUpdate(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const nameToUse = updateName.trim() || updatingDoc.name;
      await uploadDocument(
        token,
        updateFile,
        updatingDoc.doc_type,
        nameToUse,
        updateIssuedDate || undefined,
        updateExpiryDate || undefined,
        updateNotes || undefined
      );
      setSuccessMsg(`New version for "${nameToUse}" saved successfully (v${updatingDoc.version + 1}).`);
      setUpdatingDoc(null);
      await loadVault();
    } catch (err) {
      setError(formatErrorMessage(err));
    } finally {
      setSavingUpdate(false);
    }
  }

  async function handleSaveMetadata(e: React.FormEvent) {
    e.preventDefault();
    if (!editingDoc) return;
    setSavingEdit(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await patchWalletDocument(
        editingDoc.id,
        {
          name: editName.trim() || editingDoc.name,
          issued_date: editIssuedDate || undefined,
          expiry_date: editExpiryDate || undefined,
        },
        token
      );
      setSuccessMsg(`Document details updated for "${editName}".`);
      setEditingDoc(null);
      await loadVault();
    } catch (err) {
      setError(formatErrorMessage(err));
    } finally {
      setSavingEdit(false);
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
    if (activeCategory === "All" || activeCategory === "all") return true;
    const typeObj = docTypes.find(
      (t) => t.code === doc.doc_type || t.name.toLowerCase() === doc.doc_type.toLowerCase()
    );
    const docCategory = typeObj?.category || (doc as unknown as { category?: string }).category;
    return docCategory?.toLowerCase() === activeCategory.toLowerCase();
  });

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
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
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
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
              <div className="flex items-center gap-3">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-xs file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
                />
              </div>
              {file && (
                <div className="mt-2 flex items-center gap-2 rounded bg-muted/40 p-2 text-xs text-muted-foreground">
                  <ImageIcon className="size-4 text-primary shrink-0" />
                  <span className="font-medium text-foreground truncate">{file.name}</span>
                  <span className="text-[11px]">({formatBytes(file.size)})</span>
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
                <Card key={doc.id} className="relative transition-all hover:border-primary/40 flex flex-col justify-between">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                          {isImage ? <ImageIcon className="size-5" /> : <FileText className="size-5" />}
                        </div>
                        <div>
                          <p className="text-sm font-semibold tracking-tight">{doc.name}</p>
                          <p className="text-[11px] text-muted-foreground">
                            {doc.doc_type} · <span className="font-semibold text-primary">v{doc.version}</span> {isImage ? "· Image" : ""}
                          </p>
                        </div>
                      </div>
                      <Badge tone="muted" className="text-[10px]">
                        {category}
                      </Badge>
                    </div>

                    <div className="rounded border bg-muted/30 p-2.5 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>File:</span>
                        <span className="font-mono text-foreground truncate max-w-[180px]" title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Size:</span>
                        <span className="font-medium text-foreground">{formatBytes(doc.file_size)}</span>
                      </div>
                      {doc.expiry_date && (
                        <div className="flex items-center justify-between text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3" /> Expiry:
                          </span>
                          <span className="font-medium text-foreground">{doc.expiry_date}</span>
                        </div>
                      )}
                    </div>

                    {/* Action buttons bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t">
                      <div className="flex items-center gap-1.5">
                        <Button
                          variant="outline"
                          onClick={() => handleOpenView(doc)}
                          className="h-7 text-xs gap-1 px-2.5"
                          title="View details and version history"
                        >
                          <Eye className="size-3" /> View
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => handleOpenUpdate(doc)}
                          className="h-7 text-xs gap-1 px-2.5 text-primary border-primary/30 hover:bg-primary/10"
                          title="Upload a new version of this file"
                        >
                          <RefreshCw className="size-3" /> Update
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => handleOpenEdit(doc)}
                          className="h-7 text-xs gap-1 px-2 text-muted-foreground hover:text-foreground"
                          title="Edit display name or dates"
                        >
                          <Edit2 className="size-3" /> Edit
                        </Button>
                      </div>

                      <Button
                        variant="ghost"
                        onClick={() => handleDelete(doc.id, doc.name)}
                        className="h-7 text-xs text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10 px-2"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* ── MODAL 1: VIEW / DETAILS & VERSION HISTORY ──────────────────────────── */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-xl rounded-xl border bg-card p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b pb-4">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="size-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">{viewingDoc.name}</h3>
                  <p className="text-xs text-muted-foreground">
                    Type: <span className="font-mono text-foreground">{viewingDoc.doc_type}</span> · Current Version: <span className="font-semibold text-primary">v{viewingDoc.version}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setViewingDoc(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* Document Details */}
            <div className="grid grid-cols-2 gap-3 rounded-lg border bg-muted/20 p-3.5 text-xs">
              <div>
                <span className="text-muted-foreground block">Filename</span>
                <span className="font-mono font-medium text-foreground truncate block">{viewingDoc.filename}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">File Size</span>
                <span className="font-medium text-foreground">{formatBytes(viewingDoc.file_size)}</span>
              </div>
              <div>
                <span className="text-muted-foreground block">Status</span>
                <span className="inline-flex items-center gap-1 font-semibold text-emerald-500 capitalize">
                  <CheckCircle2 className="size-3.5" /> {viewingDoc.status}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Expiry Date</span>
                <span className="font-medium text-foreground">{viewingDoc.expiry_date || "No expiry set"}</span>
              </div>
            </div>

            {/* Version History */}
            <div className="space-y-2.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <History className="size-3.5 text-primary" /> Version History ({docVersions.length || 1})
              </h4>
              {loadingVersions ? (
                <div className="flex py-4 justify-center">
                  <Loader2 className="size-4 animate-spin text-muted-foreground" />
                </div>
              ) : docVersions.length === 0 ? (
                <div className="rounded border p-3 text-xs text-muted-foreground bg-muted/10">
                  Version {viewingDoc.version} is currently active.
                </div>
              ) : (
                <div className="space-y-2">
                  {docVersions.map((v) => (
                    <div
                      key={v.id}
                      className={`flex items-center justify-between rounded-lg border p-3 text-xs ${
                        v.version === viewingDoc.version
                          ? "border-primary/40 bg-primary/5"
                          : "bg-muted/10"
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-foreground">Version {v.version}</span>
                          {v.version === viewingDoc.version && (
                            <Badge tone="success" className="text-[9px] py-0 px-1.5">Current</Badge>
                          )}
                        </div>
                        <p className="font-mono text-[11px] text-muted-foreground">{v.filename}</p>
                        {v.notes && <p className="text-[11px] text-foreground/80 italic">{v.notes}</p>}
                      </div>
                      <div className="text-right text-[11px] text-muted-foreground">
                        <span>{formatBytes(v.file_size)}</span>
                        {v.created_at && (
                          <p>{new Date(v.created_at).toLocaleDateString()}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer Actions */}
            <div className="flex items-center justify-between pt-4 border-t gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  const target = viewingDoc;
                  setViewingDoc(null);
                  handleOpenEdit(target);
                }}
                className="gap-1.5 px-3 py-1.5 text-xs"
              >
                <Edit2 className="size-3.5" /> Edit Details
              </Button>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    const target = viewingDoc;
                    setViewingDoc(null);
                    handleOpenUpdate(target);
                  }}
                  className="gap-1.5 px-3 py-1.5 text-xs"
                >
                  <RefreshCw className="size-3.5" /> Upload New Version
                </Button>
                <Button variant="ghost" onClick={() => setViewingDoc(null)} className="px-3 py-1.5 text-xs">
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: UPDATE / UPLOAD NEW VERSION ─────────────────────────────── */}
      {updatingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg rounded-xl border bg-card p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-foreground">Upload New Version</h3>
                <p className="text-xs text-muted-foreground">
                  Replace <span className="font-semibold text-foreground">{updatingDoc.name}</span> with an updated file (will increment to <span className="text-primary font-bold">v{updatingDoc.version + 1}</span>).
                </p>
              </div>
              <button
                onClick={() => setUpdatingDoc(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleSaveNewVersion} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Select Replacement File *
                </label>
                <input
                  type="file"
                  required
                  onChange={(e) => setUpdateFile(e.target.files?.[0] || null)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-xs file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
                />
                {updateFile && (
                  <p className="mt-1.5 text-xs text-muted-foreground flex items-center gap-1">
                    <ImageIcon className="size-3.5 text-primary" /> {updateFile.name} ({formatBytes(updateFile.size)})
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Display Label
                </label>
                <input
                  type="text"
                  value={updateName}
                  onChange={(e) => setUpdateName(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Issue Date
                  </label>
                  <input
                    type="date"
                    value={updateIssuedDate}
                    onChange={(e) => setUpdateIssuedDate(e.target.value)}
                    className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Expiry Date
                  </label>
                  <input
                    type="date"
                    value={updateExpiryDate}
                    onChange={(e) => setUpdateExpiryDate(e.target.value)}
                    className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Version Change Notes (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Renewed passport with 10-year validity"
                  value={updateNotes}
                  onChange={(e) => setUpdateNotes(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="ghost" type="button" onClick={() => setUpdatingDoc(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={savingUpdate || !updateFile}>
                  {savingUpdate ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" /> Saving Version...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="mr-2 size-4" /> Save New Version
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 3: EDIT METADATA (NAME & DATES) ─────────────────────────────── */}
      {editingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-md rounded-xl border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between gap-2 border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-foreground">Edit Document Details</h3>
                <p className="text-xs text-muted-foreground">
                  Update label, issue date, or expiry date.
                </p>
              </div>
              <button
                onClick={() => setEditingDoc(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={handleSaveMetadata} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Display Name *
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Issue Date
                </label>
                <input
                  type="date"
                  value={editIssuedDate}
                  onChange={(e) => setEditIssuedDate(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Expiry Date
                </label>
                <input
                  type="date"
                  value={editExpiryDate}
                  onChange={(e) => setEditExpiryDate(e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="ghost" type="button" onClick={() => setEditingDoc(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={savingEdit}>
                  {savingEdit ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" /> Saving...
                    </>
                  ) : (
                    "Save Changes"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
