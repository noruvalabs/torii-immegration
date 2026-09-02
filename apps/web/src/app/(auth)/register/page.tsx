"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, User, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { register, googleLogin } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";
import { useI18n, LanguageSwitcher } from "@/lib/i18n";
import { GoogleLogo } from "../login/page";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const { setAuth } = useAuth();
  const { lang, t } = useI18n();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError(lang === "ja" ? "パスワードが一致しません" : "Passwords do not match");
      return;
    }

    setSubmitting(true);
    try {
      const res = await register(email, password, username || undefined);
      setAuth(res.access_token, res.user);
      router.push(res.user.role === "applicant" ? "/dashboard" : "/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  function handleGoogleLogin() {
    setError(null);
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setError(
        lang === "ja"
          ? "Google 登録は現在設定されていません（NEXT_PUBLIC_GOOGLE_CLIENT_ID が未設定）。メールアドレスとパスワードで登録してください。"
          : "Google Social Sign-In is not configured yet (missing NEXT_PUBLIC_GOOGLE_CLIENT_ID in .env). Please create your account with email and password.",
      );
      return;
    }
    setGoogleSubmitting(true);
    const redirectUri = `${window.location.origin}/callback/google`;
    const scope = encodeURIComponent("openid email profile");
    const state = encodeURIComponent(window.location.pathname);
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=token&scope=${scope}&state=${state}&prompt=select_account`;
    window.location.href = googleAuthUrl;
  }

  return (
    <div className="w-full max-w-md space-y-4">
      <div className="flex items-center justify-between px-1">
        <Link href="/" className="flex items-center gap-2 font-bold text-sm">
          <span>⛩️</span>
          <span>Torii</span>
        </Link>
        <LanguageSwitcher />
      </div>

      <Card className="border shadow-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-xl font-bold">
            {t("auth_register_title", "Create your Torii account")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("auth_register_sub", "Begin your verified immigration application with official guidance.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Social Sign Up Button */}
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            disabled={googleSubmitting || submitting}
            className="w-full justify-center gap-2 h-10 border bg-background hover:bg-muted font-medium text-xs shadow-xs rounded-md"
          >
            <GoogleLogo />
            <span>{t("auth_google_continue", "Continue with Google")}</span>
          </Button>

          <div className="relative flex items-center justify-center my-1.5">
            <div className="border-t flex-1 border-border" />
            <span className="bg-card px-2.5 text-[11px] text-muted-foreground uppercase font-medium tracking-wider whitespace-nowrap shrink-0">
              {t("auth_or_divider", "Or continue with email")}
            </span>
            <div className="border-t flex-1 border-border" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">Email</span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_username_optional", "Username (optional)")}
              </span>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="johndoe"
                  minLength={3}
                  maxLength={64}
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">{t("auth_password", "Password")}</span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_confirm_password", "Confirm password")}
              </span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="••••••••"
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </label>

            {error && (
              <p className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]">
                {error}
              </p>
            )}

            <Button type="submit" disabled={submitting || googleSubmitting} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
              {submitting ? t("loading", "Creating account…") : t("auth_create_one", "Create account")}
              <ArrowRight className="ml-1.5 size-3.5" />
            </Button>

            <p className="text-center text-xs text-muted-foreground pt-1">
              {t("auth_have_account", "Already have an account?")}{" "}
              <Link href="/login" className="font-semibold text-primary hover:underline">
                {t("sign_in", "Sign in")}
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
