"use client";

import { useCallback, useEffect, useState, useMemo, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  FileText,
  HelpCircle,
  ListChecks,
  Loader2,
  Plus,
  Save,
  ShieldAlert,
  Trash2,
  ExternalLink,
  Edit2,
  Search,
  Filter,
  Check,
  X,
  Layers,
  Sparkles,
  RefreshCw,
  UploadCloud,
  FileCheck,
  Download,
  Eye,
  FileUp,
  Maximize2,
  Minimize2,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { toast } from "sonner";
import {
  fetchScopeDetails,
  updateScopeDetails,
  uploadFormTemplatePdf,
  type AdminScopeDetails,
  type IntakeQuestion,
  type DocumentRequirement,
  type FormTemplateDetail,
  type EligibilityRule,
} from "@/lib/api/jurisdictions";

type ActiveTab = "intake" | "forms" | "documents" | "eligibility";

export default function RouteEditorPage() {
  const params = useParams<{ code: string; routeCode: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const { lang, t } = useI18n();

  const jurisdictionCode = (params?.code || "").toUpperCase();
  const routeCode = (params?.routeCode || "").toLowerCase();
  const initialAction = searchParams?.get("action") || "";

  const [details, setDetails] = useState<AdminScopeDetails | null>(null);
  const [selectedAction, setSelectedAction] = useState<string>(initialAction);
  const selectedActionRef = useRef<string>(initialAction);
  selectedActionRef.current = selectedAction;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>("intake");

  // Working state for editing
  const [questions, setQuestions] = useState<IntakeQuestion[]>([]);
  const [forms, setForms] = useState<FormTemplateDetail[]>([]);
  const [documents, setDocuments] = useState<DocumentRequirement[]>([]);
  const [rules, setRules] = useState<EligibilityRule[]>([]);
  const [routeName, setRouteName] = useState("");
  const [routeDescription, setRouteDescription] = useState("");
  const [routeEnabled, setRouteEnabled] = useState(true);
  const [hasChanges, setHasChanges] = useState(false);

  // Question search & modal state
  const [questionSearch, setQuestionSearch] = useState("");
  const [editingQuestionIdx, setEditingQuestionIdx] = useState<number | null>(null);
  const [showQuestionModal, setShowQuestionModal] = useState(false);
  const [questionForm, setQuestionForm] = useState<IntakeQuestion>({
    key: "",
    section: "General Information",
    prompt: "",
    prompt_ja: "",
    type: "string",
    required: true,
  });

  // Form template modal state
  const [showFormModal, setShowFormModal] = useState(false);
  const [formTemplateForm, setFormTemplateForm] = useState<FormTemplateDetail>({
    code: "",
    version: "1.0",
    official_title: "",
    field_mappings: [],
  });
  const [newMappingField, setNewMappingField] = useState("");
  const [newMappingKey, setNewMappingKey] = useState("");

  // Document requirement modal state
  const [showDocModal, setShowDocModal] = useState(false);
  const [docForm, setDocForm] = useState<{
    code: string;
    name_en: string;
    name_ja: string;
    is_required: boolean;
    how_to_obtain: string;
    why_required: string;
  }>({
    code: "",
    name_en: "",
    name_ja: "",
    is_required: true,
    how_to_obtain: "",
    why_required: "",
  });

  // PDF Upload modal state
  const [uploadingPdfFor, setUploadingPdfFor] = useState<string | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Embedded PDF Viewer state
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
      const res = await uploadFormTemplatePdf(token, uploadingPdfFor, pdfFile, {
        jurisdiction_code: jurisdictionCode,
        visa_category_code: routeCode,
        action_code: selectedAction,
      });
      toast.success(res.message || `PDF uploaded successfully for ${uploadingPdfFor}!`);
      setUploadingPdfFor(null);
      setPdfFile(null);
      await loadData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to upload PDF");
    } finally {
      setUploadingPdf(false);
    }
  };

  const handleImportDetectedFields = (formCode: string, detectedFields: string[]) => {
    if (!detectedFields || detectedFields.length === 0) return;
    setForms((prev) =>
      prev.map((f) => {
        if (f.code !== formCode) return f;
        const currentMappings = f.field_mappings || [];
        const existingFieldNames = new Set(currentMappings.map((m) => m.form_field));
        const newMappings = [...currentMappings];
        for (const field of detectedFields) {
          if (!existingFieldNames.has(field)) {
            const matchedQuestion = questions.find(
              (q) =>
                q.key.toLowerCase() === field.toLowerCase() ||
                field.toLowerCase().includes(q.key.toLowerCase()),
            );
            newMappings.push({
              form_field: field,
              answer_key: matchedQuestion ? matchedQuestion.key : field,
              required: false,
            });
          }
        }
        return { ...f, field_mappings: newMappings };
      }),
    );
    setHasChanges(true);
    toast.success(`Imported ${detectedFields.length} detected fields into mappings!`);
  };

  // Load scope details from API
  const loadData = useCallback(
    async (actionToLoad?: string) => {
      if (!jurisdictionCode || !routeCode) return;
      setLoading(true);
      setError(null);
      try {
        const targetAction = actionToLoad || selectedActionRef.current || undefined;
        const data = await fetchScopeDetails(
          token,
          jurisdictionCode,
          routeCode,
          targetAction,
        );
        setDetails(data);
        const curAction = data.case_action?.code || data.available_actions[0]?.code || "";
        setSelectedAction(curAction);
        selectedActionRef.current = curAction;
        setQuestions(data.intake_questions || []);
        setForms(data.form_templates || []);
        setDocuments(data.document_requirements || []);
        setRules(data.eligibility_rules || []);
        setRouteName(data.visa_category.name);
        setRouteDescription(data.visa_category.description || "");
        setRouteEnabled(data.visa_category.is_enabled);
        setHasChanges(false);

        // Auto-expand PDF viewer for forms with attached PDF
        setExpandedPdfForms((prev) => {
          const updated = { ...prev };
          for (const f of data.form_templates || []) {
            if (f.has_pdf && updated[f.code] === undefined) {
              updated[f.code] = true;
            }
          }
          return updated;
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load route details");
      } finally {
        setLoading(false);
      }
    },
    [token, jurisdictionCode, routeCode],
  );

  useEffect(() => {
    if (authLoading) return;
    void loadData(initialAction || undefined);
  }, [authLoading, loadData, initialAction]);

  // Handle switching application type
  const handleSelectAction = (actionCode: string) => {
    if (actionCode === selectedAction) return;
    if (hasChanges) {
      if (!confirm("You have unsaved changes. Discard and switch application type?")) {
        return;
      }
    }
    setSelectedAction(actionCode);
    selectedActionRef.current = actionCode;
    void loadData(actionCode);
  };

  // Save all changes
  const handleSaveAll = async () => {
    if (!token) {
      toast.error("You must be signed in as staff or admin to save changes.");
      return;
    }
    if (!details) return;
    setSaving(true);
    try {
      const updated = await updateScopeDetails(token, {
        jurisdiction_code: jurisdictionCode,
        visa_category_code: routeCode,
        action_code: selectedAction,
        category_name: routeName,
        category_description: routeDescription,
        is_enabled: routeEnabled,
        intake_questions: questions,
        document_requirements: documents,
        form_templates: forms,
        eligibility_rules: rules,
      });
      setDetails(updated);
      setHasChanges(false);
      toast.success("Route configuration saved & published to live system!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  // Filter questions
  const filteredQuestions = useMemo(() => {
    if (!questionSearch.trim()) return questions;
    const q = questionSearch.toLowerCase();
    return questions.filter(
      (item) =>
        item.key.toLowerCase().includes(q) ||
        item.prompt.toLowerCase().includes(q) ||
        (item.section && item.section.toLowerCase().includes(q)),
    );
  }, [questions, questionSearch]);

  // Group questions by section
  const questionSections = useMemo(() => {
    const map = new Map<string, IntakeQuestion[]>();
    for (const q of filteredQuestions) {
      const sec = q.section || "General";
      if (!map.has(sec)) map.set(sec, []);
      map.get(sec)!.push(q);
    }
    return Array.from(map.entries());
  }, [filteredQuestions]);

  // Add / Edit Question
  const handleSaveQuestion = () => {
    if (!questionForm.key.trim() || !questionForm.prompt.trim()) {
      toast.error("Question key and prompt are required");
      return;
    }
    const cleanKey = questionForm.key.trim().toLowerCase().replace(/\s+/g, "_");
    const updated = [...questions];
    if (editingQuestionIdx !== null) {
      updated[editingQuestionIdx] = { ...questionForm, key: cleanKey };
    } else {
      updated.push({ ...questionForm, key: cleanKey });
    }
    setQuestions(updated);
    setHasChanges(true);
    setShowQuestionModal(false);
    setEditingQuestionIdx(null);
    toast.success(editingQuestionIdx !== null ? "Question updated" : "Question added");
  };

  const handleDeleteQuestion = (idx: number) => {
    if (!confirm("Are you sure you want to delete this intake question?")) return;
    const updated = questions.filter((_, i) => i !== idx);
    setQuestions(updated);
    setHasChanges(true);
    toast.success("Question deleted");
  };

  // Add / Edit Document
  const handleSaveDocument = () => {
    if (!docForm.code.trim() || !docForm.name_en.trim()) {
      toast.error("Document code and English title are required");
      return;
    }
    const cleanCode = docForm.code.trim().toLowerCase().replace(/\s+/g, "_");
    const newDoc: DocumentRequirement = {
      code: cleanCode,
      name: docForm.name_ja ? { en: docForm.name_en, ja: docForm.name_ja } : docForm.name_en,
      is_required: docForm.is_required,
      how_to_obtain: docForm.how_to_obtain,
      why_required: docForm.why_required,
    };
    setDocuments([...documents, newDoc]);
    setHasChanges(true);
    setShowDocModal(false);
    toast.success("Document requirement added");
  };

  const handleDeleteDocument = (idx: number) => {
    if (!confirm("Are you sure you want to delete this document requirement?")) return;
    setDocuments(documents.filter((_, i) => i !== idx));
    setHasChanges(true);
    toast.success("Document removed");
  };

  // Add Form Mapping
  const handleAddFormMapping = () => {
    if (!newMappingField.trim() || !newMappingKey.trim()) return;
    const mappings = formTemplateForm.field_mappings || [];
    setFormTemplateForm({
      ...formTemplateForm,
      field_mappings: [
        ...mappings,
        {
          form_field: newMappingField.trim(),
          answer_key: newMappingKey.trim(),
          required: true,
        },
      ],
    });
    setNewMappingField("");
    setNewMappingKey("");
  };

  const handleSaveFormTemplate = () => {
    if (!formTemplateForm.code.trim() || !formTemplateForm.official_title.trim()) {
      toast.error("Form code and official title are required");
      return;
    }
    setForms([...forms, formTemplateForm]);
    setHasChanges(true);
    setShowFormModal(false);
    toast.success("Form template added");
  };

  const handleDeleteFormTemplate = (idx: number) => {
    if (!confirm("Are you sure you want to delete this form template?")) return;
    setForms(forms.filter((_, i) => i !== idx));
    setHasChanges(true);
    toast.success("Form template deleted");
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Loader2 className="size-8 animate-spin text-primary" />
        <p className="text-sm font-medium text-muted-foreground">Loading visa route configuration...</p>
      </div>
    );
  }

  if (error || !details) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 py-8">
        <Button variant="outline" size="sm" onClick={() => router.push("/admin/jurisdictions")}>
          <ArrowLeft className="size-4 mr-1.5" /> Back to Jurisdictions
        </Button>
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="p-6 text-center space-y-3">
            <h2 className="text-base font-bold text-red-600">Failed to Load Route</h2>
            <p className="text-xs text-muted-foreground">{error || "Route not found"}</p>
            <div>
              <Button size="sm" variant="outline" onClick={() => void loadData()}>
                <RefreshCw className="size-3.5 mr-1.5" /> Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      {/* ── TOP HEADER & BREADCRUMBS ────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div>
          <nav className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <Link href="/admin/jurisdictions" className="hover:text-foreground transition-colors">
              Jurisdictions
            </Link>
            <ChevronRight className="size-3" />
            <Link href="/admin/jurisdictions" className="hover:text-foreground transition-colors font-medium">
              {details.jurisdiction.name} ({details.jurisdiction.code})
            </Link>
            <ChevronRight className="size-3" />
            <span className="text-foreground font-semibold font-mono">{routeCode}</span>
          </nav>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-black tracking-tight text-foreground">{routeName}</h1>
            <Badge tone="muted" className="font-mono text-xs uppercase tracking-wider">
              {routeCode}
            </Badge>
            <button
              type="button"
              onClick={() => {
                setRouteEnabled(!routeEnabled);
                setHasChanges(true);
              }}
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-all ${
                routeEnabled
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20"
                  : "border-border bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              <span
                className={`size-2 rounded-full ${
                  routeEnabled ? "bg-emerald-500" : "bg-muted-foreground"
                }`}
              />
              <span>{routeEnabled ? "Route Active (On)" : "Route Disabled (Off)"}</span>
            </button>
          </div>
          {routeDescription && (
            <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl">{routeDescription}</p>
          )}
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          {hasChanges && (
            <span className="flex items-center gap-1 text-xs font-semibold text-amber-600 dark:text-amber-400 animate-pulse">
              <span className="size-2 rounded-full bg-amber-500" />
              Unsaved changes
            </span>
          )}
          <Button
            onClick={() => void handleSaveAll()}
            disabled={saving || !hasChanges}
            size="sm"
            className="gap-1.5 text-xs font-semibold shadow-xs"
          >
            {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
            <span>{saving ? "Saving..." : "Save Changes"}</span>
          </Button>
        </div>
      </div>

      {/* ── APPLICATION TYPES BAR (NESTED INSIDE VISA ROUTE) ──────────────────── */}
      <Card className="border shadow-xs bg-card/60 backdrop-blur-sm overflow-hidden">
        <div className="bg-muted/30 border-b px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Layers className="size-4 text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider text-foreground">
              Application Types for {details.visa_category.name}:
            </span>
          </div>
          <span className="text-[11px] text-muted-foreground">
            Selecting an application type configures its specific intake questionnaire &amp; official PDF form.
          </span>
        </div>

        <CardContent className="p-3 flex flex-wrap items-center gap-2">
          {details.available_actions.map((act) => {
            const isActive = act.code.toLowerCase() === selectedAction.toLowerCase();
            return (
              <button
                key={act.id}
                type="button"
                onClick={() => handleSelectAction(act.code)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border ${
                  isActive
                    ? "bg-primary text-primary-foreground border-primary shadow-xs"
                    : "bg-background text-muted-foreground hover:bg-muted/80 hover:text-foreground border-border"
                }`}
              >
                <span>{act.name}</span>
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    isActive
                      ? "bg-primary-foreground/20 text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {act.code}
                </span>
                {isActive && <CheckCircle2 className="size-3.5" />}
              </button>
            );
          })}
        </CardContent>
      </Card>

      {/* ── CONFIGURATION TABS ──────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b">
        <button
          type="button"
          onClick={() => setActiveTab("intake")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
            activeTab === "intake"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <HelpCircle className="size-4" />
          <span>Intake Questions</span>
          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full font-mono">
            {questions.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("forms")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
            activeTab === "forms"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="size-4" />
          <span>Official PDF Forms</span>
          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full font-mono">
            {forms.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("documents")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
            activeTab === "documents"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ListChecks className="size-4" />
          <span>Document Checklist</span>
          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full font-mono">
            {documents.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("eligibility")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all ${
            activeTab === "eligibility"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ShieldAlert className="size-4" />
          <span>Eligibility Rules</span>
          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded-full font-mono">
            {rules.length}
          </span>
        </button>
      </div>

      {/* ── TAB 1: INTAKE QUESTIONS ─────────────────────────────────────────── */}
      {activeTab === "intake" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <input
                type="search"
                value={questionSearch}
                onChange={(e) => setQuestionSearch(e.target.value)}
                placeholder="Search questions by key, prompt, or section..."
                className="h-8.5 w-full rounded-lg border bg-background pl-8.5 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-primary"
              />
            </div>

            <Button
              size="sm"
              onClick={() => {
                setQuestionForm({
                  key: "",
                  section: "General Information",
                  prompt: "",
                  prompt_ja: "",
                  type: "string",
                  required: true,
                });
                setEditingQuestionIdx(null);
                setShowQuestionModal(true);
              }}
              className="gap-1.5 text-xs self-end sm:self-auto font-semibold"
            >
              <Plus className="size-3.5" /> Add Intake Question
            </Button>
          </div>

          {questionSections.length === 0 ? (
            <Card className="border-dashed p-8 text-center">
              <HelpCircle className="mx-auto size-8 text-muted-foreground opacity-50" />
              <p className="mt-2 text-sm font-semibold text-foreground">No Intake Questions</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add questions to create the questionnaire applicants will answer for this visa.
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              {questionSections.map(([sectionName, sectionQuestions]) => (
                <div key={sectionName} className="space-y-2">
                  <h3 className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <span>{sectionName}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted">
                      {sectionQuestions.length}
                    </span>
                  </h3>

                  <div className="grid gap-2">
                    {sectionQuestions.map((q) => {
                      const globalIdx = questions.indexOf(q);
                      return (
                        <div
                          key={q.key}
                          className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border bg-card p-3 shadow-2xs hover:border-primary/40 transition-colors"
                        >
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-mono text-xs font-bold text-foreground bg-muted/60 px-1.5 py-0.5 rounded">
                                {q.key}
                              </span>
                              <Badge tone="muted" className="text-[10px] uppercase font-mono">
                                {q.type}
                              </Badge>
                              {q.required ? (
                                <Badge tone="warning" className="text-[10px]">
                                  Required
                                </Badge>
                              ) : (
                                <span className="text-[10px] text-muted-foreground">Optional</span>
                              )}
                            </div>
                            <p className="text-xs font-medium text-foreground">{q.prompt}</p>
                            {q.prompt_ja && (
                              <p className="text-[11px] text-muted-foreground">{q.prompt_ja}</p>
                            )}
                            {q.options && q.options.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {q.options.slice(0, 6).map((opt) => (
                                  <span
                                    key={opt}
                                    className="text-[10px] font-mono rounded bg-accent px-1.5 py-0.2 text-accent-foreground"
                                  >
                                    {opt}
                                  </span>
                                ))}
                                {q.options.length > 6 && (
                                  <span className="text-[10px] text-muted-foreground">
                                    +{q.options.length - 6} more
                                  </span>
                                )}
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setQuestionForm({ ...q });
                                setEditingQuestionIdx(globalIdx);
                                setShowQuestionModal(true);
                              }}
                              className="h-8 px-2.5 text-xs"
                            >
                              <Edit2 className="size-3.5 mr-1" /> Edit
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteQuestion(globalIdx)}
                              className="h-8 px-2.5 text-xs text-red-600 hover:text-red-700 hover:bg-red-500/10"
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: OFFICIAL PDF FORMS ────────────────────────────────────────── */}
      {activeTab === "forms" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Official government PDF forms generated from intake answers when this application is unlocked.
            </p>
            <Button
              size="sm"
              onClick={() => {
                setFormTemplateForm({
                  code: "",
                  version: "1.0",
                  official_title: "",
                  field_mappings: [],
                });
                setShowFormModal(true);
              }}
              className="gap-1.5 text-xs font-semibold"
            >
              <Plus className="size-3.5" /> Add Form Template
            </Button>
          </div>

          {forms.length === 0 ? (
            <Card className="border-dashed p-8 text-center">
              <FileText className="mx-auto size-8 text-muted-foreground opacity-50" />
              <p className="mt-2 text-sm font-semibold text-foreground">No Official Form Templates</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add an official form template code (e.g. MOJ-COE-WORK) and its field mappings.
              </p>
            </Card>
          ) : (
            <div className="grid gap-4">
              {forms.map((f, fIdx) => (
                <Card key={f.code} className="border shadow-xs overflow-hidden">
                  <CardHeader className="bg-muted/20 pb-3 border-b">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-black uppercase text-foreground bg-primary/10 text-primary px-2 py-0.5 rounded-md">
                            {f.code}
                          </span>
                          <span className="text-xs font-bold text-muted-foreground font-mono">
                            v{f.version}
                          </span>
                        </div>
                        <CardTitle className="text-sm font-bold text-foreground">
                          {f.official_title}
                        </CardTitle>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteFormTemplate(fIdx)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-500/10 h-8 px-2"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </CardHeader>

                  {/* PDF Document Status & Action Strip */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-accent/30 px-4 py-2.5 border-b text-xs">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      {f.has_pdf ? (
                        <>
                          <Badge tone="success" className="gap-1 font-semibold text-[11px]">
                            <FileCheck className="size-3" /> PDF Attached
                          </Badge>
                          <span className="font-mono text-muted-foreground truncate max-w-[220px]">
                            {f.pdf_filename || `${f.code}.pdf`}
                          </span>
                          {f.pdf_pages && (
                            <span className="text-muted-foreground">• {f.pdf_pages} pages</span>
                          )}
                          {f.pdf_filesize && (
                            <span className="text-muted-foreground">
                              • {Math.round(f.pdf_filesize / 1024)} KB
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
                      {f.has_pdf && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => togglePdfExpand(f.code)}
                            className="gap-1.5 h-7 px-2.5 text-xs font-semibold hover:bg-muted"
                          >
                            {expandedPdfForms[f.code] ? (
                              <>
                                <ChevronUp className="size-3.5 text-primary" />
                                <span>Hide PDF</span>
                              </>
                            ) : (
                              <>
                                <Eye className="size-3.5 text-primary" />
                                <span>View PDF</span>
                              </>
                            )}
                          </Button>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setFullscreenPdf({
                                code: f.code,
                                title: f.official_title,
                                url: `/backend/v1/admin/ops/form-templates/${encodeURIComponent(f.code)}/pdf`,
                              })
                            }
                            className="gap-1 h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                            title="Open in Fullscreen Viewer"
                          >
                            <Maximize2 className="size-3.5" />
                            <span className="hidden sm:inline">Fullscreen</span>
                          </Button>

                          <a
                            href={`/backend/v1/admin/ops/form-templates/${encodeURIComponent(f.code)}/pdf`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted transition-colors shadow-2xs text-muted-foreground hover:text-foreground"
                            title="Open in new browser tab"
                          >
                            <ExternalLink className="size-3" />
                          </a>
                        </>
                      )}

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenPdfUpload(f.code)}
                        className="gap-1.5 h-7 px-2.5 text-xs font-semibold bg-background shadow-2xs hover:border-primary/50 text-primary"
                      >
                        <UploadCloud className="size-3.5" />
                        <span>{f.has_pdf ? "Change PDF" : "Upload PDF"}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Embedded Live PDF Viewer (iframe) */}
                  {f.has_pdf && expandedPdfForms[f.code] && (
                    <div className="border-b bg-card/50 p-3 space-y-2">
                      <div className="flex items-center justify-between text-xs px-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-foreground flex items-center gap-1.5">
                            <FileText className="size-3.5 text-primary" /> Official Government Form (Embedded Viewer)
                          </span>
                          <span className="text-muted-foreground font-mono text-[11px]">
                            {f.pdf_filename || `${f.code}.pdf`}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-muted-foreground hidden sm:inline">
                            Interactive document preview
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setFullscreenPdf({
                                code: f.code,
                                title: f.official_title,
                                url: `/backend/v1/admin/ops/form-templates/${encodeURIComponent(f.code)}/pdf`,
                              })
                            }
                            className="h-6 px-2 text-[11px] gap-1 font-semibold text-primary hover:bg-primary/10"
                          >
                            <Maximize2 className="size-3" /> Fullscreen
                          </Button>
                        </div>
                      </div>
                      <div className="rounded-xl overflow-hidden border shadow-sm bg-muted/40 relative">
                        <iframe
                          src={`/backend/v1/admin/ops/form-templates/${encodeURIComponent(f.code)}/pdf#toolbar=1&navpanes=1`}
                          className="w-full h-[640px] rounded-xl border-0 bg-white dark:bg-zinc-950"
                          title={`Official PDF Template Preview: ${f.official_title}`}
                        />
                      </div>
                    </div>
                  )}

                  {!f.has_pdf && (
                    <div
                      onClick={() => handleOpenPdfUpload(f.code)}
                      className="p-6 border-b border-dashed bg-muted/10 text-center cursor-pointer hover:bg-primary/5 transition-colors group"
                    >
                      <UploadCloud className="mx-auto size-7 text-muted-foreground group-hover:text-primary transition-colors mb-2" />
                      <p className="text-xs font-bold text-foreground">No Official PDF File Attached</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5 max-w-md mx-auto">
                        Click here to upload the official immigration sheet (.pdf). It will be rendered directly inside this viewer and used for applicant form generation.
                      </p>
                    </div>
                  )}

                  <CardContent className="p-4 space-y-3">
                    {/* Detected interactive fields banner */}
                    {f.detected_fields && f.detected_fields.length > 0 && (
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-lg bg-primary/5 border border-primary/20 text-xs">
                        <div className="flex items-center gap-1.5 text-primary">
                          <Sparkles className="size-3.5 shrink-0" />
                          <span>
                            Detected <strong>{f.detected_fields.length}</strong> interactive PDF fields in uploaded file.
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleImportDetectedFields(f.code, f.detected_fields!)}
                          className="h-6 text-[11px] font-semibold gap-1 text-primary border-primary/30 hover:bg-primary/10 self-start sm:self-auto"
                        >
                          <Plus className="size-3" /> Import Fields to Matrix
                        </Button>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Field-to-Intake Mapping Matrix ({f.field_mappings?.length || 0} fields mapped)
                      </span>
                    </div>

                    <div className="rounded-lg border overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-muted/40 border-b text-muted-foreground font-semibold">
                          <tr>
                            <th className="p-2.5">PDF Form Field</th>
                            <th className="p-2.5">Mapped Answer Key</th>
                            <th className="p-2.5 text-right">Required</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {(f.field_mappings || []).map((m, mIdx) => (
                            <tr key={mIdx} className="hover:bg-muted/20 transition-colors">
                              <td className="p-2.5 font-mono font-semibold text-foreground">
                                {m.form_field}
                              </td>
                              <td className="p-2.5 font-mono text-primary flex items-center gap-1.5">
                                <span>↳</span>
                                <span>{m.answer_key}</span>
                              </td>
                              <td className="p-2.5 text-right">
                                {m.required ? (
                                  <Badge tone="warning" className="text-[10px]">
                                    Required
                                  </Badge>
                                ) : (
                                  <span className="text-[10px] text-muted-foreground">Optional</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: DOCUMENT CHECKLIST ────────────────────────────────────────── */}
      {activeTab === "documents" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Required proof documents and evidence applicants must gather for this application.
            </p>
            <Button
              size="sm"
              onClick={() => {
                setDocForm({
                  code: "",
                  name_en: "",
                  name_ja: "",
                  is_required: true,
                  how_to_obtain: "",
                  why_required: "",
                });
                setShowDocModal(true);
              }}
              className="gap-1.5 text-xs font-semibold"
            >
              <Plus className="size-3.5" /> Add Required Document
            </Button>
          </div>

          {documents.length === 0 ? (
            <Card className="border-dashed p-8 text-center">
              <ListChecks className="mx-auto size-8 text-muted-foreground opacity-50" />
              <p className="mt-2 text-sm font-semibold text-foreground">No Document Requirements</p>
              <p className="text-xs text-muted-foreground mt-1">
                Define the certificate, tax record, and contract items required by immigration.
              </p>
            </Card>
          ) : (
            <div className="grid gap-3">
              {documents.map((doc, dIdx) => {
                const titleEn = typeof doc.name === "object" ? doc.name.en : doc.name;
                const titleJa = typeof doc.name === "object" ? doc.name.ja : undefined;
                return (
                  <div
                    key={doc.code || dIdx}
                    className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 rounded-xl border bg-card p-3.5 shadow-2xs hover:border-primary/40 transition-colors"
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-foreground bg-muted/60 px-1.5 py-0.5 rounded">
                          {doc.code}
                        </span>
                        {doc.is_required ? (
                          <Badge tone="warning" className="text-[10px]">
                            Mandatory
                          </Badge>
                        ) : (
                          <Badge tone="muted" className="text-[10px]">
                            Conditional
                          </Badge>
                        )}
                        {doc.show_when && (
                          <span className="text-[10px] font-mono text-muted-foreground bg-accent px-1.5 py-0.5 rounded">
                            Rule: {JSON.stringify(doc.show_when)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-bold text-foreground">{titleEn}</p>
                      {titleJa && <p className="text-[11px] text-muted-foreground">{titleJa}</p>}
                      {typeof doc.how_to_obtain === "string" && (
                        <p className="text-[11px] text-muted-foreground mt-1">
                          <span className="font-semibold text-foreground">How to obtain: </span>
                          {doc.how_to_obtain}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-auto">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteDocument(dIdx)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-500/10 h-8 px-2"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 4: ELIGIBILITY RULES ────────────────────────────────────────── */}
      {activeTab === "eligibility" && (
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Deterministic statutory criteria rules (e.g. minimum remuneration, university degree prerequisite).
          </p>

          {rules.length === 0 ? (
            <Card className="border-dashed p-8 text-center">
              <ShieldAlert className="mx-auto size-8 text-muted-foreground opacity-50" />
              <p className="mt-2 text-sm font-semibold text-foreground">No Eligibility Rules</p>
              <p className="text-xs text-muted-foreground mt-1">
                Statutory threshold rules screen applicants before filing to prevent formal rejection.
              </p>
            </Card>
          ) : (
            <div className="grid gap-3">
              {rules.map((r, rIdx) => (
                <div
                  key={rIdx}
                  className="flex items-center justify-between gap-3 rounded-xl border bg-card p-3 shadow-2xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-foreground">{r.key}</span>
                      <Badge tone="info" className="text-[10px] font-mono">
                        {r.operator}
                      </Badge>
                      <span className="font-mono text-xs text-muted-foreground">
                        {JSON.stringify(r.value)}
                      </span>
                    </div>
                    {r.message && <p className="text-xs text-muted-foreground">{r.message}</p>}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setRules(rules.filter((_, i) => i !== rIdx));
                      setHasChanges(true);
                    }}
                    className="text-red-600 hover:text-red-700 hover:bg-red-500/10 h-8 px-2"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── QUESTION MODAL ─────────────────────────────────────────────────── */}
      {showQuestionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <Card className="w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl border">
            <CardHeader className="border-b pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold text-foreground">
                  {editingQuestionIdx !== null ? "Edit Intake Question" : "Add Intake Question"}
                </CardTitle>
                <CardDescription className="text-xs">
                  Define the question key and prompt shown to applicants in Step 2.
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowQuestionModal(false)}
                className="size-8 p-0"
              >
                <X className="size-4" />
              </Button>
            </CardHeader>

            <CardContent className="p-4 space-y-3.5 text-xs">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Question Key (Unique ID)</span>
                  <input
                    required
                    value={questionForm.key}
                    onChange={(e) => setQuestionForm({ ...questionForm, key: e.target.value })}
                    placeholder="e.g. passport_number"
                    className="h-8.5 rounded-lg border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Section Header</span>
                  <input
                    value={questionForm.section || ""}
                    onChange={(e) => setQuestionForm({ ...questionForm, section: e.target.value })}
                    placeholder="e.g. Personal & Identity"
                    className="h-8.5 rounded-lg border bg-background px-3 text-xs outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Prompt (English)</span>
                <textarea
                  required
                  rows={2}
                  value={questionForm.prompt}
                  onChange={(e) => setQuestionForm({ ...questionForm, prompt: e.target.value })}
                  placeholder="What is your passport number?"
                  className="rounded-lg border bg-background p-2.5 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Prompt (Japanese - Optional)</span>
                <input
                  value={questionForm.prompt_ja || ""}
                  onChange={(e) => setQuestionForm({ ...questionForm, prompt_ja: e.target.value })}
                  placeholder="旅券番号を入力してください"
                  className="h-8.5 rounded-lg border bg-background px-3 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Data Type</span>
                  <select
                    value={questionForm.type}
                    onChange={(e) =>
                      setQuestionForm({ ...questionForm, type: e.target.value as IntakeQuestion["type"] })
                    }
                    className="h-8.5 rounded-lg border bg-background px-2.5 text-xs outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="string">Text (Short String)</option>
                    <option value="text">Long Text / Paragraph</option>
                    <option value="enum">Dropdown / Single Choice (Enum)</option>
                    <option value="date">Calendar Date (YYYY-MM-DD)</option>
                    <option value="integer">Number / Integer</option>
                    <option value="boolean">Yes / No (Boolean)</option>
                  </select>
                </label>

                <div className="flex items-center gap-2 pt-6">
                  <input
                    type="checkbox"
                    id="req_check"
                    checked={Boolean(questionForm.required)}
                    onChange={(e) => setQuestionForm({ ...questionForm, required: e.target.checked })}
                    className="size-4 rounded border"
                  />
                  <label htmlFor="req_check" className="font-bold text-foreground cursor-pointer">
                    Mandatory / Required question
                  </label>
                </div>
              </div>

              {questionForm.type === "enum" && (
                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Options (Comma separated)</span>
                  <input
                    value={(questionForm.options || []).join(", ")}
                    onChange={(e) =>
                      setQuestionForm({
                        ...questionForm,
                        options: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      })
                    }
                    placeholder="e.g. bachelor_degree, master_degree, doctorate_phd"
                    className="h-8.5 rounded-lg border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>
              )}

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => setShowQuestionModal(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveQuestion}>
                  Save Question
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── FORM TEMPLATE MODAL ────────────────────────────────────────────── */}
      {showFormModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <Card className="w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl border">
            <CardHeader className="border-b pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold text-foreground">
                  Add Official PDF Form Template
                </CardTitle>
                <CardDescription className="text-xs">
                  Register a government form code and map its field boxes to intake keys.
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowFormModal(false)}
                className="size-8 p-0"
              >
                <X className="size-4" />
              </Button>
            </CardHeader>

            <CardContent className="p-4 space-y-3.5 text-xs">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Form Code (e.g. MOJ-COE-01)</span>
                  <input
                    required
                    value={formTemplateForm.code}
                    onChange={(e) => setFormTemplateForm({ ...formTemplateForm, code: e.target.value })}
                    placeholder="moj_coe_work"
                    className="h-8.5 rounded-lg border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>

                <label className="flex flex-col gap-1">
                  <span className="font-bold text-foreground">Version</span>
                  <input
                    value={formTemplateForm.version}
                    onChange={(e) =>
                      setFormTemplateForm({ ...formTemplateForm, version: e.target.value })
                    }
                    placeholder="2026-04"
                    className="h-8.5 rounded-lg border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>
              </div>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Official Title</span>
                <input
                  required
                  value={formTemplateForm.official_title}
                  onChange={(e) =>
                    setFormTemplateForm({ ...formTemplateForm, official_title: e.target.value })
                  }
                  placeholder="Application for Certificate of Eligibility (在留資格認定証明書交付申請書)"
                  className="h-8.5 rounded-lg border bg-background px-3 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              {/* Add Field Mapping */}
              <div className="border-t pt-3 space-y-2">
                <span className="font-bold text-foreground uppercase tracking-wider text-[11px]">
                  Add Field Mapping
                </span>
                <div className="flex items-center gap-2">
                  <input
                    value={newMappingField}
                    onChange={(e) => setNewMappingField(e.target.value)}
                    placeholder="PDF Field (e.g. applicant_name)"
                    className="h-8 rounded-lg border bg-background px-2.5 font-mono text-xs flex-1 outline-none focus:ring-1 focus:ring-primary"
                  />
                  <input
                    value={newMappingKey}
                    onChange={(e) => setNewMappingKey(e.target.value)}
                    placeholder="Intake Key (e.g. full_name)"
                    className="h-8 rounded-lg border bg-background px-2.5 font-mono text-xs flex-1 outline-none focus:ring-1 focus:ring-primary"
                  />
                  <Button size="sm" type="button" onClick={handleAddFormMapping} className="h-8 px-2.5">
                    Map
                  </Button>
                </div>

                <div className="max-h-36 overflow-y-auto divide-y rounded-lg border">
                  {(formTemplateForm.field_mappings || []).map((m, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 text-[11px] font-mono">
                      <span>
                        {m.form_field} ➔ {m.answer_key}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setFormTemplateForm({
                            ...formTemplateForm,
                            field_mappings: formTemplateForm.field_mappings?.filter((_, i) => i !== idx),
                          })
                        }
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => setShowFormModal(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveFormTemplate}>
                  Save Form Template
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── DOCUMENT REQUIREMENT MODAL ──────────────────────────────────────── */}
      {showDocModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <Card className="w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl border">
            <CardHeader className="border-b pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold text-foreground">
                  Add Document Requirement
                </CardTitle>
                <CardDescription className="text-xs">
                  Define an evidence requirement for the applicant checklist.
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setShowDocModal(false)} className="size-8 p-0">
                <X className="size-4" />
              </Button>
            </CardHeader>

            <CardContent className="p-4 space-y-3.5 text-xs">
              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Document Code (Unique ID)</span>
                <input
                  required
                  value={docForm.code}
                  onChange={(e) => setDocForm({ ...docForm, code: e.target.value })}
                  placeholder="e.g. university_degree_certificate"
                  className="h-8.5 rounded-lg border bg-background px-3 font-mono text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Document Title (English)</span>
                <input
                  required
                  value={docForm.name_en}
                  onChange={(e) => setDocForm({ ...docForm, name_en: e.target.value })}
                  placeholder="University Graduation Certificate or Official Transcript"
                  className="h-8.5 rounded-lg border bg-background px-3 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Document Title (Japanese - Optional)</span>
                <input
                  value={docForm.name_ja}
                  onChange={(e) => setDocForm({ ...docForm, name_ja: e.target.value })}
                  placeholder="大学の卒業証明書又は卒業証書の写し"
                  className="h-8.5 rounded-lg border bg-background px-3 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">How to Obtain (Applicant Guidance)</span>
                <textarea
                  rows={2}
                  value={docForm.how_to_obtain}
                  onChange={(e) => setDocForm({ ...docForm, how_to_obtain: e.target.value })}
                  placeholder="Request an official sealed transcript or graduation diploma from your university registrar."
                  className="rounded-lg border bg-background p-2.5 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="font-bold text-foreground">Why Required (Statutory Purpose)</span>
                <textarea
                  rows={2}
                  value={docForm.why_required}
                  onChange={(e) => setDocForm({ ...docForm, why_required: e.target.value })}
                  placeholder="Proves statutory eligibility under Ministerial Ordinance criteria for Engineer status."
                  className="rounded-lg border bg-background p-2.5 text-xs outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="doc_req_check"
                  checked={docForm.is_required}
                  onChange={(e) => setDocForm({ ...docForm, is_required: e.target.checked })}
                  className="size-4 rounded border"
                />
                <label htmlFor="doc_req_check" className="font-bold text-foreground cursor-pointer">
                  Mandatory for all applicants
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <Button variant="outline" size="sm" onClick={() => setShowDocModal(false)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveDocument}>
                  Add Document
                </Button>
              </div>
            </CardContent>
          </Card>
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
                    Attach or replace the government form template for <strong className="font-mono text-primary">{uploadingPdfFor}</strong>
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
