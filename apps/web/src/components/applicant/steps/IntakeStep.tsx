"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import {
  Check,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Search,
  ArrowRight,
  CheckCircle2,
  ListChecks,
  LayoutGrid,
  AlertCircle,
  AlertTriangle,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ALL_COUNTRIES, matchCountry, searchCountries, type Country } from "@/lib/countries";
import { CountryFlag } from "@/components/landing/country-flag";
import { getWallet, syncProfileFromWallet, type WalletDocument } from "@/lib/api/wallet";
import type { IntakeState, IntakeQuestion, User } from "./types";
import { findQuestionByKey } from "./types";

type IntakeStepProps = {
  state: IntakeState;
  profile: User | null;
  onAnswer: (key: string, value: unknown) => void;
  onProceedToEligibility?: () => void;
  targetKey?: string | null;
  targetTimestamp?: number;
  token?: string;
  caseId?: number;
  onRefresh?: () => void;
};

/** Map profile country names and demonyms to common ISO codes used in intake enums. */
const COUNTRY_ALIASES: Record<string, string> = {
  japan: "JP",
  japanese: "JP",
  "united states": "US",
  american: "US",
  usa: "US",
  "united kingdom": "UK",
  british: "UK",
  uk: "UK",
  canada: "CA",
  canadian: "CA",
  australia: "AU",
  australian: "AU",
  germany: "DE",
  german: "DE",
  france: "FR",
  french: "FR",
  singapore: "SG",
  singaporean: "SG",
  "south korea": "KR",
  korean: "KR",
  korea: "KR",
  bangladesh: "BD",
  bangladeshi: "BD",
  india: "IN",
  indian: "IN",
  pakistan: "PK",
  pakistani: "PK",
  china: "CN",
  chinese: "CN",
  philippines: "PH",
  filipino: "PH",
  vietnam: "VN",
  vietnamese: "VN",
  nepal: "NP",
  nepalese: "NP",
  nepali: "NP",
  "sri lanka": "LK",
  "sri lankan": "LK",
};

const MONTHS_LOOKUP: Record<string, number> = {
  january: 1, jan: 1, february: 2, feb: 2, march: 3, mar: 3,
  april: 4, apr: 4, may: 5, june: 6, jun: 6, july: 7, jul: 7,
  august: 8, aug: 8, september: 9, sep: 9, sept: 9, october: 10, oct: 10,
  november: 11, nov: 11, december: 12, dec: 12,
};

export function normalizeDateToISO(val?: string | null): string {
  if (!val) return "";
  const s = val.trim().replace(/,/g, " ");
  // YYYY-MM-DD or YYYY/MM/DD
  const isoMatch = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
  if (isoMatch) {
    return `${isoMatch[1].padStart(4, "0")}-${isoMatch[2].padStart(2, "0")}-${isoMatch[3].padStart(2, "0")}`;
  }
  // DD-MM-YYYY or DD/MM/YYYY
  const dmyMatch = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/);
  if (dmyMatch) {
    return `${dmyMatch[3].padStart(4, "0")}-${dmyMatch[2].padStart(2, "0")}-${dmyMatch[1].padStart(2, "0")}`;
  }
  // 15 March 2002 or March 15 2002
  const parts = s.split(/\s+/);
  if (parts.length === 3) {
    if (/^\d+$/.test(parts[0]) && MONTHS_LOOKUP[parts[1].toLowerCase()] && /^\d{4}$/.test(parts[2])) {
      const mon = String(MONTHS_LOOKUP[parts[1].toLowerCase()]).padStart(2, "0");
      return `${parts[2]}-${mon}-${parts[0].padStart(2, "0")}`;
    }
    if (MONTHS_LOOKUP[parts[0].toLowerCase()] && /^\d+$/.test(parts[1]) && /^\d{4}$/.test(parts[2])) {
      const mon = String(MONTHS_LOOKUP[parts[0].toLowerCase()]).padStart(2, "0");
      return `${parts[2]}-${mon}-${parts[1].padStart(2, "0")}`;
    }
  }
  return val.replace(/\//g, "-");
}

function matchEnumOption(value: string, options: string[]): string | null {
  if (options.includes(value)) return value;
  const upper = value.toUpperCase();
  const byCode = options.find((o) => o.toUpperCase() === upper);
  if (byCode) return byCode;
  const byName = options.find((o) => o.toLowerCase() === value.toLowerCase());
  if (byName) return byName;
  const alias = COUNTRY_ALIASES[value.toLowerCase()];
  if (alias) {
    const hit = options.find((o) => o.toUpperCase() === alias || o === alias);
    if (hit) return hit;
    const ctry = ALL_COUNTRIES.find((c) => c.code === alias);
    if (ctry) {
      const hitName = options.find((o) => o.toLowerCase() === ctry.name.toLowerCase());
      if (hitName) return hitName;
    }
  }
  return null;
}

const PROFILE_ALIASES: Record<string, keyof User> = {
  full_name: "full_name",
  applicant_name: "full_name",
  name: "full_name",
  legal_name: "full_name",
  full_legal_name: "full_name",

  nationality: "nationality",
  citizenship: "nationality",
  country_of_citizenship: "nationality",
  country_of_nationality: "nationality",

  passport_number: "passport_number",
  passport_no: "passport_number",
  passport_num: "passport_number",
  travel_document_number: "passport_number",

  passport_expiry: "passport_expiry",
  passport_expiry_date: "passport_expiry",
  passport_expiration_date: "passport_expiry",
  passport_valid_until: "passport_expiry",

  date_of_birth: "date_of_birth",
  dob: "date_of_birth",
  birth_date: "date_of_birth",
  applicant_dob: "date_of_birth",
  applicant_date_of_birth: "date_of_birth",

  current_country: "current_country",
  current_residence_country: "current_country",
  current_location_country: "current_country",
  residence_country: "current_country",
  country_of_residence: "current_country",
};

const INVALID_PASSPORT_VALUES = new Set([
  "PASSPORT", "PASSEPORT", "DOCUMENT", "NULL", "NONE", "UNDEFINED", "JAPAN", "UNKNOWN"
]);

function isValidPassportNumber(val: string): boolean {
  const clean = val.trim().toUpperCase();
  if (clean.length < 6 || INVALID_PASSPORT_VALUES.has(clean)) return false;
  return /\d/.test(clean);
}

const INVALID_RC_VALUES = new Set([
  "RESIDENCE", "RESIDENT", "ENGINEER", "MINISTRY", "NULL", "NONE", "UNDEFINED", "UNKNOWN"
]);

function isValidResidenceCardNumber(val: string): boolean {
  const clean = val.trim().toUpperCase();
  if (clean.length < 8 || INVALID_RC_VALUES.has(clean)) return false;
  return /\d/.test(clean);
}

function getProfileValueForQuestion(key: string, prompt: string, profile: User): string | null {
  const normKey = key.toLowerCase();
  const normPrompt = prompt.toLowerCase();

  // Direct alias check
  const mappedField = PROFILE_ALIASES[normKey];
  if (mappedField) {
    const val = profile[mappedField];
    if (val && typeof val === "string" && val.trim()) return val.trim();
  }

  // Fuzzy match on key and prompt
  if (
    normKey.includes("date_of_birth") ||
    normKey === "dob" ||
    normKey.includes("birth_date") ||
    (normPrompt.includes("date of birth") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse") && !normPrompt.includes("child"))
  ) {
    if (profile.date_of_birth?.trim()) return profile.date_of_birth.trim();
  }

  if (
    (normKey.includes("passport") && (normKey.includes("expiry") || normKey.includes("expiration"))) ||
    (normPrompt.includes("passport") && (normPrompt.includes("expiry") || normPrompt.includes("expiration")))
  ) {
    if (profile.passport_expiry?.trim()) return profile.passport_expiry.trim();
  }

  if (
    (normKey.includes("passport") && (normKey.includes("number") || normKey.includes("no") || normKey.includes("num"))) ||
    normKey === "passport_number" ||
    normKey === "passport_no" ||
    normKey === "passport" ||
    (normPrompt.includes("passport") && (normPrompt.includes("number") || normPrompt.includes("no")))
  ) {
    if (profile.passport_number?.trim() && isValidPassportNumber(profile.passport_number)) {
      return profile.passport_number.trim();
    }
  }

  if (
    normKey === "full_name" ||
    normKey === "applicant_name" ||
    (normPrompt.includes("full name") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse") && !normPrompt.includes("employer"))
  ) {
    if (profile.full_name?.trim()) return profile.full_name.trim();
  }

  if (
    normKey === "nationality" ||
    normKey === "citizenship" ||
    (normPrompt.includes("nationality") && !normPrompt.includes("spouse") && !normPrompt.includes("father"))
  ) {
    if (profile.nationality?.trim()) return profile.nationality.trim();
  }

  if (
    normKey.includes("residence_country") ||
    normKey.includes("current_country") ||
    normKey.includes("location_country")
  ) {
    if (profile.current_country?.trim()) return profile.current_country.trim();
  }

  return null;
}

export type AutofillMatch = {
  value: string;
  source: string;
};

function getExtractedVal(raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === "object" && "value" in (raw as Record<string, unknown>)) {
    const v = (raw as Record<string, unknown>).value;
    if (v !== null && v !== undefined && String(v).trim()) return String(v).trim();
  }
  if (typeof raw === "string" && raw.trim()) return raw.trim();
  if (typeof raw === "number") return String(raw);
  return null;
}

function getAutofillValueForQuestion(
  key: string,
  prompt: string,
  profile?: User | null,
  walletDocs: WalletDocument[] = [],
): AutofillMatch | null {
  const normKey = key.toLowerCase().replace(/[\s\-]/g, "_");
  const normPrompt = prompt.toLowerCase();

  // 1. Check profile first
  if (profile) {
    const pVal = getProfileValueForQuestion(normKey, normPrompt, profile);
    if (pVal) {
      return { value: pVal, source: "Profile" };
    }
  }

  // 2. Search wallet documents extracted fields
  for (const doc of walletDocs) {
    if (!doc.extracted_fields || typeof doc.extracted_fields !== "object") continue;
    const docLabel = doc.name || doc.doc_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const fields = doc.extracted_fields as Record<string, unknown>;

    for (const [fKey, fRaw] of Object.entries(fields)) {
      const normFKey = fKey.toLowerCase().replace(/[\s\-]/g, "_");
      const fVal = getExtractedVal(fRaw);
      if (!fVal) continue;

      if (normKey === normFKey) {
        if (normKey.includes("passport") && (normKey.includes("number") || normKey.includes("no"))) {
          if (isValidPassportNumber(fVal)) return { value: fVal, source: docLabel };
        } else if (normKey.includes("residence_card") || normKey.includes("card_number")) {
          if (isValidResidenceCardNumber(fVal)) return { value: fVal, source: docLabel };
        } else {
          return { value: fVal, source: docLabel };
        }
      }

      // Passport number
      if (
        (normKey.includes("passport") && (normKey.includes("number") || normKey.includes("no") || normKey.includes("num"))) ||
        normKey === "passport_number" ||
        normKey === "passport_no" ||
        normKey === "passport" ||
        (normPrompt.includes("passport") && (normPrompt.includes("number") || normPrompt.includes("no")))
      ) {
        if (
          (normFKey.includes("passport") && (normFKey.includes("number") || normFKey.includes("no") || normFKey.includes("num"))) ||
          normFKey === "passport_number" ||
          normFKey === "passport_no"
        ) {
          if (isValidPassportNumber(fVal)) {
            return { value: fVal, source: docLabel };
          }
        }
      }

      // Passport expiry
      if (
        (normKey.includes("passport") && (normKey.includes("expiry") || normKey.includes("expiration"))) ||
        (normPrompt.includes("passport") && (normPrompt.includes("expiry") || normPrompt.includes("expiration")))
      ) {
        if (normFKey.includes("expiry") || normFKey.includes("expiration")) {
          return { value: fVal, source: docLabel };
        }
      }

      // Residence Card number
      if (
        normKey.includes("residence_card") ||
        normKey.includes("zairyu") ||
        normPrompt.includes("residence card") ||
        normPrompt.includes("zairyu")
      ) {
        if (normFKey.includes("residence_card") || normFKey === "card_number") {
          if (isValidResidenceCardNumber(fVal)) {
            return { value: fVal, source: docLabel };
          }
        }
      }

      // Status of Residence / Current visa
      if (
        normKey.includes("status_of_residence") ||
        normKey.includes("current_status") ||
        normKey.includes("visa_status") ||
        normPrompt.includes("status of residence") ||
        normPrompt.includes("current visa")
      ) {
        if (normFKey.includes("status_of_residence") || normFKey.includes("residence_status") || normFKey.includes("visa_status")) {
          return { value: fVal, source: docLabel };
        }
      }

      // Japan address
      if (
        normKey.includes("japan_address") ||
        normKey.includes("current_japan_address") ||
        (normPrompt.includes("address in japan") || normPrompt.includes("current address in japan"))
      ) {
        if (normFKey.includes("current_japan_address") || normFKey === "address") {
          return { value: fVal, source: docLabel };
        }
      }

      // Bank name
      if (
        normKey.includes("bank_name") ||
        normKey.includes("financial_institution") ||
        normPrompt.includes("bank name") ||
        normPrompt.includes("name of your bank")
      ) {
        if (normFKey === "bank_name" || normFKey === "institution") {
          return { value: fVal, source: docLabel };
        }
      }

      // Bank account number
      if (
        normKey.includes("account_number") ||
        normPrompt.includes("bank account number") ||
        normPrompt.includes("account number")
      ) {
        if (normFKey === "account_number") {
          return { value: fVal, source: docLabel };
        }
      }

      // Balance / Funds
      if (
        normKey.includes("balance") ||
        normKey.includes("proof_of_funds") ||
        normKey.includes("funds_amount") ||
        normPrompt.includes("bank balance") ||
        normPrompt.includes("proof of funds") ||
        normPrompt.includes("available funds")
      ) {
        if (normFKey === "balance" || normFKey === "proof_of_funds" || normFKey === "funds") {
          return { value: fVal, source: docLabel };
        }
      }

      // Employer / Company name
      if (
        normKey.includes("employer") ||
        normKey.includes("company_name") ||
        normKey.includes("sponsor_name") ||
        normPrompt.includes("employer name") ||
        normPrompt.includes("company name") ||
        normPrompt.includes("sponsoring organization")
      ) {
        if (normFKey === "employer_name" || normFKey === "company_name" || normFKey === "sponsor_name") {
          return { value: fVal, source: docLabel };
        }
      }

      // Salary / Remuneration
      if (
        normKey.includes("salary") ||
        normKey.includes("remuneration") ||
        normPrompt.includes("monthly salary") ||
        normPrompt.includes("remuneration")
      ) {
        if (normFKey === "monthly_salary" || normFKey === "salary" || normFKey === "remuneration") {
          return { value: fVal, source: docLabel };
        }
      }

      // Tax Year / Income
      if (
        normKey.includes("tax_year") ||
        normPrompt.includes("tax year") ||
        normPrompt.includes("assessment year")
      ) {
        if (normFKey === "tax_year") {
          return { value: fVal, source: docLabel };
        }
      }

      if (
        normKey.includes("annual_income") ||
        normKey.includes("gross_income") ||
        normPrompt.includes("annual income") ||
        normPrompt.includes("total income")
      ) {
        if (normFKey === "annual_income" || normFKey === "gross_income") {
          return { value: fVal, source: docLabel };
        }
      }

      if (
        normKey.includes("tax_paid") ||
        normPrompt.includes("tax paid") ||
        normPrompt.includes("total tax paid")
      ) {
        if (normFKey === "tax_paid" || normFKey === "paid_tax") {
          return { value: fVal, source: docLabel };
        }
      }

      // Position / Job Title
      if (
        normKey.includes("position") ||
        normKey.includes("job_title") ||
        normPrompt.includes("job title") ||
        normPrompt.includes("position in company")
      ) {
        if (normFKey === "position" || normFKey === "job_title") {
          return { value: fVal, source: docLabel };
        }
      }

      // Full Name
      if (
        normKey === "full_name" ||
        normKey === "applicant_name" ||
        normKey === "name" ||
        (normPrompt.includes("full name") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse") && !normPrompt.includes("employer"))
      ) {
        if (normFKey === "full_name" || normFKey === "applicant_name" || normFKey === "name") {
          const clean = fVal.split(/\r?\n/)[0].trim();
          if (clean.length >= 3) return { value: clean, source: docLabel };
        }
      }

      // Date of Birth
      if (
        normKey === "date_of_birth" ||
        normKey === "dob" ||
        normKey === "birth_date" ||
        normKey === "applicant_dob" ||
        (normPrompt.includes("date of birth") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse"))
      ) {
        if (normFKey === "date_of_birth" || normFKey === "dob" || normFKey === "birth_date") {
          const iso = normalizeDateToISO(fVal);
          return { value: iso, source: docLabel };
        }
      }

      // Nationality / Citizenship
      if (
        normKey === "nationality" ||
        normKey === "citizenship" ||
        normKey === "country_of_citizenship" ||
        (normPrompt.includes("nationality") && !normPrompt.includes("father") && !normPrompt.includes("mother") && !normPrompt.includes("spouse"))
      ) {
        if (normFKey === "nationality" || normFKey === "citizenship") {
          return { value: fVal, source: docLabel };
        }
      }

      // Sex / Gender
      if (
        normKey === "sex" ||
        normKey === "gender" ||
        normPrompt.includes("what sex") ||
        normPrompt.includes("gender")
      ) {
        if (normFKey === "sex" || normFKey === "gender") {
          const s = fVal.toLowerCase();
          const mapped = s.startsWith("m") ? "male" : s.startsWith("f") ? "female" : fVal;
          return { value: mapped, source: docLabel };
        }
      }

      // Marital Status
      if (
        normKey === "marital_status" ||
        normPrompt.includes("marital status")
      ) {
        if (normFKey === "marital_status" || normFKey === "marital") {
          return { value: fVal.toLowerCase(), source: docLabel };
        }
      }

      // Occupation
      if (
        normKey === "occupation" ||
        normKey === "profession" ||
        normKey === "job_title" ||
        normPrompt.includes("occupation") ||
        normPrompt.includes("profession")
      ) {
        if (normFKey === "occupation" || normFKey === "profession" || normFKey === "job_title") {
          return { value: fVal, source: docLabel };
        }
      }

      // Current Country / Residing
      if (
        normKey === "current_location_country" ||
        normKey === "current_country" ||
        normKey === "residence_country" ||
        normKey === "current_residence_country" ||
        normPrompt.includes("currently residing in") ||
        normPrompt.includes("current country")
      ) {
        if (normFKey === "current_country" || normFKey === "current_residence" || normFKey === "residence_country") {
          return { value: fVal, source: docLabel };
        }
      }

      // Phone Number
      if (
        normKey === "phone_number" ||
        normKey === "phone" ||
        normKey === "contact_number" ||
        normPrompt.includes("phone number")
      ) {
        if (normFKey === "phone_number" || normFKey === "phone" || normFKey === "mobile_number") {
          return { value: fVal, source: docLabel };
        }
      }

      // Departure Date
      if (
        normKey.includes("departure_date") ||
        normPrompt.includes("date of departure") ||
        normPrompt.includes("arrival date")
      ) {
        if (normFKey === "departure_date") {
          return { value: fVal, source: docLabel };
        }
      }
    }
  }

  return null;
}


export function IntakeStep({
  state,
  profile,
  onAnswer,
  onProceedToEligibility,
  targetKey,
  targetTimestamp,
  token,
  caseId,
  onRefresh,
}: IntakeStepProps) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>({});
  const [savingFields, setSavingFields] = useState<Record<string, boolean>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});
  const [activeSection, setActiveSection] = useState<string | null>(() => {
    for (const q of state.questions) {
      if (
        q.required !== false &&
        (state.answers[q.key] === undefined ||
          state.answers[q.key] === null ||
          state.answers[q.key] === "")
      ) {
        return q.section || null;
      }
    }
    return state.questions[0]?.section || null;
  });
  const [enumSearch, setEnumSearch] = useState<Record<string, string>>({});
  const [openSelectorKey, setOpenSelectorKey] = useState<string | null>(null);
  const [viewAll, setViewAll] = useState<boolean>(false);
  const [highlightedKey, setHighlightedKey] = useState<string | null>(null);
  const [walletDocs, setWalletDocs] = useState<WalletDocument[]>([]);
  const [autofilledSources, setAutofilledSources] = useState<Record<string, string>>({});
  const [syncingWallet, setSyncingWallet] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [isProceeding, setIsProceeding] = useState<boolean>(false);

  const onAnswerRef = useRef(onAnswer);
  onAnswerRef.current = onAnswer;
  const autoSubmittedRef = useRef<Set<string>>(new Set());
  const draftsRef = useRef<Record<string, unknown>>({});
  draftsRef.current = drafts;
  const debounceTimersRef = useRef<Record<string, NodeJS.Timeout>>({});
  const initializedSectionRef = useRef(false);

  useEffect(() => {
    return () => {
      Object.values(debounceTimersRef.current).forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    if (!token) return;
    getWallet(token).then((docs) => {
      setWalletDocs(docs);
    }).catch(() => {});
  }, [token]);

  function validateField(q: (typeof state.questions)[number], value: unknown): string | null {
    const isOptional = q.required === false;
    if (value === undefined || value === null || (typeof value === "string" && value.trim() === "")) {
      return isOptional ? null : "This field is required.";
    }

    if (q.type === "integer") {
      const num = typeof value === "number" ? value : Number(value);
      if (isNaN(num) || !Number.isInteger(num)) {
        return "Please enter a valid whole number.";
      }
      if (q.min_value !== undefined && q.min_value !== null && num < q.min_value) {
        return `Value must be at least ${q.min_value}.`;
      }
      if (q.max_value !== undefined && q.max_value !== null && num > q.max_value) {
        return `Value must be at most ${q.max_value}.`;
      }
      return null;
    }

    if (q.type === "string") {
      const str = String(value).trim();
      if (q.min_length !== undefined && q.min_length !== null && str.length < q.min_length) {
        return `Must be at least ${q.min_length} characters.`;
      }
      if (q.max_length !== undefined && q.max_length !== null && str.length > q.max_length) {
        return `Must be at most ${q.max_length} characters.`;
      }
      return null;
    }

    if (q.type === "date") {
      const str = String(value).trim();
      if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        return "Please enter a valid date in YYYY-MM-DD format.";
      }
      const d = new Date(str);
      if (isNaN(d.getTime())) {
        return "Please enter a valid calendar date.";
      }
      return null;
    }

    if (q.type === "enum" && q.options && q.options.length > 0) {
      const str = String(value).trim();
      if (!q.options.includes(str)) {
        return "Please choose a valid option.";
      }
      return null;
    }

    return null;
  }

  // Auto-fill unanswered fields from profile and verified document wallet items
  useEffect(() => {
    const toAutoFill: Record<string, unknown> = {};
    const newSources: Record<string, string> = {};

    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined || autoSubmittedRef.current.has(q.key)) continue;
      const match = getAutofillValueForQuestion(q.key, q.prompt, profile, walletDocs);
      if (match) {
        let val: string | null = match.value;
        if (q.type === "enum" && q.options?.length) {
          val = matchEnumOption(val, q.options);
        }
        if (val) {
          toAutoFill[q.key] = val;
          newSources[q.key] = match.source;
        }
      }
    }

    if (Object.keys(toAutoFill).length > 0) {
      setDrafts((prev) => ({ ...prev, ...toAutoFill }));
      setAutofilledSources((prev) => ({ ...prev, ...newSources }));
      for (const [key, val] of Object.entries(toAutoFill)) {
        if (val !== undefined) {
          autoSubmittedRef.current.add(key);
          void onAnswerRef.current(key, val);
        }
      }
    }
  }, [profile, walletDocs, state.questions, state.answers]);

  // Identify sources for fields that were already filled from DB intake answers
  useEffect(() => {
    if (walletDocs.length === 0 && !profile) return;
    const traced: Record<string, string> = {};
    for (const q of state.questions) {
      if (state.answers[q.key] !== undefined && !autofilledSources[q.key]) {
        const match = getAutofillValueForQuestion(q.key, q.prompt, profile, walletDocs);
        if (match && String(state.answers[q.key]).trim().toLowerCase() === match.value.toLowerCase()) {
          traced[q.key] = match.source;
        }
      }
    }
    if (Object.keys(traced).length > 0) {
      setAutofilledSources((prev) => ({ ...prev, ...traced }));
    }
  }, [walletDocs, profile, state.questions, state.answers, autofilledSources]);

  async function handleManualSync() {
    if (!token) return;
    setSyncingWallet(true);
    setSyncMessage(null);
    try {
      const res = await syncProfileFromWallet(token);
      const refreshedDocs = await getWallet(token);
      setWalletDocs(refreshedDocs);
      if (onRefresh) onRefresh();

      setSyncMessage(res.message || `Synced ${res.fields_synced?.length || 0} fields from verified documents.`);
      setTimeout(() => setSyncMessage(null), 8000);
    } catch (err) {
      setSyncMessage(err instanceof Error ? err.message : "Sync failed");
      setTimeout(() => setSyncMessage(null), 8000);
    } finally {
      setSyncingWallet(false);
    }
  }

  // Group questions by section if present, or assign defaults
  const sectionsMap = useMemo(() => {
    const map = new Map<string, IntakeQuestion[]>();
    for (const q of state.questions) {
      const sec = q.section || "General Details";
      if (!map.has(sec)) map.set(sec, []);
      map.get(sec)!.push(q);
    }
    return map;
  }, [state.questions]);

  const sectionKeys = useMemo(() => Array.from(sectionsMap.keys()), [sectionsMap]);

  const isQuestionAnswered = useCallback(
    (q: IntakeQuestion): boolean => {
      const serverVal = state.answers[q.key];
      if (serverVal !== undefined && serverVal !== null && serverVal !== "") {
        return true;
      }
      const draftVal = drafts[q.key];
      if (
        draftVal !== undefined &&
        draftVal !== null &&
        draftVal !== "" &&
        !fieldErrors[q.key]
      ) {
        return true;
      }
      return false;
    },
    [state.answers, drafts, fieldErrors]
  );

  // Compute first incomplete section so users are automatically taken to unanswered fields
  const firstIncompleteSection = useMemo(() => {
    for (const sec of sectionKeys) {
      const qs = sectionsMap.get(sec) || [];
      const reqQuestions = qs.filter((q) => q.required !== false);
      const answered = reqQuestions.length > 0
        ? reqQuestions.filter(isQuestionAnswered).length
        : qs.filter(isQuestionAnswered).length;
      const targetCount = reqQuestions.length > 0 ? reqQuestions.length : qs.length;
      if (answered < targetCount) return sec;
    }
    return null;
  }, [sectionKeys, sectionsMap, isQuestionAnswered]);

  // One-time initialization of activeSection to first incomplete section once sections are loaded
  useEffect(() => {
    if (initializedSectionRef.current) return;
    if (sectionKeys.length > 0) {
      initializedSectionRef.current = true;
      if (!activeSection || !sectionKeys.includes(activeSection)) {
        setActiveSection(firstIncompleteSection || sectionKeys[0]);
      }
    }
  }, [sectionKeys, activeSection, firstIncompleteSection]);

  // Switch to targetKey section, smoothly scroll to question, and highlight
  useEffect(() => {
    if (targetKey) {
      const q = findQuestionByKey(state.questions, targetKey);
      if (q) {
        if (q.section && sectionKeys.includes(q.section)) {
          setActiveSection(q.section);
        }
        setHighlightedKey(q.key);

        const scrollTimer = setTimeout(() => {
          const el = document.getElementById(`question-${q.key}`);
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            const input = el.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
              "input, select, textarea"
            );
            if (input) {
              input.focus({ preventScroll: true });
            }
          }
        }, 150);

        const fadeTimer = setTimeout(() => {
          setHighlightedKey((prev) => (prev === q.key ? null : prev));
        }, 6000);

        return () => {
          clearTimeout(scrollTimer);
          clearTimeout(fadeTimer);
        };
      }
    }
  }, [targetKey, targetTimestamp, state.questions, sectionKeys]);

  const currentSectionKey = useMemo(() => {
    if (activeSection && sectionKeys.includes(activeSection)) {
      return activeSection;
    }
    return sectionKeys[0] ?? "General Details";
  }, [activeSection, sectionKeys]);

  const currentSectionIndex = sectionKeys.indexOf(currentSectionKey);

  function handleChange(key: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [key]: value }));

    if (debounceTimersRef.current[key]) {
      clearTimeout(debounceTimersRef.current[key]);
      delete debounceTimersRef.current[key];
    }

    const q = state.questions.find((item) => item.key === key);
    if (q) {
      let valToSend: unknown = value;
      if (q.type === "integer" && typeof value === "string") {
        if (value.trim() === "") {
          valToSend = q.required === false ? null : "";
        } else {
          const parsed = Number.parseInt(value, 10);
          valToSend = Number.isNaN(parsed) ? value : parsed;
        }
      } else if (typeof value === "string" && value.trim() === "") {
        valToSend = q.required === false ? null : "";
      }

      const err = validateField(q, valToSend);
      setFieldErrors((prev) => ({ ...prev, [key]: err }));

      // Debounced auto-save (500ms) for responsive updates without manual blur
      if (!err && valToSend !== "" && valToSend !== null && valToSend !== undefined) {
        debounceTimersRef.current[key] = setTimeout(() => {
          void handleSubmit(key);
        }, 500);
      }
    }
  }

  async function handleSubmit(key: string): Promise<boolean> {
    if (debounceTimersRef.current[key]) {
      clearTimeout(debounceTimersRef.current[key]);
      delete debounceTimersRef.current[key];
    }

    const raw = draftsRef.current[key] !== undefined ? draftsRef.current[key] : drafts[key];
    if (raw === undefined) return true;

    const q = state.questions.find((item) => item.key === key);
    if (!q) return true;

    let valToSend: unknown = raw;
    if (q.type === "integer") {
      if (typeof raw === "string") {
        if (raw.trim() === "") {
          valToSend = q.required === false ? null : "";
        } else {
          const parsed = Number.parseInt(raw, 10);
          valToSend = Number.isNaN(parsed) ? raw : parsed;
        }
      }
    } else if (typeof raw === "string" && raw.trim() === "") {
      valToSend = q.required === false ? null : "";
    }

    const clientError = validateField(q, valToSend);
    if (clientError) {
      setFieldErrors((prev) => ({ ...prev, [key]: clientError }));
      return false;
    }

    setFieldErrors((prev) => ({ ...prev, [key]: null }));
    setSavingFields((prev) => ({ ...prev, [key]: true }));

    try {
      await onAnswer(key, valToSend);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid answer provided.";
      setFieldErrors((prev) => ({ ...prev, [key]: msg }));
      return false;
    } finally {
      setSavingFields((prev) => ({ ...prev, [key]: false }));
    }
  }

  async function flushAllDrafts(): Promise<boolean> {
    Object.values(debounceTimersRef.current).forEach(clearTimeout);
    debounceTimersRef.current = {};

    const activeKeys = Object.keys(draftsRef.current).filter(
      (k) => draftsRef.current[k] !== undefined && draftsRef.current[k] !== ""
    );
    if (activeKeys.length === 0) return true;

    let allOk = true;
    for (const k of activeKeys) {
      const ok = await handleSubmit(k);
      if (!ok) allOk = false;
    }
    return allOk;
  }

  async function handleProceed() {
    if (isProceeding) return;
    setIsProceeding(true);
    try {
      const ok = await flushAllDrafts();
      if (ok && onProceedToEligibility) {
        onProceedToEligibility();
      }
    } finally {
      setIsProceeding(false);
    }
  }

  async function handleDirectAnswer(key: string, value: unknown) {
    if (debounceTimersRef.current[key]) {
      clearTimeout(debounceTimersRef.current[key]);
      delete debounceTimersRef.current[key];
    }
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setFieldErrors((prev) => ({ ...prev, [key]: null }));
    try {
      await onAnswer(key, value);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid selection.";
      setFieldErrors((prev) => ({ ...prev, [key]: msg }));
    }
  }

  // Clear drafts that have successfully synced to state.answers
  useEffect(() => {
    setDrafts((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const k of Object.keys(next)) {
        if (
          state.answers[k] !== undefined &&
          (state.answers[k] === next[k] || String(state.answers[k]) === String(next[k]))
        ) {
          delete next[k];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [state.answers]);

  const allRequiredQuestions = useMemo(
    () => state.questions.filter((q) => q.required !== false),
    [state.questions]
  );
  const totalAnsweredCount = useMemo(
    () => state.questions.filter(isQuestionAnswered).length,
    [state.questions, isQuestionAnswered]
  );
  const answeredRequiredCount = useMemo(
    () => allRequiredQuestions.filter(isQuestionAnswered).length,
    [allRequiredQuestions, isQuestionAnswered]
  );
  const isAllComplete = allRequiredQuestions.length > 0
    ? answeredRequiredCount >= allRequiredQuestions.length
    : totalAnsweredCount === state.questions.length;
  const totalRemainingCount = allRequiredQuestions.length > 0
    ? Math.max(0, allRequiredQuestions.length - answeredRequiredCount)
    : Math.max(0, state.questions.length - totalAnsweredCount);

  const pct = state.questions.length > 0
    ? Math.round((totalAnsweredCount / state.questions.length) * 100)
    : 0;

  const currentQuestions = sectionsMap.get(currentSectionKey) || state.questions;
  const currentRequired = currentQuestions.filter((q) => q.required !== false);
  const currentAnsweredCount = currentQuestions.filter(isQuestionAnswered).length;
  const currentAnsweredRequired = currentRequired.filter(isQuestionAnswered).length;
  const isCurrentSectionComplete = currentRequired.length > 0
    ? currentAnsweredRequired >= currentRequired.length
    : currentAnsweredCount === currentQuestions.length;
  const remainingInCurrent = currentRequired.length > 0
    ? Math.max(0, currentRequired.length - currentAnsweredRequired)
    : Math.max(0, currentQuestions.length - currentAnsweredCount);

  function optionLabel(q: (typeof state.questions)[number], option: string): string {
    // The printed wording where the form has one; otherwise the value made readable.
    return q.option_labels?.[option] ?? option.replaceAll("_", " ");
  }

  function renderQuestion(q: (typeof state.questions)[number]) {
    const current = (drafts[q.key] !== undefined ? drafts[q.key] : state.answers[q.key]) as string | number | boolean | undefined;
    const hasOptions = q.type === "enum" && q.options && q.options.length > 0;
    const optionsCount = q.options?.length ?? 0;
    const isLongEnum = hasOptions && optionsCount > 5;
    const searchVal = enumSearch[q.key] || "";
    const filteredOptions = isLongEnum && searchVal
      ? q.options!.filter((opt) =>
          `${opt} ${q.option_labels?.[opt] ?? ""}`.toLowerCase().includes(searchVal.toLowerCase()),
        )
      : q.options || [];

    const isDateInput =
      q.type === "date" ||
      ((q.key.includes("date") ||
        q.key.includes("expiry") ||
        q.key.includes("expiration") ||
        q.key === "dob" ||
        q.key.includes("date_of_birth") ||
        q.key.includes("birth_date") ||
        q.prompt.toLowerCase().includes("yyyy-mm-dd") ||
        q.prompt.toLowerCase().includes("date of birth") ||
        q.prompt.toLowerCase().includes("expiry date")) &&
        !q.key.includes("place") &&
        !q.prompt.toLowerCase().includes("where were you born") &&
        !q.prompt.toLowerCase().includes("place of birth"));

    const isFullWidth = hasOptions && optionsCount > 8;

    const isHighlighted = q.key === highlightedKey;

    const isOptional = q.required === false;

    const fieldError = fieldErrors[q.key];
    const isAnswered =
      state.answers[q.key] !== undefined || (drafts[q.key] !== undefined && drafts[q.key] !== "");

    return (
      <Card
        key={q.key}
        id={`question-${q.key}`}
        className={`p-4 sm:p-5 flex flex-col justify-between rounded-xl border transition-all duration-150 bg-card shadow-xs ${
          isFullWidth ? "col-span-1 md:col-span-2" : "col-span-1"
        } ${
          fieldError
            ? "border-rose-500/80 ring-2 ring-rose-500/20 bg-rose-500/[0.02]"
            : isHighlighted
              ? "ring-2 ring-primary/40 border-primary bg-primary/[0.03]"
              : isAnswered
                ? "border-border/90 dark:border-slate-800 hover:border-primary/40 dark:hover:border-slate-700"
                : "border-border/90 dark:border-slate-800 hover:border-primary/40 dark:hover:border-slate-700"
        }`}
      >
        <div className="space-y-3">
          {/* Card Header: Question prompt + status badge */}
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-1 min-w-0">
              <label
                className={`block text-[13px] sm:text-sm font-medium tracking-tight leading-snug ${
                  fieldError ? "text-rose-600 dark:text-rose-400" : "text-foreground"
                }`}
              >
                {q.prompt}
                {!isOptional && <span className="text-rose-500 ml-0.5">*</span>}
              </label>

              {q.hint && (
                <p className="text-xs text-muted-foreground/80 leading-relaxed">{q.hint}</p>
              )}

              <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                {isOptional && (
                  <span className="text-[10px] font-normal text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded border border-border/50">
                    Optional
                  </span>
                )}
                {autofilledSources[q.key] && (
                  <span className="text-[10px] font-medium text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 inline-flex items-center gap-1">
                    <Sparkles className="size-2.5" />
                    Auto-filled
                  </span>
                )}
              </div>
            </div>

            {/* Status indicator on top right */}
            <div className="shrink-0 pt-0.5">
              {savingFields[q.key] ? (
                <span className="inline-flex items-center gap-1 text-[11px] text-primary font-medium">
                  <Loader2 className="size-3 animate-spin" />
                </span>
              ) : isAnswered ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  <Check className="size-3" />
                  Answered
                </span>
              ) : isHighlighted ? (
                <span className="text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                  Target
                </span>
              ) : null}
            </div>
          </div>

          {(() => {
            const isCountryQuestion =
              !["education_country", "study_location", "school_location"].includes(q.key) &&
              (
                q.key === "nationality" ||
                q.key.endsWith("_nationality") ||
                q.key === "citizenship" ||
                q.key.endsWith("_citizenship") ||
                q.key === "passport_country" ||
                q.key === "birth_country" ||
                q.key === "current_residence_country" ||
                q.key === "residence_country" ||
                q.prompt.toLowerCase().includes("what is your nationality") ||
                q.prompt.toLowerCase().includes("supporter's nationality") ||
                q.prompt.toLowerCase().includes("guarantor's nationality") ||
                q.prompt.toLowerCase().includes("country of citizenship") ||
                q.prompt.toLowerCase().includes("passport country")
              );

            const hasSelected = current !== undefined && current !== "" && current !== null;
            const isEditing = openSelectorKey === q.key;

            // ── 1. Country / Nationality Picker ──
            if (isCountryQuestion) {
              if (hasSelected && !isEditing) {
                const currentStr = String(current);
                const isOther = currentStr.toLowerCase() === "other";
                const cMeta = isOther
                  ? { flag: "🌐", name: "Other / Not Listed", code: "other" }
                  : matchCountry(currentStr);
                return (
                  <div className={`flex items-center justify-between rounded-lg border p-2.5 text-xs ${fieldError ? "border-rose-500 bg-rose-500/5" : "border-border/90 dark:border-slate-800 bg-muted/20"}`}>
                    <div className="flex items-center gap-2.5 min-w-0">
                      <CountryFlag code={cMeta.code} className="size-5 shrink-0" />
                      <div className="min-w-0">
                        <p className="font-semibold text-xs text-foreground truncate">{cMeta.name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">
                          {cMeta.code || currentStr.toUpperCase()}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setOpenSelectorKey(q.key);
                        setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                      }}
                      className="rounded-md border border-border/80 dark:border-slate-700 bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-accent transition-colors shrink-0"
                    >
                      Change
                    </button>
                  </div>
                );
              }

              const countriesToDisplay = searchVal
                ? searchCountries(searchVal, 40)
                : ALL_COUNTRIES.slice(0, 30);

              return (
                <div className="space-y-2 pt-1">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground/60" />
                    <input
                      type="text"
                      value={searchVal}
                      onChange={(e) => setEnumSearch((prev) => ({ ...prev, [q.key]: e.target.value }))}
                      placeholder="Search country name or code..."
                      autoFocus={isEditing}
                      className={`h-9 w-full rounded-lg border bg-background/90 pl-8 pr-3 text-xs outline-none transition-colors ${fieldError ? "border-rose-500 focus-visible:ring-rose-500/50" : "border-border/90 dark:border-slate-700 hover:dark:border-slate-600 focus:border-primary focus:ring-1 focus:ring-primary/20"}`}
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-52 overflow-y-auto pr-1">
                    {countriesToDisplay.map((country) => {
                      const isSelected =
                        String(current).toUpperCase() === country.code.toUpperCase() ||
                        String(current).toLowerCase() === country.name.toLowerCase();
                      return (
                        <button
                          key={country.code}
                          type="button"
                          onClick={() => {
                            const answerVal =
                              q.type === "enum" && q.options && q.options.some((o) => o.toLowerCase() === country.name.toLowerCase())
                                ? country.name
                                : country.code;
                            void handleDirectAnswer(q.key, answerVal);
                            setOpenSelectorKey(null);
                            setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                          }}
                          className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition-all ${
                            isSelected
                              ? "border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary/30"
                              : "border-border/80 dark:border-slate-800 hover:dark:border-slate-700 hover:bg-muted/60 text-foreground bg-background/50"
                          }`}
                        >
                          <CountryFlag code={country.code} className="size-4 shrink-0" />
                          <span className="truncate flex-1 font-medium">{country.name}</span>
                          <span className="text-[10px] text-muted-foreground font-mono">{country.code}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            }

            // ── 2. Standard Enum Questions ──
            if (q.type === "enum" && q.options) {
              if (optionsCount <= 4) {
                return (
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {q.options.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => void handleDirectAnswer(q.key, opt)}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary/30 shadow-xs"
                            : "border-border/90 dark:border-slate-800 bg-background hover:bg-muted/60 hover:border-border dark:hover:border-slate-700 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {optionLabel(q, opt)}
                      </button>
                    ))}
                  </div>
                );
              }

              if (hasSelected && !isEditing) {
                return (
                  <div className={`flex items-center justify-between rounded-lg border p-2.5 text-xs ${fieldError ? "border-rose-500 bg-rose-500/5" : "border-border/90 dark:border-slate-800 bg-muted/20"}`}>
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="size-1.5 rounded-full bg-primary shrink-0" />
                      <span className="font-medium text-foreground text-xs truncate">{optionLabel(q, String(current))}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setOpenSelectorKey(q.key);
                        setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                      }}
                      className="rounded-md border border-border/80 dark:border-slate-700 bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-accent transition-colors shrink-0"
                    >
                      Change
                    </button>
                  </div>
                );
              }

              return (
                <div className="space-y-2 pt-1">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground/60" />
                    <input
                      type="text"
                      value={searchVal}
                      onChange={(e) => setEnumSearch((prev) => ({ ...prev, [q.key]: e.target.value }))}
                      placeholder={`Search ${optionsCount} options...`}
                      autoFocus={isEditing}
                      className={`h-9 w-full rounded-lg border bg-background/90 pl-8 pr-3 text-xs outline-none transition-colors ${fieldError ? "border-rose-500 focus-visible:ring-rose-500/50" : "border-border/90 dark:border-slate-700 hover:dark:border-slate-600 focus:border-primary focus:ring-1 focus:ring-primary/20"}`}
                    />
                  </div>

                  <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
                    {filteredOptions.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => {
                          void handleDirectAnswer(q.key, opt);
                          setOpenSelectorKey(null);
                          setEnumSearch((prev) => ({ ...prev, [q.key]: "" }));
                        }}
                        className={`rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all ${
                          current === opt
                            ? "border-primary bg-primary/10 text-primary font-semibold ring-1 ring-primary/30 shadow-xs"
                            : "border-border/90 dark:border-slate-800 bg-background/50 hover:bg-muted/70 hover:border-border dark:hover:border-slate-700 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {optionLabel(q, opt)}
                      </button>
                    ))}
                    {filteredOptions.length === 0 && (
                      <p className="text-xs text-muted-foreground py-1">No options match &quot;{searchVal}&quot;</p>
                    )}
                  </div>
                </div>
              );
            }

            // ── 3. Boolean Questions (Yes / No) ──
            if (q.type === "boolean") {
              return (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => void handleDirectAnswer(q.key, true)}
                    className={`h-9 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                      current === true
                        ? "border-emerald-500/70 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold ring-1 ring-emerald-500/30 shadow-xs"
                        : "border-border/90 dark:border-slate-700 bg-background hover:bg-muted/60 hover:border-border dark:hover:border-slate-600 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Check className="size-3.5" />
                    <span>Yes</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDirectAnswer(q.key, false)}
                    className={`h-9 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                      current === false
                        ? "border-muted-foreground/50 bg-muted text-foreground font-semibold ring-1 ring-border shadow-xs"
                        : "border-border/90 dark:border-slate-700 bg-background hover:bg-muted/60 hover:border-border dark:hover:border-slate-600 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <span>No</span>
                  </button>
                </div>
              );
            }

            // ── 4. Text, number, date inputs ──
            return (
              <div className="pt-0.5">
                <input
                  type={q.type === "integer" ? "number" : isDateInput ? "date" : "text"}
                  min={q.type === "integer" && q.min_value !== undefined && q.min_value !== null ? q.min_value : undefined}
                  max={q.type === "integer" && q.max_value !== undefined && q.max_value !== null ? q.max_value : undefined}
                  step={q.type === "integer" ? "1" : undefined}
                  value={
                    isDateInput
                      ? (normalizeDateToISO(String(current ?? "")) || String(current ?? ""))
                      : String(current ?? "")
                  }
                  onChange={(e) => handleChange(q.key, e.target.value)}
                  onBlur={() => void handleSubmit(q.key)}
                  onPaste={(e) => {
                    const text = e.clipboardData.getData("text").trim();
                    if (text) {
                      handleChange(q.key, text);
                      const parsed = q.type === "integer" ? (parseInt(text, 10) || text) : text;
                      void handleDirectAnswer(q.key, parsed);
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void handleSubmit(q.key);
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  placeholder={`Enter ${q.key.replaceAll("_", " ")}...`}
                  className={`h-10 w-full rounded-lg border bg-background/80 px-3.5 text-sm outline-none transition-all placeholder:text-muted-foreground/40 ${
                    fieldError
                      ? "border-rose-500 focus:ring-2 focus:ring-rose-500/25 bg-rose-500/[0.02]"
                      : "border-border/90 dark:border-slate-700 hover:border-muted-foreground/50 dark:hover:border-slate-600 focus:border-primary dark:focus:border-primary focus:ring-2 focus:ring-primary/20 shadow-2xs"
                  }`}
                />
              </div>
            );
          })()}
        </div>

        {fieldError && (
          <div className="flex items-center gap-1.5 text-xs text-rose-600 dark:text-rose-400 font-medium pt-2 animate-in fade-in duration-200">
            <AlertCircle className="size-3.5 shrink-0 text-rose-500" />
            <span>{fieldError}</span>
          </div>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress & Section Tabs Header */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Intake Questionnaire &amp; Screening</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {totalAnsweredCount} of {state.questions.length} total fields completed ({pct}%)
              {isAllComplete ? " · Ready for Eligibility Evaluation" : ""}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {sectionKeys.length > 1 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setViewAll((prev) => !prev)}
                className="h-7 text-xs gap-1 px-2.5 text-muted-foreground hover:text-foreground"
              >
                {viewAll ? <LayoutGrid className="size-3.5" /> : <ListChecks className="size-3.5" />}
                {viewAll ? "Tabbed View" : "View All Questions"}
              </Button>
            )}
            <Badge tone={pct === 100 ? "success" : "default"} className="text-xs font-medium">
              {sectionKeys.length} Modules ({pct}% complete)
            </Badge>
          </div>
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-primary transition-all duration-300" style={{ width: `${pct}%` }} />
        </div>
      </div>

      {/* Document Autofill Active Banner */}
      {Object.keys(autofilledSources).length > 0 && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-xs shadow-2xs flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <div>
              <span className="font-semibold text-foreground">
                Document Auto-fill Active
              </span>
              <span className="text-muted-foreground ml-1.5">
                {Object.keys(autofilledSources).length} question{Object.keys(autofilledSources).length === 1 ? "" : "s"} auto-filled from your verified documents (
                {Array.from(new Set(Object.values(autofilledSources))).join(", ")}). You may review or modify any response.
              </span>
            </div>
          </div>
          {token && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualSync}
              disabled={syncingWallet}
              className="h-7 text-xs gap-1.5 shrink-0 border-emerald-500/30 hover:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
            >
              <RefreshCw className={`size-3 ${syncingWallet ? "animate-spin" : ""}`} />
              {syncingWallet ? "Syncing..." : "Re-sync Documents"}
            </Button>
          )}
        </div>
      )}

      {syncMessage && (
        <div className="rounded-md border border-primary/20 bg-primary/5 p-2.5 text-xs text-primary flex items-center gap-2">
          <CheckCircle2 className="size-4 shrink-0 text-primary" />
          <span>{syncMessage}</span>
        </div>
      )}

      {/* Section Navigation Tabs (Tabbed Mode) */}
      {!viewAll && sectionKeys.length > 1 && (
        <div className="flex flex-wrap gap-2 border-b pb-3">
          {sectionKeys.map((secName) => {
            const secQuestions = sectionsMap.get(secName) || [];
            const reqQuestions = secQuestions.filter((q) => q.required !== false);
            const answeredInSec = secQuestions.filter(isQuestionAnswered).length;
            const answeredReqInSec = reqQuestions.filter(isQuestionAnswered).length;
            const isSecComplete = reqQuestions.length > 0
              ? answeredReqInSec >= reqQuestions.length
              : answeredInSec === secQuestions.length;
            const isActive = secName === currentSectionKey;

            return (
              <button
                key={secName}
                onClick={async () => {
                  await flushAllDrafts();
                  setActiveSection(secName);
                }}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-sm font-semibold ring-2 ring-primary/30"
                    : isSecComplete
                      ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                      : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground border"
                }`}
              >
                {isSecComplete ? (
                  <Check className="size-3 text-emerald-500 shrink-0" />
                ) : (
                  <AlertCircle className="size-3 text-muted-foreground/60 shrink-0" />
                )}
                <span>{secName}</span>
                <span className={`text-[10px] font-semibold ${isSecComplete ? "opacity-80" : "text-muted-foreground"}`}>
                  ({answeredInSec}/{secQuestions.length})
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Questions Rendering */}
      {state.questions.length === 0 ? (
        <p className="text-sm text-muted-foreground">No questions available for this scope.</p>
      ) : viewAll ? (
        /* View All Mode: Render all sections sequentially */
        <div className="space-y-8">
          {sectionKeys.map((secName) => {
            const secQuestions = sectionsMap.get(secName) || [];
            const reqQuestions = secQuestions.filter((q) => q.required !== false);
            const secAnswered = secQuestions.filter(isQuestionAnswered).length;
            const secReqAnswered = reqQuestions.filter(isQuestionAnswered).length;
            const isComplete = reqQuestions.length > 0
              ? secReqAnswered >= reqQuestions.length
              : secAnswered === secQuestions.length;

            return (
              <div key={secName} className="space-y-3">
                <div className="flex items-center justify-between border-b pb-2.5">
                  <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-2.5">
                    <span>{secName}</span>
                    <Badge tone={isComplete ? "success" : "default"} className="text-[11px] font-medium">
                      {secAnswered} / {secQuestions.length} answered
                    </Badge>
                  </h4>
                </div>


                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {secQuestions.map(renderQuestion)}
                </div>
              </div>
            );
          })}

          {/* View All Bottom Completion Banner */}
          <div className="rounded-[var(--radius)] border p-4 bg-muted/30 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-muted-foreground flex items-center gap-2">
              {!isAllComplete && (
                <AlertTriangle className="size-4 text-amber-500 shrink-0" />
              )}
              <span>
                {isAllComplete
                  ? "All required questions answered across all modules."
                  : `${totalRemainingCount} question(s) remaining. You may proceed to documents.`}
              </span>
            </div>
            {onProceedToEligibility && (
              <Button
                onClick={handleProceed}
                disabled={isProceeding}
                className={`gap-2 text-xs font-semibold text-white shadow-sm ${
                  isAllComplete
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-primary hover:bg-primary/90"
                }`}
              >
                {isProceeding ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : isAllComplete ? (
                  <CheckCircle2 className="size-4" />
                ) : (
                  <AlertTriangle className="size-3.5 text-amber-300" />
                )}
                {isAllComplete
                  ? "All Sections Complete — Continue to Documents"
                  : `Proceed to Documents (${totalRemainingCount} incomplete)`}{" "}
                <ArrowRight className="size-4" />
              </Button>
            )}
          </div>
        </div>
      ) : (
        /* Tabbed Active Section Mode */
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1.5">
            <h4 className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-2.5">
              <span>{currentSectionKey}</span>
              <Badge tone={isCurrentSectionComplete ? "success" : "default"} className="text-[11px] font-medium">
                {currentAnsweredCount} / {currentQuestions.length} answered
              </Badge>
            </h4>
          </div>


          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentQuestions.map(renderQuestion)}
          </div>

          {/* Section Navigation Wizard Footer */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-t pt-5 mt-6">
            {currentSectionIndex > 0 ? (
              <Button
                variant="outline"
                onClick={async () => {
                  await flushAllDrafts();
                  setActiveSection(sectionKeys[currentSectionIndex - 1]);
                }}
                className="h-9 text-xs gap-1.5 px-3 justify-center sm:justify-start"
              >
                <ChevronLeft className="size-3.5" /> Previous: {sectionKeys[currentSectionIndex - 1]}
              </Button>
            ) : <div />}

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              {!isCurrentSectionComplete && (
                <span className="text-xs text-muted-foreground font-medium text-center sm:text-left">
                  {remainingInCurrent} question(s) left in this module
                </span>
              )}

              {currentSectionIndex < sectionKeys.length - 1 ? (
                <div className="flex flex-wrap items-center gap-2 justify-end">
                  <Button
                    onClick={async () => {
                      await flushAllDrafts();
                      setActiveSection(sectionKeys[currentSectionIndex + 1]);
                    }}
                    className="h-9 text-xs gap-1.5 px-4 font-semibold shadow-sm justify-center sm:justify-start"
                  >
                    Continue to: {sectionKeys[currentSectionIndex + 1]} <ChevronRight className="size-3.5" />
                  </Button>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2 justify-end">
                  {firstIncompleteSection && firstIncompleteSection !== currentSectionKey && (
                    <Button
                      variant="outline"
                      onClick={async () => {
                        await flushAllDrafts();
                        setActiveSection(firstIncompleteSection);
                      }}
                      className="h-9 text-xs gap-1.5 px-3 text-primary border-primary/30 hover:bg-primary/5"
                    >
                      Review Incomplete: {firstIncompleteSection}
                    </Button>
                  )}
                  {onProceedToEligibility && (
                    <Button
                      onClick={handleProceed}
                      disabled={isProceeding}
                      className={`h-9 text-xs gap-1.5 px-4 font-semibold text-white shadow-sm ${
                        isAllComplete
                          ? "bg-emerald-600 hover:bg-emerald-700"
                          : "bg-primary hover:bg-primary/90"
                      }`}
                    >
                      {isProceeding ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : isAllComplete ? (
                        <CheckCircle2 className="size-4" />
                      ) : (
                        <AlertTriangle className="size-3.5 text-amber-300" />
                      )}
                      {isAllComplete
                        ? "All Sections Complete — Continue to Documents"
                        : `Proceed to Documents (${totalRemainingCount} incomplete)`}{" "}
                      <ArrowRight className="size-4" />
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
