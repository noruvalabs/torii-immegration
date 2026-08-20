"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    async function processOAuth() {
      try {
        // Parse token from hash (#access_token=...) or query string (?token=...)
        const hash = window.location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        const searchParams = new URLSearchParams(window.location.search);

        const accessToken =
          hashParams.get("access_token") ||
          searchParams.get("token") ||
          hashParams.get("id_token");

        if (!accessToken) {
          const errorParam = hashParams.get("error") || searchParams.get("error");
          if (errorParam) {
            setError(`Google authorization was denied: ${errorParam}`);
            return;
          }
          setError("No authentication token was returned from Google.");
          return;
        }

        const res = await googleLogin({ token: accessToken });
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
