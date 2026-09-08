"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, XCircle, Loader2, Mail, ArrowRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { verifyEmail, resendVerification } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";
import { ToriiLogo } from "@/components/brand/ToriiLogo";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailForm />
    </Suspense>
  );
}

function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { setAuth } = useAuth();

  const [status, setStatus] = useState<"loading" | "success" | "error" | "no-token">(
    token ? "loading" : "no-token"
  );
  const [message, setMessage] = useState("");
  const [userRole, setUserRole] = useState("applicant");
  const [resendEmail, setResendEmail] = useState("");
  const [resendSuccess, setResendSuccess] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!token) return;
    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.detail);
        if (res.access_token && res.user) {
          setAuth(res.access_token, res.user);
          setUserRole(res.user.role);
        }
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Verification link is invalid or expired");
      });
  }, [token, setAuth]);

  async function handleResend(e: React.FormEvent) {
    e.preventDefault();
    if (!resendEmail) return;
    setResending(true);
    try {
      await resendVerification(resendEmail);
      setResendSuccess(true);
    } catch {
      setResendSuccess(true);
    } finally {
      setResending(false);
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
        {status === "loading" && (
          <>
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-xl font-bold">Verifying your email</CardTitle>
              <CardDescription className="text-xs">
                Checking your verification token with the system…
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center gap-3 py-8">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-xs text-muted-foreground">Please wait a moment…</p>
              </div>
            </CardContent>
          </>
        )}

        {status === "success" && (
          <>
            <CardHeader className="space-y-2 text-center pb-2">
              <div className="mx-auto my-2 flex size-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-6" />
              </div>
              <CardTitle className="text-xl font-bold">Email Verified</CardTitle>
              <CardDescription className="text-xs">
                {message || "Your email address has been verified successfully. Your account is now active."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-center">
              <div className="pt-2">
                <Link href={["admin", "ops", "employer"].includes(userRole) ? "/admin" : "/dashboard"}>
                  <Button className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                    Proceed to Dashboard
                    <ArrowRight className="ml-1.5 size-3.5" />
                  </Button>
                </Link>
              </div>
              <div className="border-t border-border pt-3">
                <Link href="/login" className="text-xs text-muted-foreground hover:underline">
                  Sign in with a different account
                </Link>
              </div>
            </CardContent>
          </>
        )}

        {(status === "no-token" || status === "error") && (
          <>
            <CardHeader className="space-y-2 text-center pb-2">
              <div
                className={`mx-auto my-2 flex size-12 items-center justify-center rounded-full ${
                  status === "error"
                    ? "bg-[var(--color-danger)]/10 text-[var(--color-danger)]"
                    : "bg-primary/10 text-primary"
                }`}
              >
                {status === "error" ? <XCircle className="size-6" /> : <Mail className="size-6" />}
              </div>
              <CardTitle className="text-xl font-bold">
                {status === "error" ? "Verification Link Expired or Invalid" : "Verify Your Email"}
              </CardTitle>
              <CardDescription className="text-xs">
                {status === "error"
                  ? message
                  : "Please enter your email to receive a new verification link."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {resendSuccess ? (
                <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-center space-y-1">
                  <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                    Verification link sent!
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    If an unverified account exists for <strong>{resendEmail}</strong>, a new link has been dispatched to your inbox.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleResend} className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Enter your email address below and we will send you a fresh verification link:
                  </p>
                  <label className="flex flex-col gap-1 text-xs font-semibold">
                    <span className="text-muted-foreground">Email address</span>
                    <div className="relative">
                      <Mail className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                      <input
                        type="email"
                        required
                        value={resendEmail}
                        onChange={(e) => setResendEmail(e.target.value)}
                        placeholder="you@example.com"
                        className="h-9 w-full rounded-md border bg-background pl-9 pr-3 text-xs outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                    </div>
                  </label>
                  <Button type="submit" disabled={resending} className="w-full text-xs font-semibold h-9 shadow-xs rounded-md">
                    {resending ? "Sending…" : "Send new verification link"}
                  </Button>
                </form>
              )}

              <div className="border-t border-border pt-3 text-center">
                <Link href="/login" className="text-xs font-semibold text-primary hover:underline">
                  Back to sign in
                </Link>
              </div>
            </CardContent>
          </>
        )}
      </Card>
    </div>
  );
}
