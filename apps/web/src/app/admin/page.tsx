import {
  FolderKanban,
  ClipboardCheck,
  RefreshCw,
  Globe,
  ArrowUpRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/** Server-side base URL for the FastAPI system of record. In the container this is the
 *  internal service address; locally it defaults to the dev API on :8000. */
const API_BASE = process.env.API_INTERNAL_BASE_URL ?? "http://localhost:8000";

type ApiStatus = { reachable: boolean; jurisdictions: number };

async function getApiStatus(): Promise<ApiStatus> {
  try {
    const res = await fetch(`${API_BASE}/v1/jurisdictions`, { cache: "no-store" });
    if (!res.ok) return { reachable: false, jurisdictions: 0 };
    const data = (await res.json()) as unknown[];
    return { reachable: true, jurisdictions: data.length };
  } catch {
    return { reachable: false, jurisdictions: 0 };
  }
}

const STATS = [
  { label: "Active cases", value: "—", icon: FolderKanban, hint: "Cases started · in progress" },
  { label: "Review queue", value: "—", icon: ClipboardCheck, hint: "Escalated & low-confidence (US-27)" },
  { label: "Sources awaiting review", value: "—", icon: RefreshCw, hint: "Change-monitor flags (US-26, US-31.3)" },
];

export default async function DashboardPage() {
  const status = await getApiStatus();

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
                {status.reachable ? status.jurisdictions : "—"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {status.reachable ? "from the API" : "API unreachable"}
              </p>
            </div>
            <Globe className="size-8 text-primary/70" />
          </CardContent>
        </Card>

        {STATS.map((s) => {
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
            <p className="text-sm text-muted-foreground">
              The canonical case pipeline lands here — one status lifecycle, whatever channel a
              case arrived through. No cases yet.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">API (system of record)</span>
              <Badge tone={status.reachable ? "success" : "danger"}>
                {status.reachable ? "connected" : "offline"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Endpoint</span>
              <code className="text-xs">{API_BASE}</code>
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
