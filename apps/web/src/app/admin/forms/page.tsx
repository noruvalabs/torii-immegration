"use client";

import { useCallback, useEffect, useState, useRef, useMemo } from "react";
import {
  FileText,
  Plus,
  Trash2,
  UploadCloud,
  FileCheck,
  FileUp,
  Eye,
  Loader2,
  X,
  Search,
  ExternalLink,
  Maximize2,
  ChevronUp,
  ChevronDown,
  Download,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import {
  listAllFormTemplates,
  uploadFormTemplatePdf,
  type FormTemplateDetail,
} from "@/lib/api/jurisdictions";
import { toast } from "sonner";

export default function FormsPage() {
  const { token, loading: authLoading } = useAuth();
  const [templates, setTemplates] = useState<FormTemplateDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Upload modal state
  const [uploadingPdfFor, setUploadingPdfFor] = useState<string | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Embedded viewer state
  const [expandedPdfForms, setExpandedPdfForms] = useState<Record<string, boolean>>({});
  const [fullscreenPdf, setFullscreenPdf] = useState<{
    code: string;
    title: string;
    url: string;
  } | null>(null);

  const togglePdfExpand = (formCode: string) => {
    setExpandedPdfForms((prev) => ({
      ...prev,
      [formCode]: !prev[formCode],
    }));
  };

  const previewUploadUrl = useMemo(() => {
    if (!pdfFile) return null;
    return URL.createObjectURL(pdfFile);
  }, [pdfFile]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAllFormTemplates(token);
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load form templates.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (authLoading) return;
    void load();
  }, [authLoading, load]);

  const handleOpenPdfUpload = (formCode: string) => {
    setUploadingPdfFor(formCode);
    setPdfFile(null);
  };

  const handleUploadPdf = async () => {
    if (!uploadingPdfFor || !pdfFile) {
      toast.error("Please select a PDF file to upload.");
      return;
    }
    setUploadingPdf(true);
    try {
      const targetTemplate = templates.find((t) => t.code === uploadingPdfFor);
      const res = await uploadFormTemplatePdf(token, uploadingPdfFor, pdfFile, {
        jurisdiction_code: targetTemplate?.jurisdiction_code || undefined,
        visa_category_code: targetTemplate?.visa_category_code || undefined,
        action_code: targetTemplate?.action_code || undefined,
      });
      toast.success(res.message || `PDF uploaded successfully for ${uploadingPdfFor}!`);
      setUploadingPdfFor(null);
      setPdfFile(null);
      // Auto expand viewer for this form
      setExpandedPdfForms((prev) => ({ ...prev, [uploadingPdfFor]: true }));
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to upload PDF");
    } finally {
      setUploadingPdf(false);
    }
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return templates;
    const q = search.toLowerCase();
    return templates.filter(
      (t) =>
        t.code.toLowerCase().includes(q) ||
        t.official_title.toLowerCase().includes(q) ||
        (t.jurisdiction_name && t.jurisdiction_name.toLowerCase().includes(q)) ||
        (t.visa_category_name && t.visa_category_name.toLowerCase().includes(q)),
    );
  }, [templates, search]);

  return (
    <div className="space-y-6 max-w-6xl pb-16">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary shadow-2xs">
            <FileText className="size-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">Forms &amp; PDF Templates</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Official government application PDF templates, version tracking, and field mappings.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void load()}
            disabled={loading}
            className="text-xs"
          >
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {error}
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter form templates by code, title, country, or route..."
          className="w-full pl-9 pr-4 py-2 text-xs rounded-xl border bg-card text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary shadow-2xs"
        />
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-2">
          <Loader2 className="size-6 animate-spin text-primary" />
          <p className="text-xs text-muted-foreground font-medium">Loading form templates &amp; PDF files...</p>
        </div>
      ) : filtered.length === 0 ? (
        <Card className="border-dashed p-10 text-center">
          <FileText className="mx-auto mb-3 size-10 text-muted-foreground/40" />
          <h3 className="text-sm font-bold text-foreground">No form templates found</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {search ? "No templates match your search filter." : "No form templates configured yet."}
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filtered.map((t) => {
            const isExpanded = expandedPdfForms[t.code] ?? false;
            return (
              <Card key={`${t.code}-${t.id || ""}`} className="border shadow-xs overflow-hidden">
                <CardHeader className="bg-muted/20 pb-3 border-b">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-black uppercase text-foreground bg-primary/10 text-primary px-2 py-0.5 rounded-md">
                          {t.code}
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">v{t.version}</span>
                        {t.jurisdiction_name && (
                          <Badge tone="muted" className="text-[10px]">
                            {t.jurisdiction_name} ({t.jurisdiction_code})
                          </Badge>
                        )}
                        {t.visa_category_name && (
                          <Badge tone="muted" className="text-[10px]">
                            {t.visa_category_name}
                          </Badge>
                        )}
                        <Badge tone={t.is_live ? "success" : "muted"} className="text-[10px]">
                          {t.is_live ? "live" : "draft"}
                        </Badge>
                      </div>
                      <CardTitle className="text-sm font-bold text-foreground">{t.official_title}</CardTitle>
                    </div>

                    {t.jurisdiction_code && t.visa_category_code && (
                      <Link
                        href={`/admin/jurisdictions/${t.jurisdiction_code}/routes/${t.visa_category_code}`}
                        className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline shrink-0"
                      >
                        <span>Route Editor</span>
                        <ExternalLink className="size-3" />
                      </Link>
                    )}
                  </div>
                </CardHeader>

                {/* PDF Document Status & Action Strip */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-accent/30 px-4 py-2.5 border-b text-xs">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    {t.has_pdf ? (
                      <>
                        <Badge tone="success" className="gap-1 font-semibold text-[11px]">
                          <FileCheck className="size-3" /> PDF Attached
                        </Badge>
                        <span className="font-mono text-muted-foreground truncate max-w-[220px]">
                          {t.pdf_filename || `${t.code}.pdf`}
                        </span>
                        {t.pdf_pages && <span className="text-muted-foreground">• {t.pdf_pages} pages</span>}
                        {t.pdf_filesize && (
                          <span className="text-muted-foreground">
                            • {Math.round(t.pdf_filesize / 1024)} KB
                          </span>
                        )}
                      </>
                    ) : (
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Badge tone="warning" className="gap-1 font-semibold text-[11px]">
                          <FileUp className="size-3" /> No PDF Attached
                        </Badge>
                        <span className="text-[11px]">Upload the official government PDF template for this form.</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {t.has_pdf && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => togglePdfExpand(t.code)}
                          className="gap-1.5 h-7 px-2.5 text-xs font-semibold hover:bg-muted"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUp className="size-3.5 text-primary" />
                              <span>Hide PDF</span>
                            </>
                          ) : (
                            <>
                              <Eye className="size-3.5 text-primary" />
                              <span>View PDF Form</span>
                            </>
                          )}
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setFullscreenPdf({
                              code: t.code,
                              title: t.official_title,
                              url: `/backend/v1/admin/ops/form-templates/${encodeURIComponent(t.code)}/pdf`,
                            })
                          }
                          className="gap-1 h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                          title="Fullscreen Viewer"
                        >
                          <Maximize2 className="size-3.5" />
                          <span className="hidden sm:inline">Fullscreen</span>
                        </Button>

                        <a
                          href={`/backend/v1/admin/ops/form-templates/${encodeURIComponent(t.code)}/pdf`}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted transition-colors shadow-2xs text-muted-foreground hover:text-foreground"
                          title="Open in new tab"
                        >
                          <ExternalLink className="size-3" />
                        </a>
                      </>
                    )}

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenPdfUpload(t.code)}
                      className="gap-1.5 h-7 px-2.5 text-xs font-semibold bg-background shadow-2xs hover:border-primary/50 text-primary"
                    >
                      <UploadCloud className="size-3.5" />
                      <span>{t.has_pdf ? "Change PDF" : "Upload PDF"}</span>
                    </Button>
                  </div>
                </div>

                {/* Embedded Live PDF Viewer (iframe) */}
                {t.has_pdf && isExpanded && (
                  <div className="border-b bg-card/50 p-3 space-y-2">
                    <div className="flex items-center justify-between text-xs px-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground flex items-center gap-1.5">
                          <FileText className="size-3.5 text-primary" /> Official Government Form (Embedded Viewer)
                        </span>
                        <span className="text-muted-foreground font-mono text-[11px]">
                          {t.pdf_filename || `${t.code}.pdf`}
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setFullscreenPdf({
                            code: t.code,
                            title: t.official_title,
                            url: `/backend/v1/admin/ops/form-templates/${encodeURIComponent(t.code)}/pdf`,
                          })
                        }
                        className="h-6 px-2 text-[11px] gap-1 font-semibold text-primary hover:bg-primary/10"
                      >
                        <Maximize2 className="size-3" /> Expand Fullscreen
                      </Button>
                    </div>
                    <div className="rounded-xl overflow-hidden border shadow-sm bg-muted/40 relative">
                      <iframe
                        src={`/backend/v1/admin/ops/form-templates/${encodeURIComponent(t.code)}/pdf#toolbar=1&navpanes=1`}
                        className="w-full h-[620px] rounded-xl border-0 bg-white dark:bg-zinc-950"
                        title={`Official PDF Template: ${t.official_title}`}
                      />
                    </div>
                  </div>
                )}

                <CardContent className="p-4">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>
                      Field Mappings: <strong>{t.field_mappings?.length || 0}</strong> input fields mapped
                    </span>
                    {t.detected_fields && t.detected_fields.length > 0 && (
                      <span className="font-mono text-[11px] text-primary">
                        {t.detected_fields.length} AcroForm fields detected
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── MODAL: UPLOAD OR CHANGE PDF ────────────────────────────────────── */}
      {uploadingPdfFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <Card className="w-full max-w-lg shadow-2xl border bg-card">
            <CardHeader className="pb-3 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-bold text-foreground">
                    Upload Official PDF Form Template
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Attach or replace the government form template for{" "}
                    <strong className="font-mono text-primary">{uploadingPdfFor}</strong>
                  </CardDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setUploadingPdfFor(null);
                    setPdfFile(null);
                  }}
                  className="size-8 p-0"
                >
                  <X className="size-4" />
                </Button>
              </div>
            </CardHeader>

            <CardContent className="p-5 space-y-4">
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  const file = e.dataTransfer.files?.[0];
                  if (file && (file.type === "application/pdf" || file.name.endsWith(".pdf"))) {
                    setPdfFile(file);
                  } else {
                    toast.error("Please drop a valid .pdf file.");
                  }
                }}
                className="flex flex-col items-center justify-center border-2 border-dashed border-primary/30 rounded-xl p-8 text-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-all"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,.pdf"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setPdfFile(file);
                  }}
                />
                <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-3">
                  <UploadCloud className="size-6" />
                </div>
                {pdfFile && previewUploadUrl ? (
                  <div className="space-y-2 w-full">
                    <div className="flex items-center justify-between px-1">
                      <div className="text-left">
                        <p className="text-xs font-bold text-foreground">{pdfFile.name}</p>
                        <p className="text-[11px] text-muted-foreground font-mono">
                          {Math.round(pdfFile.size / 1024)} KB • Previewing selected document
                        </p>
                      </div>
                      <span className="text-[11px] text-primary underline">Click to choose another</span>
                    </div>
                    <div className="rounded-lg overflow-hidden border shadow-xs h-60 bg-white">
                      <iframe
                        src={`${previewUploadUrl}#toolbar=0&navpanes=0`}
                        className="w-full h-full border-0"
                        title="Selected PDF Preview"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">Click to browse or drag and drop</p>
                    <p className="text-xs text-muted-foreground">Official government application sheet (.pdf)</p>
                  </div>
                )}
              </div>

              <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
                <p className="font-semibold text-foreground">What happens when you upload:</p>
                <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                  <li>The PDF is securely cached on the server as the official template.</li>
                  <li>AcroForm interactive fields and page count are automatically extracted.</li>
                  <li>Applicants and employers can generate, inspect, and fill this exact document.</li>
                </ul>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setUploadingPdfFor(null);
                    setPdfFile(null);
                  }}
                  disabled={uploadingPdf}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleUploadPdf}
                  disabled={!pdfFile || uploadingPdf}
                  className="gap-1.5 font-semibold"
                >
                  {uploadingPdf ? (
                    <>
                      <Loader2 className="size-3.5 animate-spin" /> Uploading &amp; Processing...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="size-3.5" /> Upload &amp; Save PDF
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── FULLSCREEN PDF VIEWER MODAL ────────────────────────────────────── */}
      {fullscreenPdf && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-2 sm:p-4">
          <div className="w-full h-full max-w-6xl max-h-[94vh] flex flex-col rounded-2xl border bg-card shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b bg-muted/40 shrink-0">
              <div className="flex items-center gap-2.5">
                <span className="font-mono text-xs font-black uppercase text-primary bg-primary/10 px-2 py-0.5 rounded">
                  {fullscreenPdf.code}
                </span>
                <h3 className="text-sm font-bold text-foreground truncate max-w-lg">
                  {fullscreenPdf.title}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={fullscreenPdf.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg border bg-background px-3 py-1 text-xs font-medium hover:bg-muted transition-colors shadow-2xs"
                >
                  <ExternalLink className="size-3.5" />
                  <span>Open in Tab</span>
                </a>
                <a
                  href={fullscreenPdf.url}
                  download={`${fullscreenPdf.code}.pdf`}
                  className="inline-flex items-center gap-1.5 rounded-lg border bg-background px-3 py-1 text-xs font-medium hover:bg-muted transition-colors shadow-2xs"
                >
                  <Download className="size-3.5" />
                  <span>Download</span>
                </a>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFullscreenPdf(null)}
                  className="size-8 p-0 ml-1 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-4" />
                </Button>
              </div>
            </div>
            <div className="flex-1 min-h-0 bg-zinc-900 p-1">
              <iframe
                src={`${fullscreenPdf.url}#toolbar=1&navpanes=1`}
                className="w-full h-full rounded-xl border-0 bg-white"
                title={`Fullscreen PDF: ${fullscreenPdf.title}`}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
