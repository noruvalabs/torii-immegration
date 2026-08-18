"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import {
  User,
  Loader2,
  Check,
  Camera,
  ShieldCheck,
  FileText,
  Lock,
  ArrowRight,
  Sparkles,
  Info,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { updateProfile, uploadAvatar, type ProfileUpdate } from "@/lib/api/auth";
import { CountrySelector } from "@/components/ui/country-selector";

export default function ProfilePage() {
  const { user, token, setAuth } = useAuth();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [avatar, setAvatar] = useState<string | null>(user?.avatar_url ?? null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<ProfileUpdate>({
    full_name: user?.full_name ?? "",
    nationality: user?.nationality ?? "",
    passport_number: user?.passport_number ?? "",
    passport_expiry: user?.passport_expiry ?? "",
    date_of_birth: user?.date_of_birth ?? "",
    current_country: user?.current_country ?? "",
  });

  function update(key: keyof ProfileUpdate, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !token) return;

    if (file.size > 5 * 1024 * 1024) {
      setError("Image must be less than 5MB");
      return;
    }

    setUploadingAvatar(true);
    setError(null);

    try {
      const updated = await uploadAvatar(token, file);
      setAvatar(updated.avatar_url);
      setAuth(token, updated);
      setSuccessMsg("Profile photo updated successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload avatar");
    } finally {
      setUploadingAvatar(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateProfile(token, form);
      setAuth(token, updated);
      setSuccessMsg("Profile details saved successfully. All future cases will auto-populate with these details.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  const isValid = Boolean(
    form.full_name && form.nationality && form.passport_number && form.current_country,
  );

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* ── HEADER ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Applicant Profile</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your personal identity, passport, and residence details for automated visa form generation.
          </p>
        </div>
        <Badge
          tone={user?.profile_complete ? "success" : "warning"}
          className="w-fit flex items-center gap-1.5 py-1 px-3"
        >
          <ShieldCheck className="size-3.5" />
          {user?.profile_complete ? "Profile Complete" : "Profile Incomplete"}
        </Badge>
      </div>

      {/* ── NOTIFICATIONS ────────────────────────────────────────────────────── */}
      {error && (
        <div className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-[var(--radius)] border border-[var(--color-success)]/30 bg-[var(--color-success)]/10 px-4 py-3 text-sm text-[var(--color-success)] flex items-center justify-between">
          <span>{successMsg}</span>
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-xs font-semibold hover:underline ml-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── MAIN CONTENT GRID ────────────────────────────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left 2 Columns: Main Profile Form */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="pb-4 border-b">
              <CardTitle className="text-base font-bold text-foreground">
                Personal &amp; Travel Document Details
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                These credentials are encrypted and reused across your visa applications, checklists, and embassy packets.
              </p>
            </CardHeader>

            <CardContent className="pt-6 space-y-6">
              {/* Avatar Upload Bar */}
              <div className="flex flex-col sm:flex-row items-center gap-5 p-4 rounded-lg border bg-muted/20">
                <div className="relative group size-20 rounded-full border-2 border-dashed border-muted-foreground/30 hover:border-primary/60 transition-colors shrink-0">
                  {uploadingAvatar ? (
                    <div className="flex items-center justify-center size-full rounded-full bg-muted">
                      <Loader2 className="size-5 text-primary animate-spin" />
                    </div>
                  ) : avatar ? (
                    <img
                      src={avatar}
                      alt="Profile Avatar"
                      className="size-full rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center size-full rounded-full bg-primary/10 text-primary">
                      <User className="size-8" />
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingAvatar}
                    aria-label="Upload profile photo"
                    className="absolute inset-0 flex flex-col items-center justify-center rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity text-white text-[10px] font-medium"
                  >
                    <Camera className="size-4 mb-0.5" />
                    Change
                  </button>
                </div>

                <div className="text-center sm:text-left flex-1 min-w-0">
                  <div className="flex items-center justify-center sm:justify-start gap-2">
                    <p className="text-sm font-semibold text-foreground">
                      {form.full_name || user?.email?.split("@")[0] || "Applicant Photo"}
                    </p>
                    {user?.email_verified && (
                      <Badge tone="success" className="text-[9px] py-0 px-1.5">
                        Verified
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    JPG, PNG, or WEBP up to 5MB. Used for your profile badge and account representation.
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingAvatar}
                    className="h-7 text-xs mt-2.5 px-2.5 gap-1.5"
                  >
                    <Camera className="size-3 text-muted-foreground" /> Choose Photo
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarChange}
                    className="hidden"
                  />
                </div>
              </div>

              {/* Input Form Fields */}
              <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Full name (as on passport)" required>
                    <input
                      type="text"
                      value={form.full_name ?? ""}
                      onChange={(e) => update("full_name", e.target.value)}
                      className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      placeholder="e.g. Yuki Tanaka"
                    />
                  </Field>

                  <Field label="Date of birth">
                    <input
                      type="date"
                      value={form.date_of_birth ?? ""}
                      onChange={(e) => update("date_of_birth", e.target.value)}
                      className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </Field>

                  <Field label="Nationality" required>
                    <CountrySelector
                      value={form.nationality ?? ""}
                      valueType="name"
                      placeholder="Select nationality..."
                      onChange={(val) => update("nationality", val)}
                    />
                  </Field>

                  <Field label="Current country of residence" required>
                    <CountrySelector
                      value={form.current_country ?? ""}
                      valueType="name"
                      placeholder="Select residence country..."
                      onChange={(val) => update("current_country", val)}
                    />
                  </Field>

                  <Field label="Passport number" required>
                    <input
                      type="text"
                      value={form.passport_number ?? ""}
                      onChange={(e) => update("passport_number", e.target.value)}
                      className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      placeholder="e.g. TK4567890"
                    />
                  </Field>

                  <Field label="Passport expiry date">
                    <input
                      type="date"
                      value={form.passport_expiry ?? ""}
                      onChange={(e) => update("passport_expiry", e.target.value)}
                      className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </Field>
                </div>

                <div className="flex items-center justify-end pt-3 border-t">
                  <Button
                    type="submit"
                    disabled={!isValid || saving}
                    className="min-w-36 h-9 text-sm font-semibold gap-2 shadow-xs"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="size-4 animate-spin" /> Saving…
                      </>
                    ) : (
                      <>
                        <Check className="size-4" /> Save Profile Details
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Informational Sidebar Cards */}
        <div className="space-y-6">
          {/* Card 1: Reusability Benefit */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Sparkles className="size-4 text-primary" /> Auto-Fill Architecture
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-muted-foreground pt-0">
              <p>
                Torii uses single-source identity. Once entered, your name, passport number, and nationality
                automatically map to:
              </p>
              <ul className="space-y-1.5 list-disc list-inside text-foreground/80">
                <li>Government COE and Visa application forms</li>
                <li>Customized document requirement checklists</li>
                <li>Employer &amp; sponsor verification records</li>
              </ul>
              <div className="rounded border bg-primary/5 p-2.5 text-[11px] text-primary flex items-start gap-2">
                <Info className="size-3.5 shrink-0 mt-0.5" />
                <span>Zero redundant re-entry across any future visa filings.</span>
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Document Vault Link */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <FileText className="size-4 text-emerald-600" /> Document Vault
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-muted-foreground pt-0">
              <p>
                Have passport scans, ID photos, or bank statements? Store them securely in your vault.
              </p>
              <Link
                href="/documents"
                className="inline-flex w-full items-center justify-between rounded-[var(--radius)] border bg-background p-2.5 text-xs font-semibold text-foreground hover:bg-accent transition-colors"
              >
                <span>Go to Document Vault</span>
                <ArrowRight className="size-3.5 text-muted-foreground" />
              </Link>
            </CardContent>
          </Card>

          {/* Card 3: Security & Account Info */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                <Lock className="size-4 text-muted-foreground" /> Account Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5 text-xs pt-0">
              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">Signed in as:</span>
                <span className="font-mono text-foreground truncate max-w-[140px]" title={user?.email}>
                  {user?.email}
                </span>
              </div>
              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">Account Role:</span>
                <Badge tone="default" className="capitalize text-[10px]">
                  {user?.role || "applicant"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Email Status:</span>
                <span className="text-emerald-600 font-medium flex items-center gap-1">
                  <ShieldCheck className="size-3" /> Verified
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-foreground">
        {label}
        {required && <span className="text-[var(--color-danger)] font-bold"> *</span>}
      </span>
      {children}
    </label>
  );
}

