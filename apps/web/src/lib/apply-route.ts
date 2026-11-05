/**
 * Apply-route detection: given a traveller's passport country (and the
 * extra conditions Saudi Arabia recognises), determine HOW they can apply
 * for a Saudi visa — fully online, in person, or through a licensed agent.
 *
 * Rules are encoded from official Saudi sources (researched 2026-11-04):
 * - Saudi eVisa Terms & Conditions §3.3 "Permitted Country" list
 *   https://visa.visitsaudi.com/Home/TermsConditions
 * - Visit Saudi visa regulations (conditional eVisa / visa-on-arrival routes)
 *   https://www.visitsaudi.com/en/plan-your-trip/visa-regulations
 * - Visit Saudi Package Visa pilot (7 countries, launched July 2026)
 *   https://www.visitsaudi.com/en/campaigns/package-visa
 * - Ministry of Hajj & Umrah / Nusuk (Umrah via licensed agents)
 *   https://umrah.nusuk.sa
 *
 * This module is data-driven per destination so other countries can be
 * added by supplying their own rule sets; Saudi Arabia ("SA") is the
 * first destination implemented.
 */

export type ApplyPurpose = "tourism" | "umrah";

export type ApplyChannel = "online" | "in_person" | "agent" | "visa_free" | "citizen";

export interface TravellerConditions {
  /** Holds a US / UK / Schengen tourist or business visa that has been used at least once. */
  usedWesternVisa: boolean;
  /** Holds permanent residence in the US, UK, or EU. */
  westernPermanentResidence: boolean;
  /** Holds residence in a GCC country, valid at least 3 months beyond entry. */
  gccResidence: boolean;
}

export interface ApplyRoute {
  kind:
    | "online_evisa"
    | "online_conditional"
    | "online_package"
    | "in_person_consular"
    | "agent_umrah"
    | "visa_free"
    | "citizen";
  channel: ApplyChannel;
  /** Short badge shown to the user, e.g. "100% ONLINE". */
  badge: string;
  title: string;
  summary: string;
  facts: string[];
  feeNote?: string;
  warning?: string;
  sourceName: string;
  sourceUrl: string;
}

/** Passports eligible for the standard Saudi tourist eVisa by nationality alone
 *  (official eVisa Terms §3.3 Permitted Country list). */
export const SA_EVISA_ELIGIBLE: ReadonlySet<string> = new Set([
  "AL", "AD", "AU", "AT", "AZ", "BS", "BB", "BR", "BN", "BG", "CA", "CN", "HK", "MO",
  "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "GE", "DE", "GR", "GD", "GY", "HU", "IS",
  "IE", "IT", "JP", "KZ", "KR", "KG", "LV", "LI", "LT", "LU", "MY", "MV", "MT", "MU",
  "MC", "ME", "NL", "NZ", "NO", "PA", "PL", "PT", "RO", "RU", "KN", "SM", "SC", "SG",
  "SK", "SI", "ZA", "ES", "SE", "CH", "TJ", "TH", "TR", "UA", "GB", "US", "UZ", "BA",
  "RS", "MX", "MK",
]);

/** Passports in the Package Visa pilot (electronic visa bundled with a
 *  qualifying flight + hotel package from an approved provider). */
export const SA_PACKAGE_VISA: ReadonlySet<string> = new Set([
  "BD", "EG", "IN", "ID", "JO", "MX", "PK",
]);

/** GCC member-state passports: visa-free entry to Saudi Arabia. */
export const SA_GCC_PASSPORTS: ReadonlySet<string> = new Set(["AE", "BH", "KW", "OM", "QA"]);

/** GCC states whose residents qualify for the conditional eVisa route. */
export const GCC_RESIDENCE_COUNTRIES = ["UAE", "Bahrain", "Kuwait", "Oman", "Qatar"] as const;

const EVISA_SOURCE = {
  sourceName: "Official source: Saudi eVisa Terms & Conditions (Ministry of Tourism)",
  sourceUrl: "https://visa.visitsaudi.com/Home/TermsConditions",
};
const REGULATIONS_SOURCE = {
  sourceName: "Official source: Visit Saudi — Visa Regulations",
  sourceUrl: "https://www.visitsaudi.com/en/plan-your-trip/visa-regulations",
};
const PACKAGE_SOURCE = {
  sourceName: "Official source: Visit Saudi — Package Visa",
  sourceUrl: "https://www.visitsaudi.com/en/campaigns/package-visa",
};
const NUSUK_SOURCE = {
  sourceName: "Official source: Nusuk — Ministry of Hajj & Umrah",
  sourceUrl: "https://umrah.nusuk.sa",
};

export function detectSaudiRoute(input: {
  passportCode: string;
  purpose: ApplyPurpose;
  conditions: TravellerConditions;
}): ApplyRoute {
  const code = input.passportCode.toUpperCase();
  const { purpose, conditions } = input;
  const hasCondition =
    conditions.usedWesternVisa || conditions.westernPermanentResidence || conditions.gccResidence;

  if (code === "SA") {
    return {
      kind: "citizen",
      channel: "citizen",
      badge: "NO VISA NEEDED",
      title: "You are a Saudi citizen",
      summary: "Saudi passport holders do not need a visa to enter Saudi Arabia.",
      facts: ["Enter with your Saudi passport or national ID."],
      ...EVISA_SOURCE,
    };
  }

  if (SA_GCC_PASSPORTS.has(code)) {
    return {
      kind: "visa_free",
      channel: "visa_free",
      badge: "VISA-FREE ENTRY",
      title: "You can enter Saudi Arabia visa-free",
      summary:
        "GCC citizens enter Saudi Arabia without a visa, for tourism and for Umrah outside the Hajj season.",
      facts: [
        "Travel with your passport or national ID card.",
        "No application, no fee, nothing to submit in advance.",
        "Book your free Umrah permit in the Nusuk app before entering Masjid al-Haram.",
      ],
      ...REGULATIONS_SOURCE,
    };
  }

  const eVisaRoute: ApplyRoute = {
    kind: "online_evisa",
    channel: "online",
    badge: "100% ONLINE",
    title: "Apply online — Saudi eVisa",
    summary:
      "Your passport is on Saudi Arabia's eVisa list. Apply and pay fully online on the official portal; the visa is delivered by email. No embassy or visa-centre visit.",
    facts: [
      "1-year multiple-entry visa, stay up to 90 days.",
      "Umrah is permitted on this visa (Hajj is not).",
      "Usually issued within 24 hours.",
      "Torii can prepare and submit this with you on the official KSA portal.",
    ],
    feeNote: "Government fee approx. SAR 395 including mandatory medical insurance (shown exactly at portal checkout).",
    ...EVISA_SOURCE,
  };

  if (SA_EVISA_ELIGIBLE.has(code)) return eVisaRoute;

  if (hasCondition) {
    const viaWestern = conditions.usedWesternVisa || conditions.westernPermanentResidence;
    return {
      kind: "online_conditional",
      channel: "online",
      badge: "100% ONLINE",
      title: "Apply online — eVisa via your existing visa / residence",
      summary: conditions.gccResidence && !viaWestern
        ? "Your passport is not on the standard eVisa list, but as a GCC resident you can apply for the Saudi eVisa online before you travel."
        : "Your passport is not on the standard eVisa list, but your used US/UK/Schengen visa or permanent residence qualifies you for the Saudi eVisa online — and for visa on arrival.",
      facts: [
        ...(conditions.usedWesternVisa
          ? ["Your US/UK/Schengen visa must be tourist or business type, still valid, and used at least once — with an entry stamp from the issuing country (digital stamps are not accepted)."]
          : []),
        ...(conditions.westernPermanentResidence
          ? ["Permanent residence (not a temporary visa) in the US, UK, or EU qualifies you."]
          : []),
        ...(conditions.gccResidence
          ? ["Your GCC residence must stay valid at least 3 months beyond your entry date. This route is online-only — no visa on arrival. You may also apply for first-degree relatives."]
          : []),
        "1-year multiple-entry visa, stay up to 90 days. Umrah is permitted (Hajj is not).",
        "Torii verifies your qualifying document first, then files on the official KSA Visa platform (ksavisa.sa).",
      ],
      feeNote: "Government fee approx. SAR 339 plus medical insurance billed at checkout.",
      ...REGULATIONS_SOURCE,
    };
  }

  if (purpose === "umrah") {
    return {
      kind: "agent_umrah",
      channel: "agent",
      badge: "VIA LICENSED AGENT",
      title: "Umrah visa — through a licensed agent",
      summary:
        "Your passport is not eligible for a self-service online Umrah or tourist eVisa. Umrah visas for your nationality are issued only through travel agents licensed by the Saudi Ministry of Hajj & Umrah, who file on the Nusuk Masar platform.",
      facts: [
        "Since June 2025, an Umrah visa is only issued with verified hotel bookings, pre-booked ground transport, and a confirmed return ticket — a complete package.",
        "You cannot apply for a standalone Umrah visa yourself on Nusuk.",
        "After the visa is issued, book your free Umrah permit in the Nusuk app.",
        "Torii works with licensed partner agents and prepares your complete package.",
      ],
      warning:
        "The Package Visa does not include Makkah/Madinah services and sources conflict on whether Umrah is allowed on it — do not rely on it for an Umrah trip.",
      ...NUSUK_SOURCE,
    };
  }

  if (SA_PACKAGE_VISA.has(code)) {
    return {
      kind: "online_package",
      channel: "online",
      badge: "ONLINE — PACKAGE VISA",
      title: "Apply online — Package Visa (or in person at the visa centre)",
      summary:
        "Your passport is not on the standard eVisa list, but your country is in Saudi Arabia's Package Visa pilot: an electronic tourist visa issued online when you book a qualifying travel package. The alternative is an in-person consular visa.",
      facts: [
        "Package must include a confirmed return flight and a licensed hotel of 4 stars or above, booked with an approved provider (Reserval, Almosafer, Webook.com).",
        "Minimum package value SAR 4,000 per adult for the first 2 days (+ SAR 1,000 per extra day). Visa + insurance fee SAR 402.21 is inside the package.",
        "Single-entry, issued within about 48 hours, valid 3 months, stay 2–88 days. Cancelling the package cancels the visa.",
        "In-person alternative: consular tourist visa via the Tasheer Saudi Visa Service Centre — appointment online, biometrics in person.",
        "Torii checks both routes with you and prepares whichever you choose.",
      ],
      ...PACKAGE_SOURCE,
    };
  }

  return {
    kind: "in_person_consular",
    channel: "in_person",
    badge: "IN PERSON",
    title: "Apply in person — consular visa at the Saudi visa centre",
    summary:
      "Your passport is not eligible for the Saudi eVisa, and no conditional or package route applies. Tourist visas for your nationality are issued by the Saudi embassy through its official visa service centre (Tasheer).",
    facts: [
      "Book your appointment online, then attend in person to submit your documents and biometrics (fingerprints and photo).",
      "Prepare: passport (6+ months validity, 2 blank pages), photos, national ID, 6 months of bank statements with solvency certificate, employer NOC or trade licence, hotel booking and return flight itinerary.",
      "Typical processing is about 5–10 working days after submission.",
      "Torii prepares your complete, error-checked file before your appointment.",
    ],
    ...REGULATIONS_SOURCE,
  };
}

/** Destinations with route-detection rules implemented. */
export const ROUTE_DETECTION_DESTINATIONS: ReadonlySet<string> = new Set(["SA"]);

export function detectApplyRoute(
  destinationCode: string,
  input: { passportCode: string; purpose: ApplyPurpose; conditions: TravellerConditions },
): ApplyRoute | null {
  if (destinationCode.toUpperCase() === "SA") return detectSaudiRoute(input);
  return null;
}
