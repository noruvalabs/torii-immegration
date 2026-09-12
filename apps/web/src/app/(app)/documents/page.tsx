"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FileText,
  Upload,
  Trash2,
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
  LayoutGrid,
  Table as TableIcon,
  Sparkles,
  Zap,
  ArrowRight,
  UserCheck,
  FileCheck2,
  ExternalLink,
  Download,
  ChevronRight,
  Info,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationBar } from "@/components/ui/pagination";
import { useAuth } from "@/lib/auth-context";
import { formatErrorMessage } from "@/lib/api/errors";
import {
  getDocumentVersions,
  applyDocumentToCase,
  applyDocumentToProfile,
  reextractDocument,
  seedDummyDocuments,
  getDocumentFileUrl,
  getDocumentViewUrl,
  type WalletDocument,
  type DocumentType,
  type DocumentVersion,
} from "@/lib/api/wallet";
import {
  useWalletQuery,
  useWalletSummaryQuery,
  useDocumentTypesQuery,
  useUploadDocumentMutation,
  useDeleteDocumentMutation,
  usePatchDocumentMutation,
  walletKeys,
} from "@/lib/queries/wallet";
import { useCasesListQuery, caseKeys } from "@/lib/queries/cases";
import { useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  documentUploadSchema,
  type DocumentUploadFormData,
  documentMetadataSchema,
  type DocumentMetadataFormData,
  documentVersionSchema,
  type DocumentVersionFormData,
} from "@/lib/schemas/document";

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

const CATEGORY_MAP: Record<string, string> = {
  passport: "identity",
  photo: "identity",
  national_id: "identity",
  bank_statement: "financial",
  proof_of_funds: "financial",
  tax_return: "financial",
  employment_letter: "employment",
  employment_contract: "employment",
  pay_slips: "employment",
  business_registration: "employment",
  academic_certificate: "education",
  enrollment_letter: "education",
  transcript: "education",
  flight_itinerary: "travel",
  travel_itinerary: "travel",
  hotel_booking: "travel",
  travel_insurance: "travel",
  invitation_letter: "support",
  guarantor_letter: "support",
  residence_card: "immigration",
  visa_copy: "immigration",
  other: "support",
};

function getDocCategory(docType: string, docTypesList: DocumentType[]): string {
  const matched = docTypesList.find((t) => t.code === docType);
  if (matched?.category && matched.category.toLowerCase() !== "document") {
    return matched.category;
  }
  return CATEGORY_MAP[docType] || "document";
}

function formatBytes(bytes?: number | null) {
  if (!bytes) return "Unknown size";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatFieldKey(key: string): string {
  const map: Record<string, string> = {
    passport_number: "Passport No",
    full_name: "Full Name",
    nationality: "Nationality",
    date_of_birth: "Date of Birth",
    passport_expiry: "Passport Expiry",
    expiry_date: "Expiry Date",
    issuing_country: "Issuing Country",
    residence_card_number: "Residence Card No",
    status_of_residence: "Residence Status",
    bank_name: "Bank",
    balance: "Balance",
    account_holder: "Account Holder",
    employer_name: "Employer",
    monthly_salary: "Monthly Salary",
    position: "Position",
    departure_date: "Departure Date",
    destination: "Destination",
  };
  if (map[key]) return map[key];
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getFieldValue(val: unknown): string {
  if (val && typeof val === "object" && "value" in val) {
    return String((val as { value: unknown }).value);
  }
  return String(val || "");
}

export default function DocumentVaultPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const { data: walletDocs = [], isLoading: docsLoading } = useWalletQuery(token);
  const { data: summary = null, isLoading: summaryLoading } = useWalletSummaryQuery(token);
  const { data: typesFromQuery = [] } = useDocumentTypesQuery(token);
  const { data: userCases = [] } = useCasesListQuery(token);
  const docTypes = typesFromQuery.length > 0 ? typesFromQuery : DEFAULT_DOC_TYPES;

  let documents = walletDocs;
  if ((!documents || documents.length === 0) && summary?.documents_by_category) {
    documents = Object.values(summary.documents_by_category).flat() as WalletDocument[];
  }

  const uploadMutation = useUploadDocumentMutation(token);
  const deleteMutation = useDeleteDocumentMutation(token);
  const patchMutation = usePatchDocumentMutation(token);

  const loading = (docsLoading || summaryLoading) && documents.length === 0;

  // Dialog & Active filter state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [docViewMode, setDocViewMode] = useState<"cards" | "table">("table");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Modals state
  const [viewingDoc, setViewingDoc] = useState<WalletDocument | null>(null);
  const [docVersions, setDocVersions] = useState<DocumentVersion[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);

  const [updatingDoc, setUpdatingDoc] = useState<WalletDocument | null>(null);
  const [updateFile, setUpdateFile] = useState<File | null>(null);

  const [editingDoc, setEditingDoc] = useState<WalletDocument | null>(null);

  // "Apply to Application" Modal state
  const [applyingDoc, setApplyingDoc] = useState<WalletDocument | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [isExtractingId, setIsExtractingId] = useState<number | null>(null);
  const [isSyncingProfileId, setIsSyncingProfileId] = useState<number | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [viewTab, setViewTab] = useState<"preview" | "details">("preview");
  const [hoveredMeta, setHoveredMeta] = useState<{
    doc: WalletDocument;
    top: number;
    left: number;
  } | null>(null);

  const uploadForm = useForm<DocumentUploadFormData>({
    resolver: zodResolver(documentUploadSchema),
    defaultValues: {
      selectedType: "passport",
      docName: "",
      issuedDate: "",
      expiryDate: "",
    },
  });

  const versionForm = useForm<DocumentVersionFormData>({
    resolver: zodResolver(documentVersionSchema),
    defaultValues: {
      name: "",
      issuedDate: "",
      expiryDate: "",
      notes: "",
    },
  });

  const editForm = useForm<DocumentMetadataFormData>({
    resolver: zodResolver(documentMetadataSchema),
    defaultValues: {
      name: "",
      issued_date: "",
      expiry_date: "",
    },
  });

  async function handleSeedDummyDocuments() {
    setIsSeeding(true);
    try {
      const res = await seedDummyDocuments(token);
      await queryClient.invalidateQueries({ queryKey: walletKeys.all });
      toast.success(
        `Generated and processed ${res.documents?.length || 10} sample dummy documents with PyMuPDF & OCR.`
      );
    } catch (err) {
      toast.error(formatErrorMessage(err));
    } finally {
      setIsSeeding(false);
    }
  }

  // Open View Modal & fetch version history
  async function handleOpenView(doc: WalletDocument, initialTab: "preview" | "details" = "preview") {
    setViewingDoc(doc);
    setViewTab(initialTab);
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
    versionForm.reset({
      name: doc.name,
      issuedDate: doc.issued_date || "",
      expiryDate: doc.expiry_date || "",
      notes: "",
    });
  }

  // Open Edit Metadata Modal
  function handleOpenEdit(doc: WalletDocument) {
    setEditingDoc(doc);
    editForm.reset({
      name: doc.name,
      issued_date: doc.issued_date || "",
      expiry_date: doc.expiry_date || "",
    });
  }

  // Open Apply to Application Modal
  function handleOpenApply(doc: WalletDocument) {
    setApplyingDoc(doc);
    if (userCases.length > 0) {
      setSelectedCaseId(userCases[0].id);
    } else {
      setSelectedCaseId(null);
    }
  }

  async function handleApplyToCase() {
    if (!applyingDoc || !selectedCaseId) return;
    setIsApplying(true);
    try {
      const res = await applyDocumentToCase(applyingDoc.id, selectedCaseId, token);
      const targetCase = userCases.find((c) => c.id === selectedCaseId);
      const caseLabel = targetCase?.scope_label || targetCase?.reference || `Case #${selectedCaseId}`;
      toast.success(
        `Success! Applied ${res.fields_applied?.length || "all"} extracted metadata fields to application "${caseLabel}".`
      );
      queryClient.invalidateQueries({ queryKey: caseKeys.all });
      setApplyingDoc(null);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    } finally {
      setIsApplying(false);
    }
  }

  async function handleSyncProfile(doc: WalletDocument) {
    setIsSyncingProfileId(doc.id);
    try {
      await applyDocumentToProfile(doc.id, token);
      toast.success(`User profile updated with extracted fields from "${doc.name}".`);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    } finally {
      setIsSyncingProfileId(null);
    }
  }

  async function handleReextract(docId: number) {
    setIsExtractingId(docId);
    try {
      await reextractDocument(docId, token);
      await queryClient.invalidateQueries({ queryKey: walletKeys.all });
      toast.success("Document re-analyzed with PyMuPDF & OCR.");
    } catch (err) {
      toast.error(formatErrorMessage(err));
    } finally {
      setIsExtractingId(null);
    }
  }

  async function onUploadSubmit(data: DocumentUploadFormData) {
    if (!file) {
      toast.error("Please select a file to upload.");
      return;
    }

    try {
      const matchedType = docTypes.find((t) => t.code === data.selectedType);
      const nameToUse = data.docName?.trim() || matchedType?.name || data.selectedType;
      await uploadMutation.mutateAsync({
        file,
        docType: data.selectedType,
        name: nameToUse,
        issuedDate: data.issuedDate || undefined,
        expiryDate: data.expiryDate || undefined,
      });
      toast.success(`"${nameToUse}" uploaded and processed with PyMuPDF/OCR successfully.`);
      setFile(null);
      uploadForm.reset({
        selectedType: "passport",
        docName: "",
        issuedDate: "",
        expiryDate: "",
      });
      setIsUploadOpen(false);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    }
  }

  async function onSaveNewVersion(data: DocumentVersionFormData) {
    if (!updatingDoc) return;
    if (!updateFile) {
      toast.error("Please select a replacement file to upload as a new version.");
      return;
    }

    try {
      const nameToUse = data.name?.trim() || updatingDoc.name;
      await uploadMutation.mutateAsync({
        file: updateFile,
        docType: updatingDoc.doc_type,
        name: nameToUse,
        issuedDate: data.issuedDate || undefined,
        expiryDate: data.expiryDate || undefined,
        notes: data.notes || undefined,
      });
      toast.success(`New version for "${nameToUse}" saved (v${updatingDoc.version + 1}) and re-analyzed.`);
      setUpdatingDoc(null);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    }
  }

  async function onSaveMetadata(data: DocumentMetadataFormData) {
    if (!editingDoc) return;

    try {
      await patchMutation.mutateAsync({
        documentId: editingDoc.id,
        data: {
          name: data.name.trim(),
          issued_date: data.issued_date || undefined,
          expiry_date: data.expiry_date || undefined,
        },
      });
      toast.success(`Document details updated for "${data.name}".`);
      setEditingDoc(null);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    }
  }

  async function handleDelete(docId: number, name: string) {
    if (!confirm(`Remove "${name}" from your Document Vault?`)) return;
    try {
      await deleteMutation.mutateAsync(docId);
      toast.success(`Document "${name}" removed.`);
    } catch (err) {
      toast.error(formatErrorMessage(err));
    }
  }

  // Reset pagination when switching categories
  useEffect(() => {
    setCurrentPage(1);
  }, [activeCategory]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    docTypes.forEach((t) => {
      if (t.category && t.category.toLowerCase() !== "document") set.add(t.category);
    });
    Object.values(CATEGORY_MAP).forEach((cat) => set.add(cat));
    documents.forEach((d) => {
      const cat = getDocCategory(d.doc_type, docTypes);
      if (cat && cat.toLowerCase() !== "document") set.add(cat);
    });
    return ["All", ...Array.from(set)];
  }, [docTypes, documents]);

  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      if (activeCategory === "All" || activeCategory === "all") return true;
      const docCategory = getDocCategory(doc.doc_type, docTypes);
      return docCategory.toLowerCase() === activeCategory.toLowerCase();
    });
  }, [documents, activeCategory, docTypes]);

  const totalPages = Math.ceil(filteredDocs.length / pageSize) || 1;
  const paginatedDocs = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredDocs.slice(startIndex, startIndex + pageSize);
  }, [filteredDocs, currentPage, pageSize]);

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Document Vault</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your verified immigration documents, certificates, and records in one secure vault.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">{documents.length}</span> Documents
            <span>·</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">
              {documents.filter((d) => d.status === "active").length}
            </span> Active
          </div>

          <Button
            onClick={() => setIsUploadOpen(true)}
            className="gap-1.5 shadow-sm"
          >
            <Plus className="size-4" /> Upload Document
          </Button>
        </div>
      </div>

      {/* ── TOOLBAR: CATEGORIES & VIEW SWITCHER ─────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors capitalize ${
                activeCategory.toLowerCase() === cat.toLowerCase()
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* View Mode Switcher */}
        <div className="flex items-center rounded-lg border bg-muted/40 p-0.5 ml-auto">
          <button
            type="button"
            onClick={() => setDocViewMode("cards")}
            aria-label="Cards view"
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              docViewMode === "cards"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <LayoutGrid className="size-3.5" /> Cards
          </button>
          <button
            type="button"
            onClick={() => setDocViewMode("table")}
            aria-label="Table view"
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              docViewMode === "table"
                ? "bg-background text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <TableIcon className="size-3.5" /> Table
          </button>
        </div>
      </div>

      {/* ── DOCUMENT LIST CONTENT ────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex py-16 justify-center">
          <Loader2 className="size-8 animate-spin text-muted-foreground/60" />
        </div>
      ) : filteredDocs.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-14 text-center space-y-3">
            <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <FolderOpen className="size-6" />
            </div>
            <div>
              <p className="text-base font-semibold">No documents found</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                Upload your passport, residence card, or bank statements. Torii will extract the fields with PyMuPDF &amp; OCR and make them available to auto-fill any visa application form.
              </p>
            </div>
            <Button onClick={() => setIsUploadOpen(true)} className="gap-1.5 mt-2">
              <Plus className="size-4" /> Upload First Document
            </Button>
          </CardContent>
        </Card>
      ) : docViewMode === "table" ? (
        /* ── TABLE VIEW ─────────────────────────────────────────────────────── */
        <div className="space-y-4">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="px-5">Type / Category</TableHead>
                    <TableHead className="px-5">Extracted Metadata</TableHead>
                    <TableHead className="px-5">File &amp; Expiry</TableHead>
                    <TableHead className="px-5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedDocs.map((doc) => {
                    const category = getDocCategory(doc.doc_type, docTypes);
                    const isImage =
                      doc.content_type?.startsWith("image/") ||
                      /\.(png|jpg|jpeg|webp|gif)$/i.test(doc.filename);
                    const extracted = doc.extracted_fields || {};
                    const extractedEntries = Object.entries(extracted).filter(
                      ([, v]) => Boolean(getFieldValue(v))
                    );

                    return (
                      <TableRow key={doc.id} className="hover:bg-muted/30">
                        {/* 1. Type / Category */}
                        <TableCell className="px-5 align-middle py-3.5">
                          <div className="flex items-center gap-3">
                            <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                              {isImage ? <ImageIcon className="size-4" /> : <FileText className="size-4" />}
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="font-semibold text-sm text-foreground truncate" title={doc.name}>
                                  {doc.name}
                                </p>
                                <span className="font-semibold text-primary bg-primary/10 px-1.5 py-0.2 rounded text-[10px]">
                                  v{doc.version}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 mt-0.5 text-xs">
                                <span className="font-mono text-muted-foreground text-[11px]">{doc.doc_type}</span>
                                <Badge tone="muted" className="text-[10px] capitalize py-0 px-1.5">
                                  {category}
                                </Badge>
                              </div>
                            </div>
                          </div>
                        </TableCell>

                        {/* 2. Extracted Metadata */}
                        <TableCell className="px-5 align-middle py-3.5">
                          {extractedEntries.length > 0 ? (
                            <button
                              type="button"
                              onClick={() => handleOpenView(doc, "details")}
                              onMouseEnter={(e) => {
                                const rect = e.currentTarget.getBoundingClientRect();
                                setHoveredMeta({
                                  doc,
                                  top: rect.bottom + 6,
                                  left: Math.min(rect.left, window.innerWidth - 340),
                                });
                              }}
                              onMouseLeave={() => setHoveredMeta(null)}
                              className="group inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/10 hover:bg-primary/20 px-2.5 py-1 text-xs font-medium text-primary transition-all cursor-pointer shadow-2xs"
                              title="Hover to preview fields, click for full details modal"
                            >
                              <Sparkles className="size-3 text-primary shrink-0" />
                              <span>
                                {extractedEntries.length} {extractedEntries.length === 1 ? "field" : "fields"}
                              </span>
                              <ChevronRight className="size-3 text-primary/70 group-hover:translate-x-0.5 transition-transform" />
                            </button>
                          ) : (
                            <span className="text-xs text-muted-foreground/40 font-mono">—</span>
                          )}
                        </TableCell>

                        {/* 3. File & Expiry */}
                        <TableCell className="px-5 align-middle py-3.5 text-xs">
                          <p className="font-mono font-medium text-foreground truncate max-w-[170px]" title={doc.filename}>
                            {doc.filename}
                          </p>
                          <p className="text-muted-foreground text-[11px] mt-0.5">
                            {formatBytes(doc.file_size)}
                            {doc.expiry_date && (
                              <span className="ml-1.5 font-medium text-foreground">· Exp: {doc.expiry_date}</span>
                            )}
                          </p>
                        </TableCell>

                        {/* 4. Actions */}
                        <TableCell className="px-5 align-middle py-3.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleOpenView(doc, "preview")}
                              className="h-8 text-xs gap-1.5 px-3 font-medium shadow-2xs"
                              title="View document"
                            >
                              <Eye className="size-3.5" /> View
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleOpenUpdate(doc)}
                              className="size-8 p-0 text-muted-foreground hover:text-foreground"
                              title="Upload new version"
                            >
                              <RefreshCw className="size-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(doc.id, doc.name)}
                              className="size-8 p-0 text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10"
                              title="Delete document"
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <PaginationBar
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filteredDocs.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
            itemName="documents"
          />
        </div>
      ) : (
        /* ── CARDS VIEW ─────────────────────────────────────────────────────── */
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {paginatedDocs.map((doc) => {
              const category = getDocCategory(doc.doc_type, docTypes);
              const isImage =
                doc.content_type?.startsWith("image/") ||
                /\.(png|jpg|jpeg|webp|gif)$/i.test(doc.filename);
              const extracted = doc.extracted_fields || {};
              const extractedEntries = Object.entries(extracted).filter(
                ([, v]) => Boolean(getFieldValue(v))
              );
              const confidencePct = Math.round(
                (doc.extraction_confidence ? doc.extraction_confidence : 0.9) * 100
              );

              return (
                <Card
                  key={doc.id}
                  className="flex flex-col justify-between transition-all hover:border-primary/50 shadow-xs"
                >
                  <CardContent className="p-4 space-y-3.5">
                    {/* Top Row: Icon + Name + Category */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                          {isImage ? <ImageIcon className="size-5" /> : <FileText className="size-5" />}
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-sm font-semibold text-foreground truncate" title={doc.name}>
                            {doc.name}
                          </h3>
                          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                            <span className="font-mono">{doc.doc_type}</span>
                            <span>·</span>
                            <span className="font-semibold text-primary">v{doc.version}</span>
                            {isImage && <span>· Image</span>}
                          </div>
                        </div>
                      </div>
                      <Badge tone="muted" className="text-[10px] capitalize shrink-0">
                        {category}
                      </Badge>
                    </div>

                    {/* File metadata row */}
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground border-b pb-2">
                      <span className="font-mono truncate max-w-[160px]" title={doc.filename}>
                        {doc.filename}
                      </span>
                      <span>{formatBytes(doc.file_size)}</span>
                    </div>

                    {/* ── EXTRACTED KEY DETAILS ──────────────────────── */}
                    {extractedEntries.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 rounded-lg border bg-muted/20 p-2.5">
                        {extractedEntries.map(([key, val]) => (
                          <div
                            key={key}
                            className="rounded border border-border/60 bg-background/80 px-2 py-1 text-[11px] shadow-2xs"
                          >
                            <span className="text-muted-foreground block text-[10px]">
                              {formatFieldKey(key)}
                            </span>
                            <span className="font-semibold text-foreground truncate block max-w-[180px]">
                              {getFieldValue(val)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-lg border bg-muted/10 p-2.5 text-center text-[11px] text-muted-foreground italic">
                        Standard document record
                      </div>
                    )}

                    {/* ── CARD ACTIONS ────────────────────────────────────────── */}
                    <div className="flex items-center justify-between gap-2 pt-2 border-t">
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => handleOpenView(doc)}
                        className="gap-1.5 text-xs px-3 h-8 font-medium shadow-xs"
                      >
                        <Eye className="size-3.5" /> View
                      </Button>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleOpenUpdate(doc)}
                          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted"
                          title="Upload new version"
                        >
                          <RefreshCw className="size-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(doc)}
                          className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-muted"
                          title="Edit details"
                        >
                          <Edit2 className="size-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id, doc.name)}
                          className="p-1.5 rounded text-[var(--color-danger)] hover:bg-[var(--color-danger)]/10"
                          title="Delete"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <PaginationBar
            currentPage={currentPage}
            totalPages={totalPages}
            totalItems={filteredDocs.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
            itemName="documents"
          />
        </div>
      )}

      {/* ── MODAL 1: UPLOAD DOCUMENT (SIMPLE & CLEAN) ────────────────────────── */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg rounded-xl border bg-card p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                  <Upload className="size-4 text-primary" /> Upload Document to Vault
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  PyMuPDF &amp; OCR will parse key dates, numbers, and names automatically.
                </p>
              </div>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>

            <form onSubmit={uploadForm.handleSubmit(onUploadSubmit)} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Document Type *
                </label>
                <select
                  {...uploadForm.register("selectedType")}
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
                  File (PDF, PNG, JPG, WEBP) *
                </label>
                <input
                  type="file"
                  required
                  accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-primary file:px-3 file:py-1 file:text-xs file:font-semibold file:text-primary-foreground hover:file:bg-primary/90"
                />
                {file && (
                  <p className="mt-1.5 text-xs text-muted-foreground flex items-center gap-1">
                    <FileText className="size-3.5 text-primary" /> {file.name} ({formatBytes(file.size)})
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Display Label (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Primary Passport (2024-2034)"
                  {...uploadForm.register("docName")}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Issue Date (Optional)
                  </label>
                  <input
                    type="date"
                    {...uploadForm.register("issuedDate")}
                    className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Expiry Date (Optional)
                  </label>
                  <input
                    type="date"
                    {...uploadForm.register("expiryDate")}
                    className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              <div className="rounded-lg border bg-primary/5 p-3 text-xs text-muted-foreground flex items-center gap-2">
                <Sparkles className="size-4 text-primary shrink-0" />
                <span>
                  Dates, applicant name, and document numbers are automatically detected from PDFs using PyMuPDF and OCR.
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t">
                <Button variant="ghost" type="button" onClick={() => setIsUploadOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={uploadMutation.isPending || !file}>
                  {uploadMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" /> Analyzing &amp; Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 size-4" /> Save to Vault
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL 2: PRE-FILL VISA APPLICATION (KEY USER REQUIREMENT) ────────── */}
      {applyingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="relative w-full max-w-lg rounded-xl border bg-card p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                  <Zap className="size-4 text-amber-500" /> Pre-fill Visa Application
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Transfer extracted metadata from <span className="font-semibold text-foreground">{applyingDoc.name}</span> directly into your intake questionnaire.
                </p>
              </div>
              <button
                onClick={() => setApplyingDoc(null)}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="size-5" />
              </button>
            </div>

            {/* Extracted Fields Preview */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileCheck2 className="size-3.5 text-primary" /> Fields That Will Be Pre-filled
              </h4>
              {applyingDoc.extracted_fields && Object.keys(applyingDoc.extracted_fields).length > 0 ? (
                <div className="rounded-lg border bg-muted/20 p-3 space-y-1.5 text-xs max-h-48 overflow-y-auto">
                  {Object.entries(applyingDoc.extracted_fields).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between py-0.5">
                      <span className="text-muted-foreground">{formatFieldKey(k)}:</span>
                      <span className="font-semibold text-foreground truncate max-w-[200px]">
                        {getFieldValue(v)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded border p-3 text-xs text-muted-foreground bg-muted/10">
                  Standard document fields ({applyingDoc.doc_type}) will be linked to the application checklist.
                </div>
              )}
            </div>

            {/* Application Case Picker */}
            <div className="space-y-2 pt-1">
              <label className="block text-xs font-medium text-muted-foreground">
                Select Destination Visa Application *
              </label>
              {userCases.length === 0 ? (
                <div className="rounded border p-3 text-xs text-muted-foreground">
                  No active visa applications found. Create or open an application first from the Applications menu.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {userCases.map((c) => (
                    <label
                      key={c.id}
                      className={`flex items-center justify-between rounded-lg border p-3 text-xs cursor-pointer transition-colors ${
                        selectedCaseId === c.id
                          ? "border-primary bg-primary/5 ring-1 ring-primary"
                          : "hover:bg-muted/40"
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="targetCase"
                            checked={selectedCaseId === c.id}
                            onChange={() => setSelectedCaseId(c.id)}
                            className="text-primary"
                          />
                          <span className="font-bold text-foreground">
                            {c.scope_label || c.reference || `Case #${c.id}`}
                          </span>
                          {(c.visa_category_code || c.jurisdiction_code) && (
                            <Badge tone="muted" className="text-[10px]">
                              {c.visa_category_code || c.jurisdiction_code}
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground pl-5">
                          Status: <span className="capitalize">{c.status}</span> · Ref: {c.reference}
                        </p>
                      </div>
                      <CheckCircle2
                        className={`size-4 ${
                          selectedCaseId === c.id ? "text-primary" : "text-muted-foreground/30"
                        }`}
                      />
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t">
              <Button variant="ghost" onClick={() => setApplyingDoc(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleApplyToCase}
                disabled={isApplying || !selectedCaseId}
                className="gap-1.5"
              >
                {isApplying ? (
                  <>
                    <Loader2 className="mr-1.5 size-4 animate-spin" /> Pre-filling Intake...
                  </>
                ) : (
                  <>
                    <Zap className="mr-1.5 size-4 text-amber-300" /> Apply &amp; Pre-fill Form
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 3: VIEW / DETAILS & VERSION HISTORY (WITH IFRAME PDF VIEWER) ── */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-3 md:p-6 animate-in fade-in duration-150">
          <div className="relative w-full max-w-4xl rounded-xl border bg-card p-5 md:p-6 shadow-2xl space-y-4 max-h-[92vh] flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between gap-3 border-b pb-3 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
                  <FileText className="size-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-base font-bold text-foreground truncate">{viewingDoc.name}</h3>
                  <p className="text-xs text-muted-foreground truncate">
                    Type: <span className="font-mono text-foreground font-semibold">{viewingDoc.doc_type}</span> · Version:{" "}
                    <span className="font-semibold text-primary">v{viewingDoc.version}</span> · Size:{" "}
                    <span>{formatBytes(viewingDoc.file_size)}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={getDocumentFileUrl(viewingDoc.id, token)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md border bg-background hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shadow-2xs"
                  title="Open PDF in a new browser tab"
                >
                  <ExternalLink className="size-3.5" />
                  <span className="hidden sm:inline">Open in Tab</span>
                </a>
                <a
                  href={getDocumentFileUrl(viewingDoc.id, token)}
                  download={viewingDoc.filename}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md border bg-background hover:bg-muted text-muted-foreground hover:text-foreground transition-colors shadow-2xs"
                  title="Download document file"
                >
                  <Download className="size-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </a>
                <button
                  onClick={() => setViewingDoc(null)}
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                >
                  <X className="size-5" />
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 border-b shrink-0 text-xs">
              <button
                type="button"
                onClick={() => setViewTab("preview")}
                className={`inline-flex items-center gap-1.5 pb-2 px-3 font-semibold transition-colors border-b-2 ${
                  viewTab === "preview"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <FileText className="size-3.5" />
                Document Preview
              </button>
              <button
                type="button"
                onClick={() => setViewTab("details")}
                className={`inline-flex items-center gap-1.5 pb-2 px-3 font-semibold transition-colors border-b-2 ${
                  viewTab === "details"
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Sparkles className="size-3.5" />
                Extracted Details &amp; History
                {viewingDoc.extracted_fields && Object.keys(viewingDoc.extracted_fields).length > 0 && (
                  <Badge tone="muted" className="text-[10px] px-1.5 py-0">
                    {Object.keys(viewingDoc.extracted_fields).length}
                  </Badge>
                )}
              </button>
            </div>

            {/* Tab Body */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {viewTab === "preview" ? (
                <div className="space-y-3">
                  {/* Embedded Iframe */}
                  <div className="relative w-full h-[520px] rounded-lg border bg-[#090d16] overflow-hidden shadow-inner">
                    <iframe
                      src={getDocumentViewUrl(viewingDoc.id, token)}
                      title={viewingDoc.name}
                      className="w-full h-full border-0"
                    />
                  </div>

                  {/* Quick Metadata Snippet */}
                  {viewingDoc.extracted_fields && Object.keys(viewingDoc.extracted_fields).length > 0 && (
                    <div className="rounded-lg border bg-muted/30 p-3 flex flex-wrap items-center gap-2 text-xs">
                      <span className="font-semibold text-foreground flex items-center gap-1 text-[11px]">
                        Extracted Details:
                      </span>
                      {Object.entries(viewingDoc.extracted_fields)
                        .filter(([, v]) => Boolean(getFieldValue(v)))
                        .slice(0, 4)
                        .map(([k, v]) => (
                          <span
                            key={k}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-background border text-xs shadow-2xs"
                          >
                            <span className="text-muted-foreground font-medium">{formatFieldKey(k)}:</span>
                            <span className="font-semibold text-foreground truncate max-w-[130px]">
                              {getFieldValue(v)}
                            </span>
                          </span>
                        ))}
                      {Object.keys(viewingDoc.extracted_fields).length > 4 && (
                        <button
                          type="button"
                          onClick={() => setViewTab("details")}
                          className="text-primary hover:underline font-semibold ml-auto text-xs"
                        >
                          View all {Object.keys(viewingDoc.extracted_fields).length} fields &rarr;
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Document Details Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 rounded-lg border bg-muted/20 p-3.5 text-xs">
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-bold">Filename</span>
                      <span className="font-mono font-medium text-foreground truncate block">
                        {viewingDoc.filename}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-bold">File Size</span>
                      <span className="font-medium text-foreground">{formatBytes(viewingDoc.file_size)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-bold">Status</span>
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-500 capitalize">
                        <CheckCircle2 className="size-3.5" /> {viewingDoc.status}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px] uppercase font-bold">Expiry Date</span>
                      <span className="font-medium text-foreground">{viewingDoc.expiry_date || "—"}</span>
                    </div>
                  </div>

                  {/* Extracted Fields in Detail */}
                  {viewingDoc.extracted_fields && Object.keys(viewingDoc.extracted_fields).length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Sparkles className="size-3.5 text-primary" /> Extracted Document Details
                      </h4>
                      <div className="rounded-lg border bg-muted/10 p-3 grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                        {Object.entries(viewingDoc.extracted_fields).map(([k, v]) => (
                          <div key={k} className="p-2 rounded-md bg-background border shadow-2xs">
                            <span className="text-muted-foreground block text-[10px] uppercase font-medium">
                              {formatFieldKey(k)}
                            </span>
                            <span className="font-semibold text-foreground truncate block mt-0.5">
                              {getFieldValue(v)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Version History */}
                  <div className="space-y-2">
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
                                  <Badge tone="success" className="text-[9px] py-0 px-1.5">
                                    Current
                                  </Badge>
                                )}
                              </div>
                              <p className="font-mono text-[11px] text-muted-foreground">{v.filename}</p>
                              {v.notes && <p className="text-[11px] text-foreground/80 italic">{v.notes}</p>}
                            </div>
                            <div className="text-right text-[11px] text-muted-foreground">
                              <span>{formatBytes(v.file_size)}</span>
                              {v.created_at && <p>{new Date(v.created_at).toLocaleDateString()}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer Actions */}
            <div className="flex items-center justify-between pt-3 border-t gap-2 shrink-0">
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
                  variant="outline"
                  onClick={() => {
                    const target = viewingDoc;
                    setViewingDoc(null);
                    handleOpenUpdate(target);
                  }}
                  className="gap-1.5 px-3 py-1.5 text-xs"
                >
                  <RefreshCw className="size-3.5" /> New Version
                </Button>
                <Button variant="ghost" onClick={() => setViewingDoc(null)} className="px-3 py-1.5 text-xs">
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 4: UPDATE / UPLOAD NEW VERSION ─────────────────────────────── */}
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

            <form onSubmit={versionForm.handleSubmit(onSaveNewVersion)} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Select Replacement File *
                </label>
                <input
                  type="file"
                  required
                  accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx"
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
                  {...versionForm.register("name")}
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
                    {...versionForm.register("issuedDate")}
                    className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Expiry Date
                  </label>
                  <input
                    type="date"
                    {...versionForm.register("expiryDate")}
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
                  placeholder="e.g. Renewed document with 10-year validity"
                  {...versionForm.register("notes")}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="ghost" type="button" onClick={() => setUpdatingDoc(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={uploadMutation.isPending || !updateFile}>
                  {uploadMutation.isPending ? (
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

      {/* ── MODAL 5: EDIT METADATA (NAME & DATES) ─────────────────────────────── */}
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

            <form onSubmit={editForm.handleSubmit(onSaveMetadata)} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Display Name *
                </label>
                <input
                  type="text"
                  {...editForm.register("name")}
                  className={`w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                    editForm.formState.errors.name ? "border-[var(--color-danger)]" : ""
                  }`}
                />
                {editForm.formState.errors.name && (
                  <span className="mt-1 block text-[11px] text-[var(--color-danger)]">
                    {editForm.formState.errors.name.message}
                  </span>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Issue Date
                </label>
                <input
                  type="date"
                  {...editForm.register("issued_date")}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">
                  Expiry Date
                </label>
                <input
                  type="date"
                  {...editForm.register("expiry_date")}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="ghost" type="button" onClick={() => setEditingDoc(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={patchMutation.isPending}>
                  {patchMutation.isPending ? (
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

      {/* ── FLOATING TOOLTIP FOR EXTRACTED METADATA ────────────────────────── */}
      {hoveredMeta && (
        <div
          style={{
            position: "fixed",
            top: `${hoveredMeta.top}px`,
            left: `${hoveredMeta.left}px`,
          }}
          className="z-50 w-80 rounded-xl border bg-card/95 backdrop-blur-md p-4 shadow-2xl text-card-foreground animate-in fade-in-0 zoom-in-95 pointer-events-none"
        >
          <div className="flex items-center justify-between border-b pb-2 mb-2.5">
            <div className="flex items-center gap-1.5 min-w-0">
              <Sparkles className="size-3.5 text-primary shrink-0" />
              <span className="text-xs font-bold text-foreground truncate">{hoveredMeta.doc.name}</span>
            </div>
            <Badge tone="muted" className="text-[10px] py-0 px-1.5 shrink-0">
              {Object.keys(hoveredMeta.doc.extracted_fields || {}).length} fields
            </Badge>
          </div>
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {Object.entries(hoveredMeta.doc.extracted_fields || {}).map(([key, val]) => (
              <div key={key} className="text-xs">
                <span className="text-muted-foreground block text-[10px] font-medium uppercase tracking-wider">
                  {formatFieldKey(key)}
                </span>
                <span className="font-semibold text-foreground block text-xs mt-0.5 break-words">
                  {getFieldValue(val)}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t pt-2 mt-2.5 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>Click badge to open full details modal</span>
            <ExternalLink className="size-3 text-primary" />
          </div>
        </div>
      )}
    </div>
  );
}
