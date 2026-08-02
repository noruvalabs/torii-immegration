"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { User, Loader2, Check, Camera } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { updateProfile, uploadAvatar, type ProfileUpdate } from "@/lib/api/auth";

const COUNTRIES = [
  "Japan", "United States", "United Kingdom", "Canada", "Australia",
  "Germany", "France", "Singapore", "South Korea", "United Arab Emirates",
  "New Zealand", "Netherlands", "Italy", "Spain", "Switzerland",
  "Ireland", "Thailand", "Malaysia", "India", "China",
];

export default function ProfilePage() {
  const { user, token, setAuth } = useAuth();
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
    try {
      const updated = await updateProfile(token, form);
      setAuth(token, updated);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  const isValid = form.full_name && form.nationality && form.passport_number && form.current_country;

  return (
    <div className="mx-auto max-w-lg space-y-6 py-8">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-full bg-primary/10">
          <User className="size-5 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Complete your profile</h1>
          <p className="text-sm text-muted-foreground">
            Save your details once — they auto-fill for every new case.
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      <Card>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 pt-5">
            {/* Avatar upload */}
            <div className="flex flex-col items-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingAvatar}
                className="relative group size-24 rounded-full border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 transition-colors disabled:opacity-50"
              >
                {uploadingAvatar ? (
                  <div className="flex items-center justify-center size-full rounded-full bg-muted">
                    <Loader2 className="size-6 text-muted-foreground animate-spin" />
                  </div>
                ) : avatar ? (
                  <img
                    src={avatar}
                    alt="Avatar"
                    className="size-full rounded-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center size-full rounded-full bg-muted">
                    <Camera className="size-6 text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground mt-1">Upload</span>
                  </div>
                )}
                <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Camera className="size-5 text-white" />
                </div>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
                className="hidden"
              />
              <p className="text-xs text-muted-foreground">Click to upload photo</p>
            </div>

            <Field label="Full name (as on passport)" required>
              <input
                type="text"
                value={form.full_name ?? ""}
                onChange={(e) => update("full_name", e.target.value)}
                className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
                placeholder="Yuki Tanaka"
              />
            </Field>

            <Field label="Nationality" required>
              <select
                value={form.nationality ?? ""}
                onChange={(e) => update("nationality", e.target.value)}
                className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
              >
                <option value="">Select nationality</option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>

            <Field label="Passport number" required>
              <input
                type="text"
                value={form.passport_number ?? ""}
                onChange={(e) => update("passport_number", e.target.value)}
                className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
                placeholder="TK4567890"
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Passport expiry">
                <input
                  type="date"
                  value={form.passport_expiry ?? ""}
                  onChange={(e) => update("passport_expiry", e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
                />
              </Field>
              <Field label="Date of birth">
                <input
                  type="date"
                  value={form.date_of_birth ?? ""}
                  onChange={(e) => update("date_of_birth", e.target.value)}
                  className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
                />
              </Field>
            </div>

            <Field label="Current country of residence" required>
              <select
                value={form.current_country ?? ""}
                onChange={(e) => update("current_country", e.target.value)}
                className="w-full rounded-[var(--radius)] border bg-background px-3 py-2 text-sm"
              >
                <option value="">Select country</option>
                {COUNTRIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>

            <button
              type="submit"
              disabled={!isValid || saving}
              className="inline-flex w-full items-center justify-center gap-2 rounded-[var(--radius)] bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:pointer-events-none disabled:opacity-50"
            >
              {saving ? (
                <><Loader2 className="size-4 animate-spin" /> Saving…</>
              ) : (
                <><Check className="size-4" /> Save profile</>
              )}
            </button>
          </form>
        </CardContent>
      </Card>
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
      <span className="mb-1 block text-sm font-medium text-foreground">
        {label}
        {required && <span className="text-[var(--color-danger)]"> *</span>}
      </span>
      {children}
    </label>
  );
}
