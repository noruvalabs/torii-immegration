"use client";

import { useCallback, useEffect, useState } from "react";
import { Globe, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Jurisdiction = { id: number; code: string; name: string; is_live: boolean };

// Browser → /backend/* is rewritten to the FastAPI system of record (next.config.ts).
const API = "/backend/v1/jurisdictions";

export default function JurisdictionsPage() {
  const [items, setItems] = useState<Jurisdiction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API, { cache: "no-store" });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setItems((await res.json()) as Jurisdiction[]);
    } catch {
      setError("Could not reach the API. Is torii-api running on :8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function create() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(API, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code, name, is_live: isLive }),
      });
      if (res.status === 409) {
        setError(`Jurisdiction '${code.toUpperCase()}' already exists.`);
        return;
      }
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setCode("");
      setName("");
      setIsLive(false);
      await load();
    } catch {
      setError("Create failed — check the API is running.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Globe className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Jurisdictions</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure the countries Torii supports. Only <strong>live</strong> jurisdictions are
            offered to applicants (US-01.3, US-29). This talks to the live API.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-5">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
            className="flex flex-wrap items-end gap-3"
          >
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Code</span>
              <input
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="JP"
                maxLength={8}
                className="h-9 w-24 rounded-[var(--radius)] border bg-background px-3 uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-1 flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Name</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Japan"
                className="h-9 min-w-40 rounded-[var(--radius)] border bg-background px-3 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex h-9 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={isLive}
                onChange={(e) => setIsLive(e.target.checked)}
                className="size-4"
              />
              Live
            </label>
            <Button type="submit" disabled={submitting}>
              <Plus className="size-4" />
              {submitting ? "Adding…" : "Add"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-5 text-sm text-muted-foreground">Loading…</p>
          ) : items.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">
              No jurisdictions yet. Add one above (try Japan — the beachhead market).
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3 font-medium">Code</th>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((j) => (
                  <tr key={j.id} className="border-b last:border-0">
                    <td className="px-5 py-3 font-mono font-medium">{j.code}</td>
                    <td className="px-5 py-3">{j.name}</td>
                    <td className="px-5 py-3">
                      <Badge tone={j.is_live ? "success" : "muted"}>
                        {j.is_live ? "live" : "draft"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
