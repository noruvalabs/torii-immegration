"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, CheckCircle2, AlertCircle, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { resetPassword } from "@/lib/api/auth";
import { resetPasswordSchema, type ResetPasswordFormData } from "@/lib/schemas/auth";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      password: "",
      confirm: "",
    },
  });

  async function onSubmit(data: ResetPasswordFormData) {
    if (!token) {
      setError("Invalid or missing reset token");
      return;
    }

    setError(null);
    try {
      await resetPassword(token, data.password);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. The link may have expired.");
    }
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
        {!token ? (
          <>
            <CardHeader className="space-y-2 text-center pb-2">
              <div className="mx-auto my-2 flex size-12 items-center justify-center rounded-full bg-[var(--color-danger)]/10 text-[var(--color-danger)]">
                <AlertCircle className="size-6" />
              </div>
              <CardTitle className="text-xl font-bold">Invalid Reset Link</CardTitle>
              <CardDescription className="text-xs">
                This password-reset link is missing a token or has already been used.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Password reset links are single-use and expire after 1 hour. Please request a new one if you still need to reset your password.
              </p>
              <div className="pt-2">
                <Link href="/forgot-password">
                  <Button className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                    Request new reset link
                  </Button>
                </Link>
              </div>
              <div className="border-t border-border pt-3">
                <Link href="/login" className="text-xs text-muted-foreground hover:underline">
                  Back to sign in
                </Link>
              </div>
            </CardContent>
          </>
        ) : success ? (
          <>
            <CardHeader className="space-y-2 text-center pb-2">
              <div className="mx-auto my-2 flex size-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-6" />
              </div>
              <CardTitle className="text-xl font-bold">Password Reset Complete</CardTitle>
              <CardDescription className="text-xs">
                Your password has been updated successfully.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <p className="text-xs text-muted-foreground">
                You can now sign in to your Torii account using your new password.
              </p>
              <div className="pt-2">
                <Link href="/login">
                  <Button className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                    Sign in with new password
                    <ArrowRight className="ml-1.5 size-3.5" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </>
        ) : (
          <>
            <CardHeader className="space-y-1">
              <CardTitle className="text-xl font-bold">Reset your password</CardTitle>
              <CardDescription className="text-xs">
                Choose a strong new password for your Torii account.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
                <label className="flex flex-col gap-1 text-xs font-semibold">
                  <span className="text-muted-foreground">New password</span>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="password"
                      {...register("password")}
                      placeholder="••••••••"
                      className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                        errors.password ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]" : ""
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
                  <span className="text-muted-foreground">Confirm new password</span>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="password"
                      {...register("confirm")}
                      placeholder="••••••••"
                      className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                        errors.confirm ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]" : ""
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

                <Button type="submit" disabled={isSubmitting} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                  {isSubmitting ? "Updating password…" : "Reset password"}
                </Button>

                <p className="text-center text-xs text-muted-foreground pt-1">
                  <Link href="/login" className="font-semibold text-primary hover:underline">
                    Back to sign in
                  </Link>
                </p>
              </form>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  );
}
