"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { resetPassword } from "@/lib/api/auth";
import { resetPasswordSchema, type ResetPasswordFormData } from "@/lib/schemas/auth";

export default function ResetPasswordPage() {
  // useSearchParams must be wrapped in Suspense so the page can be statically
  // prerendered and the token is only read client-side after hydration.
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
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  if (!token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Invalid link</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            This password-reset link is invalid or has expired. Please request a new one.
          </p>
          <Link href="/forgot-password">
            <Button className="w-full">Request new reset link</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (success) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Password reset</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <CheckCircle2 className="size-10 text-green-500" />
            <p className="text-sm text-muted-foreground">
              Your password has been reset successfully.
            </p>
          </div>
          <Link href="/login">
            <Button className="w-full">
              Sign in with new password
            </Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">New password</span>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="password"
                {...register("password")}
                placeholder="••••••••"
                className={`h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
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

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted-foreground">Confirm new password</span>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="password"
                {...register("confirm")}
                placeholder="••••••••"
                className={`h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
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
            <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-sm text-[var(--color-danger)]">
              {error}
            </p>
          )}

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Resetting…" : "Reset password"}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            <Link href="/login" className="font-medium text-primary hover:underline">
              Back to sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
