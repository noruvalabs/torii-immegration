/**
 * Structured Google OAuth 2.0 client service.
 * Supports compile-time public env, runtime Next.js API config, and FastAPI fallback.
 */

let cachedClientId: string | null = null;
let inFlightRequest: Promise<string | null> | null = null;

export async function resolveGoogleClientId(): Promise<string | null> {
  // 1. Build-time inlined public env
  const staticId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim();
  if (staticId) {
    cachedClientId = staticId;
    return staticId;
  }

  // 2. Return cached value if already resolved
  if (cachedClientId) {
    return cachedClientId;
  }

  // 3. De-duplicate concurrent resolution requests
  if (inFlightRequest) {
    return inFlightRequest;
  }

  inFlightRequest = (async () => {
    try {
      // Query Next.js runtime route handler
      const res = await fetch("/api/auth/config", {
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        const data = (await res.json()) as { google_client_id?: string | null };
        if (data.google_client_id?.trim()) {
          cachedClientId = data.google_client_id.trim();
          return cachedClientId;
        }
      }
    } catch {
      // Ignore and fallback
    }

    try {
      // Fallback: Query backend directly through Next rewrite proxy
      const res = await fetch("/backend/v1/auth/config", {
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        const data = (await res.json()) as { google_client_id?: string | null };
        if (data.google_client_id?.trim()) {
          cachedClientId = data.google_client_id.trim();
          return cachedClientId;
        }
      }
    } catch {
      // Ignore
    }

    return null;
  })().finally(() => {
    inFlightRequest = null;
  });

  return inFlightRequest;
}

export interface GoogleLoginOptions {
  state?: string;
  lang?: string;
  onStart?: () => void;
  onError?: (message: string) => void;
}

export async function initiateGoogleLogin(options: GoogleLoginOptions = {}): Promise<boolean> {
  const { state = window.location.pathname, lang = "en", onStart, onError } = options;

  onStart?.();

  try {
    const clientId = await resolveGoogleClientId();

    if (!clientId) {
      const message =
        lang === "ja"
          ? "Google ログインは現在設定されていません（NEXT_PUBLIC_GOOGLE_CLIENT_ID が未設定）。メールアドレスとパスワードでログインしてください。"
          : "Google Social Sign-In is not configured yet (missing NEXT_PUBLIC_GOOGLE_CLIENT_ID in .env). Please sign in with your email and password.";
      onError?.(message);
      return false;
    }

    const redirectUri = `${window.location.origin}/callback/google`;
    const scope = encodeURIComponent("openid email profile");
    const encodedState = encodeURIComponent(state);

    // Using Google OAuth 2.0 authorization endpoint
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(
      clientId,
    )}&redirect_uri=${encodeURIComponent(
      redirectUri,
    )}&response_type=token&scope=${scope}&state=${encodedState}&prompt=select_account`;

    window.location.href = googleAuthUrl;
    return true;
  } catch (err) {
    const errorMsg =
      err instanceof Error ? err.message : "Failed to initiate Google authentication.";
    onError?.(errorMsg);
    return false;
  }
}
