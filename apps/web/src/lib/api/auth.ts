const API = "/backend/v1/auth";

export type User = {
  id: number;
  email: string;
  username: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  // Profile fields
  full_name: string | null;
  nationality: string | null;
  passport_number: string | null;
  passport_expiry: string | null;
  date_of_birth: string | null;
  current_country: string | null;
  avatar_url: string | null;
  profile_complete: boolean;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type MessageResponse = {
  detail: string;
};

export type ApiError = {
  detail: string;
};

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null;
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

export function register(email: string, password: string, username?: string) {
  return request<AuthResponse>("/register", {
    method: "POST",
    body: JSON.stringify({ email, password, username: username || undefined }),
  });
}

export function login(emailOrUsername: string, password: string) {
  return request<AuthResponse>("/login", {
    method: "POST",
    body: JSON.stringify({ email_or_username: emailOrUsername, password }),
  });
}

export function googleLogin(payload: {
  token?: string;
  code?: string;
  redirect_uri?: string;
  email?: string;
  name?: string;
  avatar_url?: string;
}) {
  return request<AuthResponse>("/google", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAuthConfig() {
  return request<{ google_client_id: string | null; google_auth_enabled: boolean }>("/config", {
    method: "GET",
  });
}

export function getMe(token: string) {
  return request<User>("/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function verifyEmail(token: string) {
  return request<MessageResponse>(`/verify-email?token=${encodeURIComponent(token)}`, {
    method: "GET",
  });
}

export function resendVerification(email: string) {
  return request<MessageResponse>("/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function forgotPassword(email: string) {
  return request<MessageResponse>("/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, password: string) {
  return request<MessageResponse>("/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, password }),
  });
}

export type ProfileUpdate = {
  full_name?: string;
  nationality?: string;
  passport_number?: string;
  passport_expiry?: string;
  date_of_birth?: string;
  current_country?: string;
};

export function getProfile(token: string) {
  return request<User>("/profile", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateProfile(token: string, profile: ProfileUpdate) {
  const cleaned: Record<string, string | null> = {};
  for (const [k, v] of Object.entries(profile)) {
    if (typeof v === "string") {
      cleaned[k] = v.trim() || null;
    } else {
      cleaned[k] = v ?? null;
    }
  }
  return request<User>("/profile", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(cleaned),
  });
}

export function uploadAvatar(token: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const API = "/backend/v1/auth";
  return fetch(`${API}/avatar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const body = (await res.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? `Upload failed (${res.status})`);
    }
    return res.json() as Promise<User>;
  });
}
