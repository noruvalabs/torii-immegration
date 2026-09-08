"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, Lock, User, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { register as registerApi, resendVerification } from "@/lib/api/auth";
import { initiateGoogleLogin } from "@/lib/auth/google";
import { useAuth } from "@/lib/auth-context";
import { useI18n } from "@/lib/i18n";
import { GoogleLogo } from "../login/page";
import { ToriiLogo } from "@/components/brand/ToriiLogo";
import { registerSchema, type RegisterFormData } from "@/lib/schemas/auth";

export default function RegisterPage() {
  const [error, setError] = useState<string | null>(null);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [resendSent, setResendSent] = useState(false);
  const [resending, setResending] = useState(false);
  const { lang, t } = useI18n();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      username: "",
      password: "",
      confirm: "",
    },
  });

  async function onSubmit(data: RegisterFormData) {
    setError(null);
    try {
      await registerApi(data.email, data.password, data.username || undefined);
      setSubmittedEmail(data.email);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  async function handleGoogleLogin() {
    setError(null);
    await initiateGoogleLogin({
      lang,
      state: window.location.pathname,
      onStart: () => setGoogleSubmitting(true),
      onError: (msg) => {
        setError(msg);
        setGoogleSubmitting(false);
      },
    });
  }

  if (submittedEmail) {
    return (
      <div className="w-full max-w-md space-y-4">
        <div className="flex items-center px-1">
          <Link href="/" className="flex items-center gap-3 font-bold">
            <ToriiLogo size={36} />
            <span className="text-xl tracking-tight">Torii</span>
          </Link>
        </div>

        <Card className="border shadow-md">
          <CardHeader className="space-y-2 text-center pb-2">
            <div className="mx-auto my-2 flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Mail className="size-6" />
            </div>
            <CardTitle className="text-xl font-bold">
              Check your email
            </CardTitle>
            <CardDescription className="text-xs">
              We&apos;ve sent a verification link to{" "}
              <span className="font-semibold text-foreground">{submittedEmail}</span>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-center">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Please check your inbox and click the verification link to activate your Torii account before signing in.
            </p>

            <div className="pt-2">
              <Link href="/login">
                <Button className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                  Proceed to Sign in
                  <ArrowRight className="ml-1.5 size-3.5" />
                </Button>
              </Link>
            </div>

            <div className="border-t border-border pt-3">
              <p className="text-xs text-muted-foreground">
                Didn&apos;t receive the email?{" "}
                {resendSent ? (
                  <span className="text-green-600 dark:text-green-400 font-medium">
                    Verification link resent!
                  </span>
                ) : (
                  <button
                    type="button"
                    disabled={resending}
                    onClick={async () => {
                      setResending(true);
                      try {
                        await resendVerification(submittedEmail);
                        setResendSent(true);
                      } catch {
                        setResendSent(true);
                      } finally {
                        setResending(false);
                      }
                    }}
                    className="font-semibold text-primary hover:underline"
                  >
                    {resending ? "Sending…" : "Resend link"}
                  </button>
                )}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
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

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">Email</span>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="email"
                  {...register("email")}
                  placeholder="you@example.com"
                  className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                    errors.email
                      ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                      : ""
                  }`}
                />
              </div>
              {errors.email && (
                <span className="text-[11px] font-normal text-[var(--color-danger)]">
                  {errors.email.message}
                </span>
              )}
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_username_optional", "Username (optional)")}
              </span>
              <div className="relative">
                <User className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  {...register("username")}
                  placeholder="johndoe"
                  className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                    errors.username
                      ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                      : ""
                  }`}
                />
              </div>
              {errors.username && (
                <span className="text-[11px] font-normal text-[var(--color-danger)]">
                  {errors.username.message}
                </span>
              )}
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">{t("auth_password", "Password")}</span>
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

            <label className="flex flex-col gap-1 text-xs font-semibold">
              <span className="text-muted-foreground">
                {t("auth_confirm_password", "Confirm password")}
              </span>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="password"
                  {...register("confirm")}
                  placeholder="••••••••"
                  className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                    errors.confirm
                      ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]"
                      : ""
                  }`}
                />
              </div>
              {errors.confirm && (
                <span className="text-[11px] font-normal text-[var(--color-danger)]">
                  {errors.confirm.message}
                </span>
              )}
            </label>

            {error && (
              <p className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]">
                {error}
              </p>
            )}

            <Button type="submit" disabled={isSubmitting || googleSubmitting} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
              {isSubmitting ? t("loading", "Creating account…") : t("auth_create_one", "Create account")}
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
