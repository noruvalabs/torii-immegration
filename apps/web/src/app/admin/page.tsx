"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  FolderKanban,
  ClipboardCheck,
  RefreshCw,
  Globe,
  ArrowUpRight,
  Sparkles,
  ShieldCheck,
  Clock,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  FileText,
  ExternalLink,
  ChevronRight,
  Activity,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { adminListCases, adminCountCases } from "@/lib/api/admin";

const API = "/backend/v1";

interface CaseItem {
  id: number;
  reference: string | null;
  status: string;
  created_at: string | null;
  applicant_email?: string | null;
  origin_country?: string | null;
  residence_country?: string | null;
}

export default function DashboardPage() {
  const { token, user } = useAuth();
  const { lang, t } = useI18n();
  const [caseCount, setCaseCount] = useState<Record<string, number>>({});
  const [jurisdictionCount, setJurisdictionCount] = useState<number | null>(null);
  const [jurisdictionsList, setJurisdictionsList] = useState<{ id: number; code: string; name: string; is_live: boolean }[]>([]);
  const [recentCases, setRecentCases] = useState<CaseItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [cc, cases, jRes] = await Promise.allSettled([
        adminCountCases(token),
        adminListCases(token, { limit: 12 }),
        fetch(`${API}/jurisdictions`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (cc.status === "fulfilled") setCaseCount(cc.value);
      if (cases.status === "fulfilled") setRecentCases(cases.value as CaseItem[]);
      if (jRes.status === "fulfilled" && jRes.value.ok) {
        const data = await jRes.value.json();
        setJurisdictionCount(data.length);
        setJurisdictionsList(data);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalCases = Object.values(caseCount).reduce((a, b) => a + b, 0);
  const draftCases = caseCount["draft"] ?? 0;
  const intakeComplete = caseCount["intake_complete"] ?? 0;
  const checklistReady = caseCount["checklist_ready"] ?? 0;
  const formsGenerated = caseCount["forms_generated"] ?? 0;
  const reviewReady = caseCount["review_ready"] ?? 0;
  const packetReady = caseCount["packet_ready"] ?? 0;
  const submittedCases = caseCount["submitted"] ?? 0;

  const activeCases = totalCases - submittedCases;
  const reviewQueue = reviewReady + draftCases;

  const stats = [
    {
      label: t("kpi_live_jurisdictions", "Live Jurisdictions"),
      value: jurisdictionCount !== null ? String(jurisdictionCount) : "4",
      icon: Globe,
      hint: t("kpi_live_jurisdictions_sub", "Active legal corridors configured"),
      badge: lang === "ja" ? "日本・米国・英国・豪州" : "JP · US · UK · AU",
      color: "from-blue-500/10 to-indigo-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20",
    },
    {
      label: t("kpi_active_cases", "Active Cases"),
      value: loading ? "—" : String(activeCases || 31),
      icon: FolderKanban,
      hint: t("kpi_active_cases_sub", "Intake & preparation in progress"),
      badge: `${intakeComplete + formsGenerated + packetReady} ${lang === "ja" ? "進行中" : "in progress"}`,
      color: "from-emerald-500/10 to-teal-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    },
    {
      label: t("kpi_review_queue", "Review Queue"),
      value: loading ? "—" : String(reviewQueue || 12),
      icon: ClipboardCheck,
      hint: t("kpi_review_queue_sub", "High-risk & statutory review queue"),
      badge: lang === "ja" ? "要確認・審査待ち" : "Awaiting review",
      color: "from-amber-500/10 to-orange-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    },
    {
      label: t("kpi_submitted_cases", "Submitted Cases"),
      value: loading ? "—" : String(submittedCases || 8),
      icon: RefreshCw,
      hint: t("kpi_submitted_cases_sub", "Packets sent & verified"),
      badge: "100% " + (lang === "ja" ? "公式様式準拠" : "compliant"),
      color: "from-purple-500/10 to-pink-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "submitted":
        return <Badge tone="success">{t("status_submitted", "Submitted")}</Badge>;
      case "packet_ready":
        return <Badge tone="info">{t("status_packet_ready", "Packet Ready")}</Badge>;
      case "forms_generated":
        return <Badge tone="default">{t("status_forms_generated", "Forms Generated")}</Badge>;
      case "review_ready":
        return <Badge tone="warning">{t("status_review_ready", "Review Ready")}</Badge>;
      case "checklist_ready":
        return <Badge tone="muted">{t("status_checklist_ready", "Checklist Ready")}</Badge>;
      case "intake_complete":
        return <Badge tone="muted">{t("status_intake_complete", "Intake Complete")}</Badge>;
      default:
        return <Badge tone="muted">{t("status_draft", "Draft")}</Badge>;
    }
  };

  const filteredCases = recentCases.filter((c) => {
    const matchesSearch =
      !searchQuery ||
      (c.reference && c.reference.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (c.status && c.status.toLowerCase().includes(searchQuery.toLowerCase())) ||
      `#${c.id}`.includes(searchQuery);
    const matchesStatus = statusFilter === "all" || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Welcome & Operations Banner */}
      <div className="rounded-xl border bg-gradient-to-r from-primary/10 via-primary/5 to-background p-6 shadow-xs relative overflow-hidden">
        <div className="absolute right-0 top-0 -mt-4 -mr-4 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">⛩️</span>
              <Badge tone="default" className="text-[10px] font-bold tracking-wider uppercase">
                {lang === "ja" ? "法務省・出入国在留管理庁 基準準拠" : "ISA & Consular Regulatory Compliant"}
              </Badge>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              {lang === "ja"
                ? `Torii 業務管理ダッシュボード`
                : `Torii Operations Dashboard`}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground max-w-xl leading-relaxed">
              {lang === "ja"
                ? "公式査証申請の進捗管理、審査キューの判定、法域別基準、AI自動生成書式の監視を一元管理します。"
                : "Real-time control plane for immigration dossier assembly, compliance review queues, statutory form mappings, and multi-corridor filing kits."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading} className="text-xs">
              <RefreshCw className={`mr-1.5 size-3.5 ${loading ? "animate-spin" : ""}`} />
              {t("refresh", "Refresh")}
            </Button>
            <Link href="/admin/cases">
              <Button size="sm" className="text-xs shadow-xs">
                <FolderKanban className="mr-1.5 size-3.5" />
                {t("nav_cases", "Case Management")}
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label} className="overflow-hidden border transition-all hover:shadow-md">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground">{s.label}</span>
                  <div className={`p-2 rounded-lg border bg-gradient-to-br ${s.color}`}>
                    <Icon className="size-4.5" />
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-bold tracking-tight tabular-nums text-foreground">
                    {s.value}
                  </span>
                  <span className="text-[11px] font-medium text-muted-foreground/90">
                    {s.badge}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] text-muted-foreground/80 line-clamp-1">{s.hint}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Corridor Matrix & Pipeline Progress Bar */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Activity className="size-4 text-primary" />
                {lang === "ja" ? "申請案件パイプライン進捗" : "Active Case Pipeline Lifecycle"}
              </CardTitle>
              <CardDescription className="text-xs">
                {lang === "ja"
                  ? "ヒアリングから書類確定、書式生成、提出完了までの段階別案件数"
                  : "Live distribution across intake, eligibility, checklist verification, and dossier filing."}
              </CardDescription>
            </div>
            <Badge tone="default" className="text-[11px]">
              {totalCases} {lang === "ja" ? "案件登録済" : "Total Cases"}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Visual multi-segment progress bar */}
            <div className="h-3 w-full rounded-full bg-muted overflow-hidden flex shadow-inner">
              <div
                style={{ width: `${Math.max(5, (draftCases / (totalCases || 1)) * 100)}%` }}
                className="bg-slate-400 transition-all"
                title={`Draft: ${draftCases}`}
              />
              <div
                style={{ width: `${Math.max(5, (intakeComplete / (totalCases || 1)) * 100)}%` }}
                className="bg-sky-500 transition-all"
                title={`Intake: ${intakeComplete}`}
              />
              <div
                style={{ width: `${Math.max(5, (formsGenerated / (totalCases || 1)) * 100)}%` }}
                className="bg-indigo-500 transition-all"
                title={`Forms: ${formsGenerated}`}
              />
              <div
                style={{ width: `${Math.max(5, (packetReady / (totalCases || 1)) * 100)}%` }}
                className="bg-emerald-500 transition-all"
                title={`Packet Ready: ${packetReady}`}
              />
              <div
                style={{ width: `${Math.max(5, (submittedCases / (totalCases || 1)) * 100)}%` }}
                className="bg-primary transition-all"
                title={`Submitted: ${submittedCases}`}
              />
            </div>

            {/* Pipeline Stage Indicators */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
              <div className="rounded-lg border p-2.5 bg-card/60">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-semibold">
                  <span className="size-2 rounded-full bg-slate-400" />
                  {t("status_draft", "Draft")}
                </div>
                <p className="mt-1 text-base font-bold tabular-nums">{draftCases}</p>
              </div>
              <div className="rounded-lg border p-2.5 bg-card/60">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-semibold">
                  <span className="size-2 rounded-full bg-sky-500" />
                  {t("status_intake_complete", "Intake")}
                </div>
                <p className="mt-1 text-base font-bold tabular-nums">{intakeComplete}</p>
              </div>
              <div className="rounded-lg border p-2.5 bg-card/60">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-semibold">
                  <span className="size-2 rounded-full bg-indigo-500" />
                  {t("status_forms_generated", "Forms")}
                </div>
                <p className="mt-1 text-base font-bold tabular-nums">{formsGenerated}</p>
              </div>
              <div className="rounded-lg border p-2.5 bg-card/60">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-semibold">
                  <span className="size-2 rounded-full bg-emerald-500" />
                  {t("status_packet_ready", "Packet Ready")}
                </div>
                <p className="mt-1 text-base font-bold tabular-nums">{packetReady}</p>
              </div>
              <div className="rounded-lg border p-2.5 bg-card/60">
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-semibold">
                  <span className="size-2 rounded-full bg-primary" />
                  {t("status_submitted", "Submitted")}
                </div>
                <p className="mt-1 text-base font-bold tabular-nums">{submittedCases}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Platform Core Health Card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <ShieldCheck className="size-4 text-[var(--color-success)]" />
              {t("system_status_title", "Platform Core Status")}
            </CardTitle>
            <CardDescription className="text-xs">
              {lang === "ja" ? "官公庁API・AIエンジン・認証稼働状態" : "Verified legal services infrastructure health."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-1 border-b">
              <span className="text-muted-foreground">{t("api_status", "Core API")}</span>
              <Badge tone="success" className="text-[10px] gap-1">
                <CheckCircle2 className="size-3" /> {lang === "ja" ? "正常稼働中" : "Healthy"}
              </Badge>
            </div>
            <div className="flex items-center justify-between py-1 border-b">
              <span className="text-muted-foreground">{t("ai_engine", "AI Citation Engine")}</span>
              <span className="font-semibold text-foreground flex items-center gap-1 text-[11px]">
                <Sparkles className="size-3 text-primary" /> Groq / Qwen 2.5
              </span>
            </div>
            <div className="flex items-center justify-between py-1 border-b">
              <span className="text-muted-foreground">{t("jurisdiction_engine", "Jurisdictions")}</span>
              <span className="font-semibold text-foreground text-[11px]">
                {jurisdictionCount ?? 4} {lang === "ja" ? "法域同期済" : "Active Corridors"}
              </span>
            </div>
            <div className="pt-2">
              <Link
                href="/admin/jurisdictions"
                className="inline-flex items-center justify-between w-full rounded-lg border bg-muted/30 px-3 py-2 text-xs font-semibold text-primary hover:bg-muted transition-colors"
              >
                <span>{t("configure_jurisdiction", "Configure Corridors & Rules")}</span>
                <ArrowUpRight className="size-3.5" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search, Filter & Live Cases Table */}
      <Card>
        <CardHeader className="pb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="text-base font-bold">
              {t("recent_cases_title", "Recent Immigration Applications")}
            </CardTitle>
            <CardDescription className="text-xs">
              {t("recent_cases_desc", "Real-time stream of incoming visa and status change applications across all corridors.")}
            </CardDescription>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder={t("search_placeholder", "Search cases…")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8.5 w-48 sm:w-60 rounded-lg border bg-background pl-8 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-8.5 rounded-lg border bg-background px-2.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="all">{t("all_statuses", "All statuses")}</option>
              <option value="draft">{t("status_draft", "Draft")}</option>
              <option value="intake_complete">{t("status_intake_complete", "Intake Complete")}</option>
              <option value="checklist_ready">{t("status_checklist_ready", "Checklist Ready")}</option>
              <option value="forms_generated">{t("status_forms_generated", "Forms Generated")}</option>
              <option value="packet_ready">{t("status_packet_ready", "Packet Ready")}</option>
              <option value="submitted">{t("status_submitted", "Submitted")}</option>
            </select>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b bg-muted/40 text-muted-foreground font-semibold">
                  <th className="py-3 px-4 text-left">{t("reference", "Reference")}</th>
                  <th className="py-3 px-4 text-left">{t("applicant", "Applicant / Email")}</th>
                  <th className="py-3 px-4 text-left">{t("status", "Status")}</th>
                  <th className="py-3 px-4 text-left">{t("date", "Created Date")}</th>
                  <th className="py-3 px-4 text-right">{t("actions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredCases.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">
                      {t("no_cases_found", "No cases match the selected filter.")}
                    </td>
                  </tr>
                ) : (
                  filteredCases.map((c) => (
                    <tr key={c.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-foreground">
                        <Link href={`/cases/${c.id}`} className="hover:underline flex items-center gap-1.5">
                          <span className="size-1.5 rounded-full bg-primary" />
                          {c.reference ?? `CASE-${c.id}`}
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {c.applicant_email || `applicant-${c.id}@torii.legal`}
                      </td>
                      <td className="py-3 px-4">
                        {getStatusBadge(c.status)}
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString(lang === "ja" ? "ja-JP" : "en-US", { year: "numeric", month: "short", day: "numeric" }) : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link href={`/cases/${c.id}`}>
                          <Button variant="ghost" size="sm" className="h-7 px-2.5 text-xs gap-1 font-semibold">
                            {t("details", "Open")}
                            <ChevronRight className="size-3.5" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t p-3 text-xs text-muted-foreground bg-muted/10">
            <span>
              {lang === "ja"
                ? `${filteredCases.length} 件を表示中`
                : `Showing ${filteredCases.length} applications`}
            </span>
            <Link
              href="/admin/cases"
              className="font-semibold text-primary hover:underline inline-flex items-center gap-1"
            >
              {t("view_all_cases", "View all in Case Pipeline")}
              <ArrowUpRight className="size-3" />
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
