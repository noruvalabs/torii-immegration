"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { User, Lock, ArrowRight, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { login, googleLogin } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";

export function GoogleLogo() {
  return (
    <svg className="size-4 shrink-0" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.03 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const [emailOrUsername, setEmailOrUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const { setAuth } = useAuth();
  const { lang, t } = useI18n();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await login(emailOrUsername, password);
      setAuth(res.access_token, res.user);
      router.push(res.user.role === "applicant" ? "/dashboard" : "/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
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
          ? "Google ログインは現在設定されていません（NEXT_PUBLIC_GOOGLE_CLIENT_ID が未設定）。メールアドレスとパスワードでログインしてください。"
          : "Google Social Sign-In is not configured yet (missing NEXT_PUBLIC_GOOGLE_CLIENT_ID in .env). Please sign in with your email and password.",
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
      <div className="flex items-center px-1">
        <Link href="/" className="flex items-center gap-2 font-bold text-sm">
          <span>⛩️</span>
          <span>Torii</span>
        </Link>
      </div>

      <Card className="border shadow-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-xl font-bold">
            {t("auth_welcome_back", "Sign in to Torii")}
          </CardTitle>
          <CardDescription className="text-xs">
            {t("auth_welcome_sub", "Official immigration application and dossier management system.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Social Sign In Button */}
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

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_email_username", "Email or username")}
              </span>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  required
                  value={emailOrUsername}
                  onChange={(e) => setEmailOrUsername(e.target.value)}
                  placeholder="applicant1@example.com"
                  className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t("auth_password", "Password")}</span>
                <Link
                  href="/forgot-password"
                  className="text-[11px] font-medium text-primary hover:underline"
                >
                  {t("auth_forgot_password", "Forgot password?")}
                </Link>
              </div>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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
              {submitting ? t("loading", "Signing in…") : t("sign_in", "Sign in")}
              <ArrowRight className="ml-1.5 size-3.5" />
            </Button>

            <p className="text-center text-xs text-muted-foreground pt-1">
              {t("auth_no_account", "No account?")}{" "}
              <Link href="/register" className="font-semibold text-primary hover:underline">
                {t("auth_create_one", "Create one")}
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
