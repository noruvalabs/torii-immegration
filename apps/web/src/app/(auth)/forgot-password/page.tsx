"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Mail, ArrowLeft, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { forgotPassword } from "@/lib/api/auth";
import { forgotPasswordSchema, type ForgotPasswordFormData } from "@/lib/schemas/auth";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export default function ForgotPasswordPage() {
  const [submittedEmail, setSubmittedEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  async function onSubmit(data: ForgotPasswordFormData) {
    setError(null);
    try {
      await forgotPassword(data.email);
      setSubmittedEmail(data.email);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
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
        {success ? (
          <>
            <CardHeader className="space-y-2 text-center pb-2">
              <div className="mx-auto my-2 flex size-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-6" />
              </div>
              <CardTitle className="text-xl font-bold">Check your email</CardTitle>
              <CardDescription className="text-xs">
                If an account exists with <strong className="text-foreground">{submittedEmail}</strong>, we have sent instructions to reset your password.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Please check your inbox and click the reset link. Links are valid for 1 hour.
              </p>
              <div className="pt-2">
                <Link href="/login">
                  <Button variant="outline" className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                    <ArrowLeft className="mr-1.5 size-3.5" />
                    Back to sign in
                  </Button>
                </Link>
              </div>
            </CardContent>
          </>
        ) : (
          <>
            <CardHeader className="space-y-1">
              <CardTitle className="text-xl font-bold">Forgot your password?</CardTitle>
              <CardDescription className="text-xs">
                Enter your registered email address and we will send you a link to reset your password.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-3.5">
                <label className="flex flex-col gap-1 text-xs font-semibold">
                  <span className="text-muted-foreground">Email address</span>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="email"
                      {...register("email")}
                      placeholder="you@example.com"
                      className={`h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring ${
                        errors.email ? "border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]" : ""
                      }`}
                    />
                  </div>
                  {errors.email && (
                    <span className="text-[11px] font-normal text-[var(--color-danger)]">
                      {errors.email.message}
                    </span>
                  )}
                </label>

                {error && (
                  <p className="rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]">
                    {error}
                  </p>
                )}

                <Button type="submit" disabled={isSubmitting} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                  {isSubmitting ? "Sending reset link…" : "Send reset link"}
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
