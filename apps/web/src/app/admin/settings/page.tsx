"use client";

import { useState } from "react";
import { Settings, Save, Bell, Shield, Globe, CreditCard } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";

export default function SettingsPage() {
  const { lang, setLang, t } = useI18n();
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

        {/* Language & Localizations */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="size-4" /> {lang === "ja" ? "言語・地域設定" : "Language & Regional Localization"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold text-muted-foreground">
                {lang === "ja" ? "管理画面およびシステム言語" : "Interface Display Language"}
              </span>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setLang("en")}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg border text-xs font-semibold transition-all ${
                    lang === "en"
                      ? "border-primary bg-primary text-primary-foreground shadow-xs"
                      : "border-border bg-card text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <span>🇺🇸</span>
                  <span>English (Global)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setLang("ja")}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg border text-xs font-semibold transition-all ${
                    lang === "ja"
                      ? "border-primary bg-primary text-primary-foreground shadow-xs"
                      : "border-border bg-card text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <span>🇯🇵</span>
                  <span>日本語 (Japanese)</span>
                </button>
              </div>
            </div>

            <label className="flex items-center gap-3 text-sm pt-2">
              <input type="checkbox" defaultChecked className="size-4" />
              {lang === "ja" ? "IPジオロケーションに基づく言語自動判定を有効化" : "Auto-detect language by visitor IP geolocation (Japan = JP)"}
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" defaultChecked className="size-4" />
              {lang === "ja" ? "公開法域のみを申請者に表示 (US-01.3)" : "Only show live jurisdictions to applicants (US-01.3)"}
            </label>
            <label className="flex items-center gap-3 text-sm">
              <input type="checkbox" className="size-4" />
              {lang === "ja" ? "電子申請受付を有効化 (US-10.3)" : "Enable e-file submission where available (US-10.3)"}
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
