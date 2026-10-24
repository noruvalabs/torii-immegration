"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useForm, Controller, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  User as UserIcon,
  Loader2,
  Check,
  Camera,
  ShieldCheck,
  FileText,
  Lock,
  ArrowRight,
  Sparkles,
  Info,
  Globe,
  Sun,
  Moon,
  Laptop,
} from "lucide-react";
import { useTheme } from "next-themes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { changePassword, type ProfileUpdate } from "@/lib/api/auth";
import {
  useProfileQuery,
  useUpdateProfileMutation,
  useUploadAvatarMutation,
} from "@/lib/queries/profile";
import { CountrySelector } from "@/components/ui/country-selector";
import { profileSchema, type ProfileFormData } from "@/lib/schemas/profile";

export default function ProfilePage() {
  const { user, token, setAuth } = useAuth();
  const { lang, setLang, t, isJapanUser } = useI18n();
  const { theme, setTheme } = useTheme();

  const { data: profileUser } = useProfileQuery(token, user);
  const updateProfileMutation = useUpdateProfileMutation(token);
  const uploadAvatarMutation = useUploadAvatarMutation(token);

  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [avatar, setAvatar] = useState<string | null>(user?.avatar_url ?? null);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const currentUser = profileUser || user;

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: currentUser?.full_name ?? "",
      nationality: currentUser?.nationality ?? "",
      passport_number: currentUser?.passport_number ?? "",
      passport_expiry: currentUser?.passport_expiry ?? "",
      date_of_birth: currentUser?.date_of_birth ?? "",
      current_country: currentUser?.current_country ?? "",
    },
  });

  const watchedFullName = useWatch({ control, name: "full_name" });

  // Sync form whenever user state is loaded or updated in auth context / query
  useEffect(() => {
    if (currentUser) {
      reset({
        full_name: currentUser.full_name ?? "",
        nationality: currentUser.nationality ?? "",
        passport_number: currentUser.passport_number ?? "",
        passport_expiry: currentUser.passport_expiry ?? "",
        date_of_birth: currentUser.date_of_birth ?? "",
        current_country: currentUser.current_country ?? "",
      });
      setAvatar(currentUser.avatar_url ?? null);
    }
  }, [currentUser, reset]);

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
      const updated = await uploadAvatarMutation.mutateAsync(file);
      setAvatar(updated.avatar_url);
      setAuth(token, updated);
      setSuccessMsg("Profile photo updated successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload avatar");
    } finally {
      setUploadingAvatar(false);
    }
  }

  async function onSubmit(data: ProfileFormData) {
    if (!token) return;
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateProfileMutation.mutateAsync({
        full_name: data.full_name,
        nationality: data.nationality,
        passport_number: data.passport_number || undefined,
        passport_expiry: data.passport_expiry || undefined,
        date_of_birth: data.date_of_birth || undefined,
        current_country: data.current_country,
      });
      setAuth(token, updated);
      setSuccessMsg("Profile details saved successfully. All future cases and questionnaires will auto-fill with these details.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    }
  }

  const isSaving = isSubmitting || updateProfileMutation.isPending;

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
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={avatar}
                      alt="Profile Avatar"
                      className="size-full rounded-full object-cover"
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center size-full rounded-full bg-primary/10 text-primary">
                      <UserIcon className="size-8" />
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
                      {watchedFullName || user?.email?.split("@")[0] || "Applicant Photo"}
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
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="Full name (as on passport)" required error={errors.full_name?.message}>
                    <input
                      type="text"
                      {...register("full_name")}
                      className={`w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        errors.full_name
                          ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                          : ""
                      }`}
                      placeholder="e.g. Yuki Tanaka"
                    />
                  </Field>

                  <Field label="Date of birth" error={errors.date_of_birth?.message}>
                    <input
                      type="date"
                      {...register("date_of_birth")}
                      className={`w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        errors.date_of_birth
                          ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                          : ""
                      }`}
                    />
                  </Field>

                  <Field label="Nationality" required error={errors.nationality?.message}>
                    <Controller
                      name="nationality"
                      control={control}
                      render={({ field }) => (
                        <CountrySelector
                          value={field.value ?? ""}
                          valueType="name"
                          placeholder="Select nationality..."
                          onChange={field.onChange}
                        />
                      )}
                    />
                  </Field>

                  <Field label="Current country of residence" required error={errors.current_country?.message}>
                    <Controller
                      name="current_country"
                      control={control}
                      render={({ field }) => (
                        <CountrySelector
                          value={field.value ?? ""}
                          valueType="name"
                          placeholder="Select residence country..."
                          onChange={field.onChange}
                        />
                      )}
                    />
                  </Field>

                  <Field label="Passport number" error={errors.passport_number?.message}>
                    <input
                      type="text"
                      {...register("passport_number")}
                      className={`w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        errors.passport_number
                          ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                          : ""
                      }`}
                      placeholder="e.g. TK4567890"
                    />
                  </Field>

                  <Field label="Passport expiry date" error={errors.passport_expiry?.message}>
                    <input
                      type="date"
                      {...register("passport_expiry")}
                      className={`w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        errors.passport_expiry
                          ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                          : ""
                      }`}
                    />
                  </Field>
                </div>

                <div className="flex items-center justify-end pt-3 border-t">
                  <Button
                    type="submit"
                    disabled={isSaving}
                    className="min-w-36 h-9 text-sm font-semibold gap-2 shadow-xs"
                  >
                    {isSaving ? (
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

        {/* Right Column: Informational Sidebar Cards & Preferences */}
        <div className="space-y-6">
          {/* Card 0: Theme & Appearance Preferences */}
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card shadow-xs">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Sun className="size-4 text-primary" />
                  Theme & Appearance
                </CardTitle>
                <Badge tone="default" className="text-[10px] capitalize">
                  {theme}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs pt-0">
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Choose your preferred interface theme for application forms and dashboards.
              </p>

              <div className="grid grid-cols-3 gap-1.5 pt-0.5">
                <button
                  type="button"
                  onClick={() => setTheme("light")}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg border text-center transition-all ${
                    theme === "light"
                      ? "border-primary bg-primary/10 text-primary font-bold shadow-xs ring-1 ring-primary"
                      : "border-border bg-background text-muted-foreground hover:bg-muted"
                  }`}
                  title="Light mode"
                >
                  <Sun className="size-3.5" />
                  <span className="text-[11px]">Light</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTheme("dark")}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg border text-center transition-all ${
                    theme === "dark"
                      ? "border-primary bg-primary/10 text-primary font-bold shadow-xs ring-1 ring-primary"
                      : "border-border bg-background text-muted-foreground hover:bg-muted"
                  }`}
                  title="Dark mode"
                >
                  <Moon className="size-3.5" />
                  <span className="text-[11px]">Dark</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTheme("system")}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg border text-center transition-all ${
                    theme === "system"
                      ? "border-primary bg-primary/10 text-primary font-bold shadow-xs ring-1 ring-primary"
                      : "border-border bg-background text-muted-foreground hover:bg-muted"
                  }`}
                  title="System default"
                >
                  <Laptop className="size-3.5" />
                  <span className="text-[11px]">System</span>
                </button>
              </div>
            </CardContent>
          </Card>

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
              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-muted-foreground">Email Status:</span>
                <span className="text-emerald-600 font-medium flex items-center gap-1">
                  <ShieldCheck className="size-3" /> Verified
                </span>
              </div>

              {/* Password Change Form */}
              <div className="pt-2">
                <p className="font-semibold text-foreground mb-2">Change Password</p>
                {pwSuccess && (
                  <p className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-2 text-[11px] text-emerald-700 dark:text-emerald-400 mb-2 font-medium">
                    ✓ {pwSuccess}
                  </p>
                )}
                {pwError && (
                  <p className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 p-2 text-[11px] text-[var(--color-danger)] mb-2">
                    {pwError}
                  </p>
                )}
                <form onSubmit={handlePasswordChange} className="space-y-2">
                  <label className="block">
                    <span className="text-[11px] text-muted-foreground block mb-0.5">Current password</span>
                    <input
                      type="password"
                      required
                      value={currentPw}
                      onChange={(e) => setCurrentPw(e.target.value)}
                      placeholder="••••••••"
                      className="h-8 w-full rounded-md border bg-background px-2.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </label>
                  <label className="block">
                    <span className="text-[11px] text-muted-foreground block mb-0.5">New password</span>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={newPw}
                      onChange={(e) => setNewPw(e.target.value)}
                      placeholder="At least 8 characters"
                      className="h-8 w-full rounded-md border bg-background px-2.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </label>
                  <label className="block">
                    <span className="text-[11px] text-muted-foreground block mb-0.5">Confirm new password</span>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={confirmPw}
                      onChange={(e) => setConfirmPw(e.target.value)}
                      placeholder="Repeat new password"
                      className="h-8 w-full rounded-md border bg-background px-2.5 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    />
                  </label>
                  <Button
                    type="submit"
                    disabled={pwSubmitting || !currentPw || !newPw || !confirmPw}
                    className="w-full text-xs font-semibold h-8 rounded-md mt-1"
                  >
                    {pwSubmitting ? "Updating…" : "Update Password"}
                  </Button>
                </form>
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
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-foreground">
        {label}
        {required && <span className="text-[var(--color-danger)] font-bold"> *</span>}
      </span>
      {children}
      {error && (
        <span className="mt-1 block text-[11px] font-normal text-[var(--color-danger)]">
          {error}
        </span>
      )}
    </label>
  );
}

