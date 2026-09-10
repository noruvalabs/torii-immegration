"use client";

import { useEffect, useState } from "react";
import { Settings, Save, Bell, Shield, Globe, CreditCard, Lock, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/lib/i18n";
import { useAuth } from "@/lib/auth-context";
import { changePassword } from "@/lib/api/auth";
import {
  adminGetPaymentSettings,
  adminUpdatePaymentSettings,
  type AdminPaymentSettingsResponse,
} from "@/lib/api/payments";

export default function SettingsPage() {
  const { lang, setLang, t } = useI18n();
  const { token } = useAuth();
  const [saved, setSaved] = useState(false);

  const [paymentSettings, setPaymentSettings] = useState<AdminPaymentSettingsResponse | null>(null);
  const [loadingPayments, setLoadingPayments] = useState(false);
  const [togglingPayments, setTogglingPayments] = useState(false);

  useEffect(() => {
    if (!token) return;
    setLoadingPayments(true);
    adminGetPaymentSettings(token)
      .then(setPaymentSettings)
      .catch(() => {
        // Fallback default
        setPaymentSettings({
          payments_enabled: true,
          provider: "paddle",
          environment: "sandbox",
          client_token_configured: false,
          api_key_configured: false,
          webhook_secret_configured: false,
          default_checkout_url: "",
        });
      })
      .finally(() => setLoadingPayments(false));
  }, [token]);

  async function handleTogglePayments(enabled: boolean) {
    if (!token || togglingPayments) return;
    setTogglingPayments(true);
    try {
      const updated = await adminUpdatePaymentSettings(token, enabled);
      setPaymentSettings(updated);
      toast.success(
        enabled
          ? (lang === "ja" ? "オンライン決済を有効化しました" : "Online payments enabled")
          : (lang === "ja" ? "オンライン決済を無効化しました" : "Online payments disabled"),
        {
          description: enabled
            ? (lang === "ja" ? "申請者はクレジットパスの購入が可能です。" : "Applicants can now purchase credit passes.")
            : (lang === "ja" ? "申請者によるクレジット新規購入は一時停止されます。" : "New credit purchases by applicants are now blocked."),
        },
      );
    } catch (err) {
      toast.error(
        lang === "ja" ? "設定の更新に失敗しました" : "Failed to update payment setting",
        {
          description: err instanceof Error ? err.message : "Error updating payment toggle",
        },
      );
    } finally {
      setTogglingPayments(false);
    }
  }

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState<string | null>(null);
  const [pwSubmitting, setPwSubmitting] = useState(false);

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(null);

    if (!token) return;
    if (newPw.length < 8) {
      setPwError("New password must be at least 8 characters long");
      return;
    }
    if (newPw !== confirmPw) {
      setPwError("New passwords do not match");
      return;
    }

    setPwSubmitting(true);
    try {
      const res = await changePassword(token, currentPw, newPw);
      setPwSuccess(res.detail || "Password changed successfully");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      setPwError(err instanceof Error ? err.message : "Failed to change password");
    } finally {
      setPwSubmitting(false);
    }
  }

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

        {/* Payment Gateway & Billing Controls */}
        <Card className="border-primary/20 shadow-xs">
          <CardHeader>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="size-4 text-primary" />
                {lang === "ja" ? "オンライン決済・課金管理 (Paddle)" : "Online Payments & Billing (Paddle)"}
              </CardTitle>
              {paymentSettings && (
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      paymentSettings.payments_enabled
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30"
                        : "bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                    }`}
                  >
                    {paymentSettings.payments_enabled ? (
                      <>
                        <CheckCircle2 className="size-3" />
                        {lang === "ja" ? "決済受付中" : "Accepting Payments"}
                      </>
                    ) : (
                      <>
                        <AlertCircle className="size-3" />
                        {lang === "ja" ? "決済停止中 (メンテナンス)" : "Payments Disabled"}
                      </>
                    )}
                  </span>
                  <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-mono text-muted-foreground uppercase">
                    {paymentSettings.environment}
                  </span>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Primary Toggle Switch */}
            <div className="flex items-start justify-between rounded-xl border border-border/70 bg-muted/20 p-4 gap-4">
              <div className="space-y-1">
                <label
                  htmlFor="toggle-payments"
                  className="text-sm font-bold text-foreground flex items-center gap-2 cursor-pointer"
                >
                  <span>{lang === "ja" ? "Paddle オンライン決済を有効にする" : "Enable Paddle Online Payments"}</span>
                  {togglingPayments && <Loader2 className="size-3.5 animate-spin text-primary" />}
                </label>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {lang === "ja"
                    ? "無効化すると、申請者による新規クレジット・申請パスの購入が即座に停止されます（メンテナンス表示）。すでに保有しているクレジットは引き続き利用可能です。"
                    : "When turned off, applicants cannot purchase credit passes (shows a maintenance notice). Existing user credit balances remain safe and usable."}
                </p>
              </div>

              <div className="pt-0.5 shrink-0">
                <input
                  id="toggle-payments"
                  type="checkbox"
                  checked={paymentSettings?.payments_enabled ?? true}
                  disabled={togglingPayments || loadingPayments}
                  onChange={(e) => handleTogglePayments(e.target.checked)}
                  className="size-5 cursor-pointer accent-primary rounded"
                />
              </div>
            </div>

            {/* Provider Configuration Status Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="rounded-lg border p-3 space-y-1">
                <span className="text-muted-foreground">{lang === "ja" ? "プロバイダー" : "Provider"}</span>
                <p className="font-semibold text-foreground">Paddle Billing (v2)</p>
              </div>

              <div className="rounded-lg border p-3 space-y-1">
                <span className="text-muted-foreground">{lang === "ja" ? "クライアントトークン" : "Client Token"}</span>
                <p className="font-semibold text-foreground">
                  {paymentSettings?.client_token_configured ? (
                    <span className="text-emerald-600">✓ {lang === "ja" ? "設定済み" : "Configured"}</span>
                  ) : (
                    <span className="text-amber-600">⚠ {lang === "ja" ? "未設定 (.env)" : "Not Set"}</span>
                  )}
                </p>
              </div>

              <div className="rounded-lg border p-3 space-y-1">
                <span className="text-muted-foreground">{lang === "ja" ? "Webhook 署名シークレット" : "Webhook Secret"}</span>
                <p className="font-semibold text-foreground">
                  {paymentSettings?.webhook_secret_configured ? (
                    <span className="text-emerald-600">✓ {lang === "ja" ? "設定済み" : "Configured"}</span>
                  ) : (
                    <span className="text-amber-600">⚠ {lang === "ja" ? "未設定 (.env)" : "Not Set"}</span>
                  )}
                </p>
              </div>
            </div>

            {/* Credit Packs Reference */}
            <div className="border-t pt-4 space-y-2">
              <span className="text-xs font-semibold text-muted-foreground">
                {lang === "ja" ? "提供中の申請パス料金" : "Active Credit Pack Prices"}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
                <div className="rounded-lg bg-card border p-2.5">
                  <div className="font-bold text-foreground">Starter (1 Pass)</div>
                  <div className="text-muted-foreground">$19.00 / ¥2,800</div>
                </div>
                <div className="rounded-lg bg-card border p-2.5">
                  <div className="font-bold text-foreground">Standard (3 Passes)</div>
                  <div className="text-muted-foreground">$39.00 / ¥5,800</div>
                </div>
                <div className="rounded-lg bg-card border p-2.5">
                  <div className="font-bold text-foreground">Agency / Family (5 Passes)</div>
                  <div className="text-muted-foreground">$59.00 / ¥8,900</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Security & Password */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="size-4" /> Security & Password
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 max-w-md">
            {pwSuccess && (
              <p className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-2.5 text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                ✓ {pwSuccess}
              </p>
            )}
            {pwError && (
              <p className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-2.5 text-xs text-[var(--color-danger)]">
                {pwError}
              </p>
            )}
            <div className="space-y-3">
              <label className="flex flex-col gap-1 text-xs font-semibold">
                <span className="text-muted-foreground">Current password</span>
                <input
                  type="password"
                  value={currentPw}
                  onChange={(e) => setCurrentPw(e.target.value)}
                  placeholder="••••••••"
                  className="h-9 w-full rounded-md border bg-background px-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold">
                <span className="text-muted-foreground">New password (min. 8 characters)</span>
                <input
                  type="password"
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                  placeholder="••••••••"
                  className="h-9 w-full rounded-md border bg-background px-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs font-semibold">
                <span className="text-muted-foreground">Confirm new password</span>
                <input
                  type="password"
                  value={confirmPw}
                  onChange={(e) => setConfirmPw(e.target.value)}
                  placeholder="••••••••"
                  className="h-9 w-full rounded-md border bg-background px-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>
              <Button
                type="button"
                onClick={handlePasswordChange}
                disabled={pwSubmitting || !currentPw || !newPw || !confirmPw}
                className="text-xs font-semibold h-9 rounded-md"
              >
                {pwSubmitting ? "Updating password…" : "Update Password"}
              </Button>
            </div>
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
