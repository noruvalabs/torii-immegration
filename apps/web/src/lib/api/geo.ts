const API = "/backend/v1/geo";

export type GeoLocation = {
  ip: string;
  country_code: string;
  country_name: string;
  city: string | null;
  region: string | null;
  is_japan: boolean;
  timezone: string | null;
};

export type Destination = {
  code: string;
  name: string;
  currency: string;
  flag: string;
};

export type VisaType = {
  code: string;
  name: string;
  description: string;
};

export type ApplicationType = {
  code: string;
  name: string;
  description: string;
};

export type Nationality = {
  code: string;
  name: string;
  currency: string;
  flag: string;
};

export type GeoData = {
  detected_country: GeoLocation;
  destinations: Destination[];
  nationalities: Nationality[];
  visa_types: VisaType[];
  application_types: ApplicationType[];
};

async function request<T>(path: string, options: RequestInit): Promise<T> {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

export function detectCountry() {
  return request<GeoLocation>("/detect", { method: "GET" });
}

export function getAllGeoData() {
  return request<GeoData>("/all", { method: "GET" });
}

export function getDestinations() {
  return request<Destination[]>("/destinations", { method: "GET" });
}

export function getVisaTypes() {
  return request<VisaType[]>("/visa-types", { method: "GET" });
}

export function getNationalities() {
  return request<Nationality[]>("/nationalities", { method: "GET" });
}

export function getApplicationTypes() {
  return request<ApplicationType[]>("/application-types", { method: "GET" });
}

export function updateResidence(countryCode: string) {
  return request<{ message: string; country_code: string }>("/residence", {
    method: "PUT",
    body: JSON.stringify({ country_code: countryCode }),
  });
}
