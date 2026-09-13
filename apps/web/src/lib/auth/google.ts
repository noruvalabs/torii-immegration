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

    // Authorization Code flow (`response_type=code`), not the implicit flow
    // (`response_type=token`) this used to request.
    //
    // Google is retiring the implicit grant for web clients, and it was never the right fit
    // here: this is a registered Web application client with a GOCSPX- secret, and the API
    // already implements the server-side code exchange (see POST /v1/auth/google, step 1).
    // Implicit also hands the access token to the browser in the URL fragment, where it
    // lands in history; the code flow keeps the token exchange server-side.
    //
    // The code arrives back as a `?code=` query parameter rather than a `#access_token=`
    // fragment. The callback page already reads both, so it needs no change -- it just takes
    // the `authCode` branch and posts { code, redirect_uri } to the API.
    //
    // redirect_uri must match an Authorised redirect URI on the OAuth client in Google Cloud
    // Console exactly, including scheme and trailing path.
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${encodeURIComponent(
      clientId,
    )}&redirect_uri=${encodeURIComponent(
      redirectUri,
    )}&response_type=code&scope=${scope}&state=${encodedState}&prompt=select_account`;

    window.location.href = googleAuthUrl;
    return true;
  } catch (err) {
    const errorMsg =
      err instanceof Error ? err.message : "Failed to initiate Google authentication.";
    onError?.(errorMsg);
    return false;
  }
}
