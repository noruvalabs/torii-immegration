"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, XCircle, Loader2, Mail } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { verifyEmail, resendVerification } from "@/lib/api/auth";

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [status, setStatus] = useState<"loading" | "success" | "error" | "no-token">(
    token ? "loading" : "no-token"
  );
  const [message, setMessage] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!token) return;
    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.detail);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification failed");
      });
  }, [token]);

  async function handleResend(e: React.FormEvent) {
    e.preventDefault();
    setResending(true);
    try {
      await resendVerification(resendEmail);
      setResendSuccess(true);
    } catch {
      // Silently succeed (prevent enumeration)
      setResendSuccess(true);
    } finally {
      setResending(false);
    }
  }

  if (status === "loading") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Verifying your email</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-8">
            <Loader2 className="size-10 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Please wait…</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (status === "success") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Email verified</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <CheckCircle2 className="size-10 text-green-500" />
            <p className="text-sm text-muted-foreground">{message}</p>
          </div>
          <Link href="/login">
            <Button className="w-full">Sign in</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  if (status === "no-token" || status === "error") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>
            {status === "error" ? "Verification failed" : "Verify your email"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === "error" && (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <XCircle className="size-10 text-[var(--color-danger)]" />
              <p className="text-sm text-muted-foreground">{message}</p>
            </div>
          )}

          {status === "no-token" && (
            <p className="text-sm text-muted-foreground">
              Enter your email to receive a new verification link.
            </p>
          )}

          {resendSuccess ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <CheckCircle2 className="size-10 text-green-500" />
              <p className="text-sm text-muted-foreground">
                If that email is registered and unverified, a verification link has been
                sent.
              </p>
            </div>
          ) : (
            <form onSubmit={handleResend} className="space-y-4">
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-muted-foreground">Email</span>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="email"
                    required
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </div>
              </label>
              <Button type="submit" disabled={resending} className="w-full">
                {resending ? "Sending…" : "Resend verification link"}
              </Button>
            </form>
          )}

          <p className="text-center text-sm text-muted-foreground">
            <Link href="/login" className="font-medium text-primary hover:underline">
              Back to sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    );
  }

  return null;
}
