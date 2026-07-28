"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, TrendingUp, Users, Globe, AlertTriangle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";

const API = "/backend/v1";

type Stats = {
  jurisdictions: number;
  users: Record<string, number>;
};

export default function ReportsPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const h = { Authorization: `Bearer ${token}` };
      const [jurRes, countRes] = await Promise.all([
        fetch(`${API}/jurisdictions`, { headers: h }),
        fetch(`${API}/admin/users/count`, { headers: h }),
      ]);
      const jurisdictions = jurRes.ok ? ((await jurRes.json()) as unknown[]).length : 0;
      const users = countRes.ok ? await countRes.json() : {};
      setStats({ jurisdictions, users });
    } catch {
      setError("Could not load report data.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const totalUsers = stats ? Object.values(stats.users).reduce((a, b) => a + b, 0) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <BarChart3 className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Reports</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform metrics: case throughput, accuracy signals, source freshness, and business
            indicators (US-31).
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading reports…</p>
      ) : stats ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader>
                <CardTitle>Live jurisdictions</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between">
                <p className="text-3xl font-semibold">{stats.jurisdictions}</p>
                <Globe className="size-8 text-primary/70" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Total users</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between">
                <p className="text-3xl font-semibold">{totalUsers}</p>
                <Users className="size-8 text-primary/70" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Cases started</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between">
                <p className="text-3xl font-semibold">—</p>
                <TrendingUp className="size-8 text-primary/70" />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Escalations</CardTitle>
              </CardHeader>
              <CardContent className="flex items-end justify-between">
                <p className="text-3xl font-semibold">—</p>
                <AlertTriangle className="size-8 text-primary/70" />
              </CardContent>
            </Card>
          </div>

          {/* User breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Users by role</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-4">
                {Object.entries(stats.users).map(([role, count]) => (
                  <div key={role} className="rounded-[var(--radius)] border p-3">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {role}
                    </p>
                    <p className="mt-1 text-2xl font-semibold">{count}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Placeholder cards for metrics not yet tracked */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Source freshness</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <RefreshCw className="size-4" />
                  Sources awaiting review: — (US-26, US-31.3)
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Accuracy signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  Review-flag rates, regenerations, reported rejections: — (US-31.2)
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
