"use client";

import { useCallback, useEffect, useState } from "react";
import {
  FolderKanban,
  ClipboardCheck,
  RefreshCw,
  Globe,
  ArrowUpRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";
import { adminListCases, adminCountCases } from "@/lib/api/admin";

const API = "/backend/v1";

export default function DashboardPage() {
  const { token } = useAuth();
  const [caseCount, setCaseCount] = useState<Record<string, number>>({});
  const [jurisdictionCount, setJurisdictionCount] = useState<number | null>(null);
  const [recentCases, setRecentCases] = useState<{ id: number; reference: string | null; status: string; created_at: string | null }[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [cc, cases, jRes] = await Promise.allSettled([
        adminCountCases(token),
        adminListCases(token, { limit: 5 }),
        fetch(`${API}/jurisdictions`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (cc.status === "fulfilled") setCaseCount(cc.value);
      if (cases.status === "fulfilled") setRecentCases(cases.value);
      if (jRes.status === "fulfilled" && jRes.value.ok) {
        const data = await jRes.value.json();
        setJurisdictionCount(data.length);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const totalCases = Object.values(caseCount).reduce((a, b) => a + b, 0);
  const activeCases = totalCases - (caseCount["submitted"] ?? 0);
  const reviewQueue = caseCount["draft"] ?? 0;
  const submittedCases = caseCount["submitted"] ?? 0;

  const stats = [
    { label: "Active cases", value: loading ? "—" : String(activeCases), icon: FolderKanban, hint: "Cases started · in progress" },
    { label: "Review queue", value: loading ? "—" : String(reviewQueue), icon: ClipboardCheck, hint: "Escalated & low-confidence (US-27)" },
    { label: "Submitted cases", value: loading ? "—" : String(submittedCases), icon: RefreshCw, hint: "Packets sent for filing" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Live jurisdictions</CardTitle>
          </CardHeader>
          <CardContent className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-semibold tabular-nums">
                {jurisdictionCount !== null ? jurisdictionCount : "—"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {jurisdictionCount !== null ? "from the API" : "API unreachable"}
              </p>
            </div>
            <Globe className="size-8 text-primary/70" />
          </CardContent>
        </Card>

        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label}>
              <CardHeader>
                <CardTitle>{s.label}</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between">
                <div>
                  <p className="text-3xl font-semibold tabular-nums">{s.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{s.hint}</p>
                </div>
                <Icon className="size-8 text-primary/70" />
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent cases</CardTitle>
          </CardHeader>
          <CardContent>
            {recentCases.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                The canonical case pipeline lands here — one status lifecycle, whatever channel a
                case arrived through. No cases yet.
              </p>
            ) : (
              <div className="space-y-3">
                {recentCases.map((c) => (
                  <div key={c.id} className="flex items-center justify-between text-sm">
                    <div>
                      <span className="font-mono font-semibold">{c.reference ?? `#${c.id}`}</span>
                      <span className="ml-2 text-muted-foreground">· {c.status}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">API (system of record)</span>
              <Badge tone="success">connected</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Endpoint</span>
              <code className="text-xs">{API}</code>
            </div>
            <a
              href="/admin/jurisdictions"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              Configure a jurisdiction <ArrowUpRight className="size-3.5" />
            </a>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
