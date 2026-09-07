"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { googleLogin } from "@/lib/api/auth";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const { setAuth } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    async function processOAuth() {
      try {
        // Parse parameters from hash (#access_token=...) and query string (?code=...)
        const hash = window.location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        const searchParams = new URLSearchParams(window.location.search);

        const errorParam =
          hashParams.get("error") ||
          searchParams.get("error");
        const errorDesc =
          hashParams.get("error_description") ||
          searchParams.get("error_description");

        if (errorParam) {
          setError(
            errorDesc
              ? `Google authorization error: ${errorDesc}`
              : `Google authorization was denied: ${errorParam}`,
          );
          return;
        }

        const accessToken =
          hashParams.get("access_token") ||
          searchParams.get("token") ||
          hashParams.get("id_token");

        const authCode = searchParams.get("code");

        if (!accessToken && !authCode) {
          setError("No authentication token or authorization code was returned from Google.");
          return;
        }

        const redirectUri = `${window.location.origin}/callback/google`;
        const res = authCode
          ? await googleLogin({ code: authCode, redirect_uri: redirectUri })
          : await googleLogin({ token: accessToken! });

        setAuth(res.access_token, res.user);

        const stateParam = hashParams.get("state") || searchParams.get("state");
        const destination =
          stateParam && stateParam.startsWith("/") && stateParam !== "/login" && stateParam !== "/register"
            ? stateParam
            : res.user.role === "applicant"
              ? "/dashboard"
              : "/admin";

        router.push(destination);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to authenticate with Google.");
      }
    }

    void processOAuth();
  }, [router, setAuth]);

  return (
    <div className="w-full max-w-md space-y-4">
      <Card className="border shadow-md">
        <CardContent className="pt-6 text-center space-y-4">
          {error ? (
            <div className="space-y-3">
              <AlertCircle className="mx-auto size-10 text-[var(--color-danger)]" />
              <h3 className="text-base font-bold text-foreground">Sign In Failed</h3>
              <p className="text-xs text-muted-foreground">{error}</p>
              <Link href="/login">
                <Button variant="outline" className="text-xs">
                  Back to Sign In
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-3 py-4">
              <Loader2 className="mx-auto size-8 animate-spin text-primary" />
              <p className="text-sm font-medium text-foreground">
                Authenticating with Google...
              </p>
              <p className="text-xs text-muted-foreground">
                Please wait while we verify your Google credentials.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
