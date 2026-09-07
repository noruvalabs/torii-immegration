import { NextResponse } from "next/server";

export type AuthConfigResponse = {
  google_client_id: string | null;
  google_auth_enabled: boolean;
};

export async function GET() {
  // 1. Direct runtime environment variables in the web container or local dev
  const envClientId =
    process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ||
    process.env.GOOGLE_CLIENT_ID?.trim() ||
    process.env.TORII_GOOGLE_CLIENT_ID?.trim() ||
    "";

  if (envClientId) {
    return NextResponse.json<AuthConfigResponse>({
      google_client_id: envClientId,
      google_auth_enabled: true,
    });
  }

  // 2. Fallback: query the FastAPI system of record's /v1/auth/config
  const apiBase =
    process.env.API_INTERNAL_BASE_URL ||
    process.env.API_PROXY_TARGET ||
    "http://localhost:8000";

  try {
    const res = await fetch(`${apiBase}/v1/auth/config`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 60 },
    });
    if (res.ok) {
      const data = (await res.json()) as AuthConfigResponse;
      return NextResponse.json<AuthConfigResponse>({
        google_client_id: data.google_client_id || null,
        google_auth_enabled: Boolean(data.google_auth_enabled && data.google_client_id),
      });
    }
  } catch {
    // API service unreachable or offline
  }

  return NextResponse.json<AuthConfigResponse>({
    google_client_id: null,
    google_auth_enabled: false,
  });
}
