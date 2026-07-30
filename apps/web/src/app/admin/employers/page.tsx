"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2, Users, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";

type Employer = {
  id: number;
  name: string;
  contact_email: string;
  employee_count: number;
  active_cases: number;
};

export default function EmployersPage() {
  const { token } = useAuth();
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      // Employer management API not yet implemented — show empty state
      setEmployers([]);
    } catch {
      setError("Could not load employers.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Building2 className="size-5" />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-semibold tracking-tight">Employers</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The B2B seam: HR teams sponsoring a foreign workforce, managing many visa cases from
            one place with compliance and deadline oversight (US-23, US-24).
          </p>
        </div>
        <Button onClick={() => {}}>
          <Plus className="size-4" /> Add employer
        </Button>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading employers…</p>
      ) : employers.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <Building2 className="mx-auto mb-3 size-8 text-muted-foreground/50" />
            <p className="text-sm font-medium">No employers yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Employer accounts will appear here once HR teams sign up. Each employer gets a
              dashboard showing all their employees&apos; cases, deadlines, and compliance status.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {employers.map((emp) => (
            <Card key={emp.id}>
              <CardContent className="flex items-center gap-4 pt-5">
                <div className="flex size-10 shrink-0 items-center justify-center rounded-[var(--radius)] bg-accent">
                  <Building2 className="size-5 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{emp.name}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">{emp.contact_email}</p>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="text-center">
                    <p className="font-semibold text-foreground">{emp.employee_count}</p>
                    <p className="text-xs">employees</p>
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-foreground">{emp.active_cases}</p>
                    <p className="text-xs">active cases</p>
                  </div>
                </div>
                <Badge tone="success">active</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
