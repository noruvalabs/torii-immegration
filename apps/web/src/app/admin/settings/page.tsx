"use client";

import { useState } from "react";
import { Settings, Save, Bell, Shield, Globe, CreditCard } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const [saved, setSaved] = useState(false);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    // TODO: POST settings to API when available
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Settings className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Settings</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform-level configuration owned by the overseer — the levers that let the system
            run itself within safe legal bounds without a developer (US-21, US-22, US-29).
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Consent & privacy */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="size-4" /> Consent & data privacy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" defaultChecked className="size-4" />
              Require explicit data-processing consent before intake starts
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" defaultChecked className="size-4" />
              Record consent timestamp and version per user
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Data retention period (days)</span>
              <input
                type="number"
                defaultValue={365}
                className="h-9 w-32 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="size-4" /> Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Renewal reminder lead time (days)</span>
              <input
                type="number"
                defaultValue={90}
                className="h-9 w-32 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <span className="text-xs text-muted-foreground">
                Days before expiry to send reminder (US-19.2)
              </span>
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" defaultChecked className="size-4" />
              Enable email notifications
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" className="size-4" />
              Enable SMS notifications
            </label>
          </CardContent>
        </Card>

        {/* Jurisdictions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="size-4" /> Jurisdiction defaults
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" defaultChecked className="size-4" />
              Only show live jurisdictions to applicants (US-01.3)
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" className="size-4" />
              Enable e-file submission where available (US-10.3)
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Default applicant locale</span>
              <select
                defaultValue="en"
                className="h-9 w-48 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="en">English</option>
                <option value="ja">Japanese</option>
                <option value="de">German</option>
              </select>
            </label>
          </CardContent>
        </Card>

        {/* Pricing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="size-4" /> Pricing & packaging
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Per-application price</span>
              <input
                type="number"
                step="0.01"
                defaultValue={49.0}
                className="h-9 w-32 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Monthly subscription price</span>
              <input
                type="number"
                step="0.01"
                defaultValue={19.0}
                className="h-9 w-32 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-muted-foreground">Employer license (per seat/month)</span>
              <input
                type="number"
                step="0.01"
                defaultValue={29.0}
                className="h-9 w-32 rounded-[var(--radius)] border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
          </CardContent>
        </Card>

        <div className="flex items-center gap-3">
          <Button type="submit">
            <Save className="size-4" /> Save settings
          </Button>
          {saved && (
            <span className="text-sm text-[var(--color-success)]">Settings saved.</span>
          )}
        </div>
      </form>
    </div>
  );
}
