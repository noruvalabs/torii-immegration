"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { User, Lock, ArrowRight, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { login, resendVerification } from "@/lib/api/auth";
import { initiateGoogleLogin } from "@/lib/auth/google";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { ToriiLogo } from "@/components/brand/ToriiLogo";
import { GoogleLogo } from "@/components/brand/GoogleLogo";
import { loginSchema, type LoginFormData } from "@/lib/schemas/auth";

function LoginForm() {
  const [error, setError] = useState<string | null>(null);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resending, setResending] = useState(false);
  const { setAuth } = useAuth();
  const { lang, t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      emailOrUsername: "",
      password: "",
    },
  });

  async function onSubmit(data: LoginFormData) {
    setError(null);
    try {
      const res = await login(data.emailOrUsername, data.password);
      setAuth(res.access_token, res.user);
      if (redirectParam && redirectParam.startsWith("/")) {
        router.push(redirectParam);
      } else {
        router.push(res.user.role === "applicant" ? "/dashboard" : "/admin");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  async function handleGoogleLogin() {
    setError(null);
    const returnTarget = redirectParam && redirectParam.startsWith("/") ? redirectParam : window.location.pathname;
    await initiateGoogleLogin({
      lang,
      state: returnTarget,
      onStart: () => setGoogleSubmitting(true),
      onError: (msg) => {
        setError(msg);
        setGoogleSubmitting(false);
      },
    });
  }

  return (
    <div className="w-full max-w-md space-y-4">
      <div className="flex items-center px-1">
        <Link href="/" className="flex items-center gap-3 font-bold">
          <ToriiLogo size={36} />
          <span className="text-xl tracking-tight">Torii</span>
        </Link>
      </div>

      <Card className="border shadow-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-xl font-bold">
            {t("auth_welcome_back", "Sign in to Torii")}
          </CardTitle>
          <CardDescription className="text-xs">
            {redirectParam
              ? "Sign in to start your official visa application process."
              : t("auth_welcome_sub", "Official immigration application and dossier management system.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Social Sign In Button */}
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            disabled={googleSubmitting || isSubmitting}
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

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_email_username", "Email or username")}
              </span>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  {...register("emailOrUsername")}
                  placeholder="applicant1@example.com"
                  className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                    errors.emailOrUsername
                      ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                      : ""
                  }`}
                />
              </div>
              {errors.emailOrUsername && (
                <span className="text-[11px] font-normal text-[var(--color-danger)]">
                  {errors.emailOrUsername.message}
                </span>
              )}
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
                  {...register("password")}
                  placeholder="••••••••"
                  className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                    errors.password
                      ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                      : ""
                  }`}
                />
              </div>
              {errors.password && (
                <span className="text-[11px] font-normal text-[var(--color-danger)]">
                  {errors.password.message}
                </span>
              )}
            </label>

            {error && (
              <div className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)] space-y-2">
                <p>{error}</p>
                {error.toLowerCase().includes("verify") && (
                  <div className="pt-1.5 border-t border-[var(--color-danger)]/20">
                    {resendSuccess ? (
                      <p className="text-emerald-600 dark:text-emerald-400 font-medium">
                        ✓ Verification link resent! Please check your inbox.
                      </p>
                    ) : (
                      <button
                        type="button"
                        disabled={resending}
                        onClick={async () => {
                          const val = getValues("emailOrUsername");
                          if (!val || !val.includes("@")) {
                            router.push("/verify-email");
                            return;
                          }
                          setResending(true);
                          try {
                            await resendVerification(val);
                            setResendSuccess(true);
                          } catch {
                            setResendSuccess(true);
                          } finally {
                            setResending(false);
                          }
                        }}
                        className="font-semibold underline hover:opacity-80 text-[var(--color-danger)]"
                      >
                        {resending ? "Sending new link…" : "Resend verification link to your email →"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            <Button type="submit" disabled={isSubmitting || googleSubmitting} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
              {isSubmitting ? t("loading", "Signing in…") : t("sign_in", "Sign in")}
              <ArrowRight className="ml-1.5 size-3.5" />
            </Button>

            <p className="text-center text-xs text-muted-foreground pt-1">
              {t("auth_no_account", "No account?")}{" "}
              <Link
                href={redirectParam ? `/register?redirect=${encodeURIComponent(redirectParam)}` : "/register"}
                className="font-semibold text-primary hover:underline"
              >
                {t("auth_create_one", "Create one")}
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
