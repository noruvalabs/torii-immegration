"use client";

import { useEffect, useState, useMemo } from "react";
import {
  FileText,
  Loader2,
  CheckCircle2,
  Sparkles,
  Copy,
  Check,
  ExternalLink,
  Download,
  AlertCircle,
  Zap,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import {
  answerIntake,
  patchCase,
  downloadOfficialForm,
} from "@/lib/api/cases";
import { useOfficialFormsQuery, useFilingQuery } from "@/lib/queries/cases";
import type { FilingInfo, OfficialForm, PortalPack } from "@/lib/api/cases";
import { toast } from "@/components/ui/sonner";
import type { GeneratedForm } from "./types";

type FormsStepProps = {
  forms: GeneratedForm[];
  loading: boolean;
  onGenerate: () => void;
  intakeAnswers?: Record<string, unknown>;
  caseId?: number;
  reference?: string;
};

type FormFieldItem = { key: string; label: string; value: string };
type FormFieldGroup = { title: string; fields: FormFieldItem[] };

type FieldControlSpec = {
  type: "text" | "date" | "select" | "number";
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  min?: number;
  max?: number;
};

function getFieldControlSpec(key: string): FieldControlSpec {
  const k = key.toLowerCase();

  // Date fields
  if (
    k.includes("date") ||
    k.includes("dob") ||
    k.includes("expiry") ||
    k.includes("expiration") ||
    k.includes("arrival") ||
    k.includes("entry_date") ||
    k.includes("graduation") ||
    k.includes("issue_date")
  ) {
    return { type: "date" };
  }

  // Sex / Gender
  if (k === "sex" || k === "gender") {
    return {
      type: "select",
      options: [
        { label: "Male (男)", value: "male" },
        { label: "Female (女)", value: "female" },
      ],
    };
  }

  // Marital Status
  if (k === "marital_status") {
    return {
      type: "select",
      options: [
        { label: "Single (未婚)", value: "single" },
        { label: "Married (有配偶)", value: "married" },
        { label: "Divorced (死別・離別)", value: "divorced" },
        { label: "Widowed (死別)", value: "widowed" },
      ],
    };
  }

  // Yes / No booleans
  if (
    k.includes("criminal_record") ||
    k.includes("has_family") ||
    k.includes("has_it_qualification") ||
    k.includes("has_criminal") ||
    k.includes("has_sponsor") ||
    k.includes("has_relatives") ||
    k.includes("deportation") ||
    k.includes("offence") ||
    k.includes("conviction") ||
    k.includes("imprisoned") ||
    k.includes("trafficking") ||
    k.includes("prostitution") ||
    k.startsWith("is_") ||
    k.startsWith("has_")
  ) {
    return {
      type: "select",
      options: [
        { label: "No (無)", value: "false" },
        { label: "Yes (有)", value: "true" },
      ],
    };
  }

  // Numbers & Currency
  if (
    k.includes("salary") ||
    k.includes("remuneration") ||
    k.includes("income") ||
    k.includes("capital") ||
    k.includes("sales") ||
    k.includes("amount") ||
    k.includes("employees") ||
    k.includes("years_in_japan") ||
    k.includes("stay_duration_months") ||
    k.includes("family_count")
  ) {
    return {
      type: "number",
      placeholder: k.includes("salary") || k.includes("capital") ? "e.g. 5000000" : "e.g. 1",
      min: 0,
    };
  }

  // Attendance Rate (出席率)
  if (k.includes("attendance_rate")) {
    return {
      type: "number",
      placeholder: "e.g. 95 (%)",
      min: 0,
      max: 100,
    };
  }

  // School Enrollment / Completion Status
  if (k.includes("enrollment_status") || k.includes("school_completed")) {
    return {
      type: "select",
      options: [
        { label: "Enrolled (在籍中・在学中)", value: "enrolled" },
        { label: "Completed / Graduated (卒業・修了)", value: "graduated" },
        { label: "Expected to Graduate (卒業見込み)", value: "expected_to_graduate" },
        { label: "Withdrawn (退学)", value: "withdrawn" },
      ],
    };
  }

  // Desired or Current Period of stay
  if (k.includes("period_of_stay") || k.includes("desired_period")) {
    return {
      type: "select",
      options: [
        { label: "5 Years (5年)", value: "5 years" },
        { label: "3 Years (3年)", value: "3 years" },
        { label: "1 Year (1年)", value: "1 year" },
        { label: "6 Months (6月)", value: "6 months" },
        { label: "3 Months (3月)", value: "3 months" },
      ],
    };
  }

  // Education Level
  if (k.includes("education_level") || k.includes("final_education")) {
    return {
      type: "select",
      options: [
        { label: "Doctorate (博士)", value: "Doctorate" },
        { label: "Master's Degree (修士)", value: "Master's Degree" },
        { label: "Bachelor's Degree (学士)", value: "Bachelor's Degree" },
        { label: "Junior College (短期大学)", value: "Junior College" },
        { label: "Vocational School / Senmonshi (専門学校・専門士)", value: "Vocational School" },
        { label: "High School (高等学校)", value: "High School" },
      ],
    };
  }

  // Status of residence
  if (k.includes("status_of_residence") || k.includes("visa_status")) {
    return {
      type: "select",
      options: [
        { label: "Engineer / Specialist in Humanities / Int'l Services (技術・人文知識・国際業務)", value: "Engineer/Specialist in Humanities/International Services" },
        { label: "Student (留学)", value: "Student" },
        { label: "Dependent (家族滞在)", value: "Dependent" },
        { label: "Spouse of Japanese National (日本人の配偶者等)", value: "Spouse of Japanese National" },
        { label: "Spouse of Permanent Resident (永住者の配偶者等)", value: "Spouse of Permanent Resident" },
        { label: "Highly Skilled Professional (高度専門職)", value: "Highly Skilled Professional" },
        { label: "Business Manager (経営・管理)", value: "Business Manager" },
        { label: "Specified Skilled Worker (特定技能)", value: "Specified Skilled Worker" },
        { label: "Designated Activities (特定活動)", value: "Designated Activities" },
        { label: "Permanent Resident (永住者)", value: "Permanent Resident" },
      ],
    };
  }

  return { type: "text", placeholder: `Enter ${key.replace(/_/g, " ")}...` };
}

const STATUTORY_REQUIRED_FIELD_KEYS = new Set([
  // Core Identity & Nationality
  "full_name",
  "applicant_name",
  "nationality",
  "country_of_citizenship",
  "date_of_birth",
  "birth_date",
  "dob",
  "sex",
  "gender",
  "marital_status",
  "place_of_birth",
  "passport_number",
  "passport_expiry_date",
  "passport_expiry",
  // Status in Japan (Extension / Renewal / Change of Status)
  "current_status_of_residence",
  "current_visa_status",
  "current_residence_status",
  "current_period_of_stay",
  "current_period_of_stay_years",
  "current_status_expiry_date",
  "current_stay_expiry_date",
  "residence_card_expiry",
  "residence_card_number",
  "current_japan_address",
  "registered_address_japan",
  "address_in_japan",
  "telephone_japan",
  "phone_number",
  "contact_phone",
  // Application terms
  "desired_period_of_stay",
  "desired_period",
  "reason_for_extension",
  "reason_for_change",
  "purpose_of_visit",
  "main_purpose",
  // Primary sponsor / school / employer
  "employer_name",
  "company_name",
  "sponsor_name",
  "employer_address",
  "employer_phone",
  "occupation",
  "job_title",
  "monthly_salary",
  "salary",
  "annual_salary",
  "school_name",
  "institution_name",
  "education_level",
  "major_field",
  "field_of_study",
  // Student & School specific statutory fields
  "attendance_rate",
  "school.attendance_rate",
  "school_attendance_rate",
  "school_completed",
  "enrollment_status",
  "school.enrollment_status",
  "school_enrollment_status",
]);

export function isFieldRequired(key: string): boolean {
  const cleanKey = key.split(".").pop()?.toLowerCase() || key.toLowerCase();
  if (STATUTORY_REQUIRED_FIELD_KEYS.has(cleanKey)) return true;
  if (
    cleanKey.includes("test_") ||
    cleanKey.includes("ability_other") ||
    cleanKey.includes("high_school") ||
    cleanKey.includes("study_from") ||
    cleanKey.includes("study_to") ||
    cleanKey.includes("supporter_") ||
    cleanKey.includes("overseas_") ||
    cleanKey.includes("remittance_") ||
    cleanKey.includes("scholarship_") ||
    cleanKey.includes("bank_balance") ||
    cleanKey.includes("carrying_cash") ||
    cleanKey.includes("co_inhabitant") ||
    cleanKey.includes("representative_") ||
    cleanKey.includes("criminal_") ||
    cleanKey.includes("deportation_") ||
    cleanKey.includes("departure_") ||
    cleanKey.includes("room_") ||
    cleanKey.includes("family_in_japan") ||
    cleanKey.includes("relatives_") ||
    cleanKey.includes("agent_") ||
    cleanKey.includes("other_") ||
    cleanKey.includes("note") ||
    cleanKey.includes("sub_") ||
    cleanKey.includes("part_time") ||
    cleanKey.includes("license_")
  ) {
    return false;
  }
  return false;
}

const FIELD_ALIAS_GROUPS: string[][] = [
  ["intended_length_of_stay_days", "stay_duration_days", "length_of_stay_days", "stay_days", "visit.length_of_stay_days", "duration_of_stay", "duration"],
  ["support_type", "financial.support_type", "financial_support_type", "visitor_has_sufficient_funds", "has_sufficient_funds", "trip_payer"],
  ["full_name", "applicant_name", "visitor_full_name", "visitor.full_name", "applicant.full_name", "name", "legal_name", "full_legal_name", "applicant full name", "applicant name (as in passport)"],
  ["nationality", "visitor_nationality", "visitor.nationality", "applicant.nationality", "country_of_citizenship", "citizenship", "primary_citizenship", "country_of_nationality", "nationality_or_region", "nationality / region", "nationality / citizenship", "6.国籍", "国籍", "国籍・地域"],
  ["home_town_city", "home_city", "hometown", "city_in_home_country", "home_town", "home town / city", "home town city"],
  ["current_country", "current_location_country", "current_residence_country", "residence_country", "country_of_residence", "country_of_current_residence", "country of current residence", "country of residence"],
  ["passport_number", "passport_no", "visitor_passport_number", "visitor.passport_number", "applicant.passport_number", "passport_num", "travel_document_number", "passport number"],
  ["date_of_birth", "dob", "birth_date", "applicant_dob", "applicant_date_of_birth", "date of birth", "date of birth (yyyy-mm-dd)"],
  ["place_of_birth", "birth_place", "city_of_birth", "country_of_birth", "place of birth", "place / country of birth"],
  ["passport_expiry_date", "passport_expiry", "passport_expiration_date", "passport_valid_until", "applicant.passport_expiry", "passport expiration date", "passport expiry date"],
  ["purpose_of_visit", "main_purpose", "purpose", "visit.purpose", "purpose_of_stay", "trip_purpose", "purpose of visit to japan", "main purpose of visit"],
  ["relationship", "relationship_to_visitor", "sponsor_relationship", "relationship_to_applicant", "relationship_to_supporter"],
  ["residence_card_number", "guarantor.residence_card_number", "residence_card_no", "zairyu_card_number", "alien_registration_number", "residence.card_number", "residence card number"],
  ["current_status_of_residence", "current_visa_status", "current_residence_status", "status_of_residence", "current residence status"],
  ["current_period_of_stay", "current_period_of_stay_years", "period_of_stay", "current period of stay"],
  ["current_status_expiry_date", "current_stay_expiry_date", "residence_card_expiry", "expiry_date_stay", "residence.card_expiry", "residence expiration date"],
  ["current_japan_address", "registered_address_japan", "address_in_japan", "residential_address_japan", "japan_address", "residence.address", "address in japan", "registered address japan"],
  ["telephone_japan", "phone_number", "contact_phone", "phone_japan", "telephone_number", "telephone number"],
  ["mobile_phone", "mobile_phone_japan", "cell_phone", "cellular / mobile phone"],
  ["employer_name", "company_name", "sponsor_name", "sponsoring_organization", "host_company_name", "employer", "employer / company name"],
  ["corporate_number", "employer_corporate_number", "company_number", "organization_number", "corporate number"],
  ["salary", "monthly_salary", "annual_salary_jpy", "salary_monthly", "income_monthly", "annual_salary", "annual salary / remuneration", "monthly salary / income"],
  ["desired_period_of_stay", "desired_period", "desired_extension_days", "desired_stay_duration", "desired length of extension"],
  ["reason_for_extension", "extension_explanation_details", "reason_for_change", "reason_for_application", "reason for application"],
  ["criminal_record", "criminal_record_any", "has_criminal_record", "criminal_disclosures", "criminal record disclosures", "criminal record / offence history (no/yes)"],
  ["has_family_in_japan", "family_in_japan", "relatives_in_japan", "family in japan"],
  ["occupation", "current_profession", "job_title", "duties", "job title / occupation", "current profession / occupation"],
  ["sex", "gender", "sex / gender"],
  ["marital_status", "marital status"],
  ["school_name", "institution_name", "last_school_attended", "school.name", "name of last school attended", "school name"],
  ["education_level", "final_education", "highest_education", "highest education level", "education level"],
  ["major_field", "field_of_study", "major", "major / field of study"],
  ["graduation_date", "graduation_year_month", "date_of_graduation", "date of graduation"],
  ["attendance_rate", "school.attendance_rate", "school_attendance_rate"],
  ["school_completed", "enrollment_status", "school.enrollment_status", "school_enrollment_status"],
];

function normalizeFieldKey(k: string): string {
  return k
    .toLowerCase()
    .trim()
    .replace(/^[\d\.\s\-_]+/, "")
    .replace(/\(.*?\)/g, "")
    .replace(/[_\s\-\/]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function getCanonicalAliasGroup(key: string): string[] | null {
  const norm = normalizeFieldKey(key);
  const clean = norm.split(".").pop() || norm;
  if (clean === "国籍" || clean === "国籍_地域") {
    return FIELD_ALIAS_GROUPS.find((g) => g[0] === "nationality") || null;
  }
  if (clean === "氏名" || clean === "名前") {
    return FIELD_ALIAS_GROUPS.find((g) => g[0] === "full_name") || null;
  }
  if (clean === "生年月日") {
    return FIELD_ALIAS_GROUPS.find((g) => g[0] === "date_of_birth") || null;
  }
  for (const group of FIELD_ALIAS_GROUPS) {
    for (const item of group) {
      const normItem = normalizeFieldKey(item);
      const cleanItem = normItem.split(".").pop() || normItem;
      if (norm === normItem || clean === cleanItem || norm === cleanItem || clean === normItem) {
        return group;
      }
    }
  }
  return null;
}

function isFieldAlreadyAnswered(key: string, filledAnswers: Record<string, unknown>): boolean {
  const norm = normalizeFieldKey(key);
  const clean = norm.split(".").pop() || norm;
  if (filledAnswers[key] !== undefined && filledAnswers[key] !== null && filledAnswers[key] !== "") return true;
  if (filledAnswers[clean] !== undefined && filledAnswers[clean] !== null && filledAnswers[clean] !== "") return true;

  const group = getCanonicalAliasGroup(key);
  if (group) {
    for (const alias of group) {
      const aliasClean = alias.split(".").pop() || alias;
      if (
        (filledAnswers[alias] !== undefined && filledAnswers[alias] !== null && filledAnswers[alias] !== "") ||
        (filledAnswers[aliasClean] !== undefined && filledAnswers[aliasClean] !== null && filledAnswers[aliasClean] !== "")
      ) {
        return true;
      }
    }
  }
  return false;
}

function deduplicateMissingFields(fields: string[], filledAnswers: Record<string, unknown>): string[] {
  const seenCanonical = new Set<string>();
  const result: string[] = [];

  for (const field of fields) {
    const cleanKey = field.split(".").pop() || field;
    if (isFieldAlreadyAnswered(field, filledAnswers)) {
      continue;
    }

    const group = getCanonicalAliasGroup(field);
    const canonicalKey = group ? group[0] : cleanKey.toLowerCase();

    if (!seenCanonical.has(canonicalKey)) {
      seenCanonical.add(canonicalKey);
      result.push(field);
    }
  }

  return result;
}

function categorizeFields(filledFields: Record<string, unknown>): FormFieldGroup[] {
  const standardGroups: Array<{
    title: string;
    keys: Array<{ key: string; label: string; aliases?: string[] }>;
  }> = [
    {
      title: "Applicant & Identity",
      keys: [
        { key: "full_name", label: "Full Name", aliases: ["applicant_name", "visitor_full_name", "applicant.full_name"] },
        { key: "nationality", label: "Nationality / Region", aliases: ["country_of_citizenship", "visitor_nationality", "citizenship", "country_of_nationality", "applicant.nationality"] },
        { key: "date_of_birth", label: "Date of Birth", aliases: ["dob", "birth_date"] },
        { key: "sex", label: "Gender", aliases: ["gender"] },
        { key: "marital_status", label: "Marital Status" },
        { key: "place_of_birth", label: "Place of Birth", aliases: ["birth_place", "city_of_birth"] },
        { key: "home_town_city", label: "Home Town / City", aliases: ["home_city", "hometown", "city_in_home_country"] },
      ],
    },
    {
      title: "Passport & Residence Status",
      keys: [
        { key: "passport_number", label: "Passport Number", aliases: ["passport_no", "applicant.passport_number"] },
        { key: "passport_expiry_date", label: "Passport Expiration Date", aliases: ["passport_expiry", "applicant.passport_expiry"] },
        { key: "current_status_of_residence", label: "Current Residence Status", aliases: ["current_visa_status", "current_residence_status", "status_of_residence"] },
        { key: "current_period_of_stay", label: "Current Period of Stay", aliases: ["current_period_of_stay_years", "period_of_stay"] },
        { key: "current_status_expiry_date", label: "Residence Expiration Date", aliases: ["current_stay_expiry_date", "residence_card_expiry", "expiry_date_stay"] },
        { key: "residence_card_number", label: "Residence Card Number", aliases: ["residence_card_no", "zairyu_card_number", "residence.card_number"] },
      ],
    },
    {
      title: "Address & Contact in Japan",
      keys: [
        { key: "current_japan_address", label: "Address in Japan", aliases: ["registered_address_japan", "address_in_japan", "residential_address_japan", "residence.address"] },
        { key: "telephone_japan", label: "Telephone Number", aliases: ["phone_number", "contact_phone", "phone_japan", "telephone_number"] },
        { key: "mobile_phone", label: "Cellular / Mobile Phone", aliases: ["mobile_phone_japan", "cell_phone"] },
      ],
    },
    {
      title: "Application Details",
      keys: [
        { key: "desired_period_of_stay", label: "Desired Length of Extension", aliases: ["desired_period", "desired_extension_days"] },
        { key: "reason_for_extension", label: "Reason for Application", aliases: ["extension_explanation_details", "reason_for_change"] },
        { key: "criminal_record", label: "Criminal Record Disclosures", aliases: ["criminal_record_any", "criminal_disclosures"] },
        { key: "has_family_in_japan", label: "Family in Japan", aliases: ["family_in_japan", "relatives_in_japan"] },
      ],
    },
    {
      title: "Employment & Sponsor (Organization Part)",
      keys: [
        { key: "employer_name", label: "Employer / Company Name", aliases: ["sponsor_name", "company_name"] },
        { key: "employer_corporate_number", label: "Corporate Number", aliases: ["corporate_number"] },
        { key: "employer_category", label: "Tax / Employer Category", aliases: ["company_category"] },
        { key: "occupation", label: "Job Title / Occupation", aliases: ["job_title", "duties"] },
        { key: "annual_salary", label: "Annual Salary / Remuneration", aliases: ["salary", "annual_income_jpy", "current_annual_income"] },
        { key: "employer_address", label: "Company Address in Japan", aliases: ["place_of_employment_address"] },
        { key: "employer_phone", label: "Company Phone Number", aliases: ["place_of_employment_tel"] },
      ],
    },
    {
      title: "Education & Qualifications",
      keys: [
        { key: "education_level", label: "Highest Education Level", aliases: ["final_education", "highest_education"] },
        { key: "school_name", label: "Name of Last School Attended", aliases: ["institution_name", "school.name"] },
        { key: "major_field", label: "Major / Field of Study", aliases: ["field_of_study", "major"] },
        { key: "graduation_date", label: "Date of Graduation", aliases: ["graduation_year_month"] },
      ],
    },
  ];

  const result: FormFieldGroup[] = [];
  const handledKeys = new Set<string>();
  const handledLabels = new Set<string>();

  for (const group of standardGroups) {
    const fields: FormFieldItem[] = [];
    for (const item of group.keys) {
      let val = filledFields[item.key];
      if (val === undefined || val === null || val === "") {
        for (const alias of item.aliases || []) {
          if (filledFields[alias] !== undefined && filledFields[alias] !== null && filledFields[alias] !== "") {
            val = filledFields[alias];
            handledKeys.add(alias);
            break;
          }
        }
      }
      if (val === undefined || val === null || val === "") {
        const agroup = getCanonicalAliasGroup(item.key);
        if (agroup) {
          for (const alias of agroup) {
            if (filledFields[alias] !== undefined && filledFields[alias] !== null && filledFields[alias] !== "") {
              val = filledFields[alias];
              handledKeys.add(alias);
              break;
            }
          }
        }
      }

      if (val !== undefined && val !== null && val !== "") {
        handledKeys.add(item.key);
        handledKeys.add(item.key.toLowerCase());
        handledLabels.add(normalizeFieldKey(item.label));

        for (const a of item.aliases || []) {
          handledKeys.add(a);
          handledKeys.add(a.toLowerCase());
          handledKeys.add(normalizeFieldKey(a));
        }

        const agroup = getCanonicalAliasGroup(item.key);
        if (agroup) {
          for (const a of agroup) {
            handledKeys.add(a);
            handledKeys.add(a.toLowerCase());
            handledKeys.add(normalizeFieldKey(a));
            handledLabels.add(normalizeFieldKey(a));
          }
        }

        fields.push({
          key: item.key,
          label: item.label,
          value: String(val),
        });
      }
    }
    if (fields.length > 0) {
      result.push({ title: group.title, fields });
    }
  }

  const otherFields: FormFieldItem[] = [];
  const seenOtherCanonical = new Set<string>();

  for (const [k, v] of Object.entries(filledFields)) {
    if (v === null || v === "" || v === undefined) continue;
    if (k.startsWith("_") || k.includes("is_") || k.includes("_flag") || typeof v === "boolean") continue;

    const normK = normalizeFieldKey(k);
    if (handledKeys.has(k) || handledKeys.has(k.toLowerCase()) || handledKeys.has(normK)) continue;

    const group = getCanonicalAliasGroup(k);
    if (group) {
      const alreadyHandledInStandard = group.some(
        (alias) =>
          handledKeys.has(alias) ||
          handledKeys.has(alias.toLowerCase()) ||
          handledKeys.has(normalizeFieldKey(alias))
      );
      if (alreadyHandledInStandard) continue;

      const canonical = group[0];
      if (seenOtherCanonical.has(canonical)) continue;
      seenOtherCanonical.add(canonical);
    }

    const cleanLabel = k
      .replace(/^[\d\.\s\-_]+/, "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
      .trim();
    const normLabel = normalizeFieldKey(cleanLabel);
    if (handledLabels.has(normLabel)) continue;

    handledLabels.add(normLabel);
    handledKeys.add(k);
    handledKeys.add(k.toLowerCase());

    otherFields.push({
      key: k,
      label: cleanLabel,
      value: String(v),
    });
  }

  if (otherFields.length > 0) {
    result.push({ title: "Other Application Fields", fields: otherFields });
  }

  return result;
}

export function FormsStep({
  forms,
  loading,
  onGenerate,
  intakeAnswers,
  caseId,
  reference,
}: FormsStepProps) {
  const { token } = useAuth();
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null);
  const [missingFieldInputs, setMissingFieldInputs] = useState<Record<string, string>>({});
  const [savingMissingField, setSavingMissingField] = useState<string | null>(null);
  const [justSavedField, setJustSavedField] = useState<string | null>(null);
  const { data: officialFormsData } = useOfficialFormsQuery(token, caseId ?? 0, Boolean(token && caseId));
  const { data: filingData } = useFilingQuery(token, caseId ?? 0, Boolean(token && caseId));

  const officialForms = useMemo(
    () => officialFormsData?.forms ?? [],
    [officialFormsData?.forms],
  );
  const filing = filingData ?? null;
  const [expandedFormKeys, setExpandedFormKeys] = useState<Record<string, boolean>>({});
  const [fieldSearchQueries, setFieldSearchQueries] = useState<Record<string, string>>({});
  const [missingFieldFilter, setMissingFieldFilter] = useState<Record<string, "all" | "required" | "optional">>({});
  const [showOptionalFields, setShowOptionalFields] = useState<Record<string, boolean>>({});

  const portalPack: PortalPack | undefined =
    filing?.filing_mode === "online_portal" ? filing.portal_pack : undefined;

  function saveBlob(bytes: Uint8Array<ArrayBuffer>, filename: string) {
    const blob = new Blob([bytes], { type: "application/pdf" });
    if (blob.size === 0) throw new Error("Generated PDF file is empty (0 bytes).");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      link.remove();
      URL.revokeObjectURL(url);
    }, 10000);
  }

  function decodeBase64(data: string): Uint8Array<ArrayBuffer> {
    const binary = atob(data);
    const bytes = new Uint8Array(new ArrayBuffer(binary.length));
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  async function handleDownloadOfficialForm(formCode: string) {
    const activeToken =
      token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!caseId || !activeToken) return;
    setDownloadingPdf(formCode);
    try {
      const data = await downloadOfficialForm(activeToken, caseId, formCode);
      if (!data?.data_base64) throw new Error("Invalid server response: missing PDF data.");
      saveBlob(decodeBase64(data.data_base64), data.filename);
      toast.success("Official PDF form downloaded.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed. Please try again.");
    } finally {
      setDownloadingPdf(null);
    }
  }

  async function handleDownloadPdf(formCode: string) {
    const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("torii_token") : null);
    if (!caseId || !activeToken) return;
    setDownloadingPdf(formCode);
    try {
      const res = await fetch(`/backend/v1/cases/${caseId}/export/application-form?format=base64`, {
        headers: {
          Authorization: `Bearer ${activeToken}`,
          Accept: "application/json",
        },
      });
      if (!res.ok) {
        const errDetail = await res.text();
        toast.error(`Failed to download PDF form: ${errDetail || res.statusText}`);
        return;
      }
      const data = await res.json();
      if (!data?.data_base64) {
        throw new Error("Invalid server response: missing PDF data.");
      }
      saveBlob(decodeBase64(data.data_base64), data.filename || `${reference || `Case-${caseId}`}_Application_Form.pdf`);
      toast.success("PDF downloaded successfully!");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "PDF download failed. Please try again.");
    } finally {
      setDownloadingPdf(null);
    }
  }

  function handleCopy(label: string, value: string) {
    void navigator.clipboard.writeText(value);
    setCopiedKey(label);
    toast.success(`Copied ${label}`, { duration: 1500 });
    setTimeout(() => setCopiedKey(null), 2000);
  }

  async function handleSaveMissingField(fieldKey: string, explicitValue?: unknown) {
    if (!token || !caseId) return;
    const cleanKey = fieldKey.split(".").pop() || fieldKey;
    let val: unknown = explicitValue !== undefined ? explicitValue : (missingFieldInputs[cleanKey] ?? missingFieldInputs[fieldKey]);
    if (val === undefined || val === null || val === "") {
      toast.error(`Please enter a value for ${cleanKey.replace(/_/g, " ")}`);
      return;
    }

    // Coerce booleans and numbers
    const spec = getFieldControlSpec(cleanKey);
    if (val === "true" || val === "yes") {
      val = true;
    } else if (val === "false" || val === "no") {
      val = false;
    } else if (
      spec.type === "number" ||
      (typeof val === "string" &&
        /^\d+$/.test(val.replace(/,/g, "").trim()) &&
        !cleanKey.includes("phone") &&
        !cleanKey.includes("tel") &&
        !cleanKey.includes("card") &&
        !cleanKey.includes("passport"))
    ) {
      val = parseInt(String(val).replace(/,/g, "").trim(), 10);
    }

    setSavingMissingField(cleanKey);
    try {
      // Gather all canonical aliases for synchronization
      const group = getCanonicalAliasGroup(cleanKey) || getCanonicalAliasGroup(fieldKey);
      const patchUpdates: Record<string, unknown> = { [cleanKey]: val };
      if (group) {
        for (const alias of group) {
          const aClean = alias.split(".").pop() || alias;
          patchUpdates[aClean] = val;
        }
      }

      // Sync local missingFieldInputs for all aliases
      const stringUpdates: Record<string, string> = {};
      for (const [k, v] of Object.entries(patchUpdates)) {
        stringUpdates[k] = String(v ?? "");
      }
      setMissingFieldInputs((prev) => ({ ...prev, ...stringUpdates }));

      try {
        await answerIntake(token, caseId, cleanKey, val);
      } catch {
        // Resilient fallback: patch case answers directly
        await patchCase(token, caseId, {
          intake_answers: { ...(intakeAnswers || {}), ...patchUpdates },
        });
      }

      // If group has aliases, also ensure patchCase synchronizes them
      if (group && group.length > 1) {
        try {
          await patchCase(token, caseId, {
            intake_answers: { ...(intakeAnswers || {}), ...patchUpdates },
          });
        } catch {
          // ignore
        }
      }

      setJustSavedField(cleanKey);
      setTimeout(() => setJustSavedField(null), 2500);

      toast.success(`Saved ${cleanKey.replace(/_/g, " ")}!`, { duration: 1500 });
      onGenerate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save field");
    } finally {
      setSavingMissingField(null);
    }
  }

  const unifiedForms = useMemo(() => {
    if (officialForms.length > 0) {
      const allFilledFields: Record<string, unknown> = { ...(intakeAnswers || {}) };
      const allMissingFields = new Set<string>();

      for (const gform of forms) {
        if (gform.filled_fields) {
          Object.assign(allFilledFields, gform.filled_fields);
        }
        for (const m of gform.missing_required_fields || []) {
          allMissingFields.add(m);
        }
      }

      return officialForms.map((oform) => {
        const combinedMissing = new Set<string>([
          ...(oform.missing_answer_keys || []),
          ...Array.from(allMissingFields),
        ]);
        const rawMissing = Array.from(combinedMissing);

        // Deduplicate and filter out fields whose alias group is already answered
        const missing = deduplicateMissingFields(rawMissing, allFilledFields);

        const requiredKeys = new Set<string>([
          ...(oform.required_missing_keys || []),
          ...Array.from(allMissingFields).filter((k) => isFieldRequired(k)),
        ]);
        const requiredMissing = missing.filter((k) => requiredKeys.has(k) || isFieldRequired(k));
        const optionalMissing = missing.filter((k) => !requiredMissing.includes(k));
        const total = oform.total_items || Object.keys(allFilledFields).length || 45;

        return {
          key: oform.code,
          code: oform.code,
          titleJa: oform.title_ja,
          titleEn: oform.title_en || oform.code,
          pages: oform.pages,
          series: oform.series,
          authority: oform.authority || "Immigration Services Agency of Japan",
          sourceUrl: oform.source_page_url || oform.citation?.url,
          missingFields: missing,
          requiredMissing,
          optionalMissing,
          totalItems: total,
          filledFields: allFilledFields,
          isOfficialDownload: true,
          note: oform.note,
        };
      });
    }

    const list: Array<{
      key: string;
      code: string;
      titleJa?: string;
      titleEn: string;
      pages?: number;
      series?: string;
      authority: string;
      sourceUrl?: string;
      missingFields: string[];
      requiredMissing: string[];
      optionalMissing: string[];
      totalItems: number;
      filledFields: Record<string, unknown>;
      isOfficialDownload: boolean;
      note?: string | null;
    }> = [];

    for (const gform of forms) {
      const citation = (gform.citation ?? {}) as {
        title?: string;
        url?: string;
        authority?: string;
      };
      const filled = gform.filled_fields || intakeAnswers || {};
      const rawMissing = gform.missing_required_fields || [];
      const missing = deduplicateMissingFields(rawMissing, filled);
      const requiredMissing = missing.filter((k) => isFieldRequired(k));
      const optionalMissing = missing.filter((k) => !isFieldRequired(k));
      const total = Object.keys(filled).length + missing.length;

      list.push({
        key: gform.form_code,
        code: gform.form_code,
        titleEn: gform.official_title || citation.title || gform.form_code,
        authority: citation.authority || "Official Authority",
        sourceUrl: citation.url,
        missingFields: missing,
        requiredMissing,
        optionalMissing,
        totalItems: total,
        filledFields: filled,
        isOfficialDownload: false,
      });
    }

    return list;
  }, [officialForms, forms, intakeAnswers]);

  const hasNoForms = unifiedForms.length === 0 && !portalPack;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
        <div>
          <h3 className="text-base font-semibold text-foreground">Official Government Application Forms</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Auto-filled with verified answers and formatted for official ministry submission.
          </p>
        </div>
        {!hasNoForms && (
          <Button
            variant="outline"
            onClick={onGenerate}
            disabled={loading}
            className="text-xs h-8 gap-1.5 self-start sm:self-auto"
          >
            {loading ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5 text-primary" />}
            Refresh &amp; Re-fill
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground leading-relaxed flex items-start gap-2.5">
        <Sparkles className="size-4 text-primary shrink-0 mt-0.5" />
        <p>
          Your intake responses have been validated across eligibility criteria and document requirements.
          Below, the <strong>statutory items required by immigration</strong> are automatically mapped and filled onto your official application sheet.
        </p>
      </div>

      {portalPack && (
        <div className="rounded-[var(--radius)] border bg-card p-5 space-y-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                Online Government Portal Filing
              </span>
              <h4 className="text-sm font-semibold text-foreground mt-0.5">{portalPack.scope_label}</h4>
            </div>
          </div>

          <div className="space-y-3">
            {portalPack.sections.map((section) => (
              <div key={section.key} className="space-y-1.5">
                <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">{section.title}</p>
                <div className="rounded-md border divide-y text-xs">
                  {section.fields.map((field) => (
                    <div key={field.field} className="flex items-center justify-between px-3 py-2">
                      <span className="text-muted-foreground w-1/2 truncate">{field.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{field.value || "—"}</span>
                        {field.value && (
                          <button
                            onClick={() => handleCopy(field.label, field.value!)}
                            className="text-muted-foreground hover:text-foreground p-1"
                            title="Copy"
                          >
                            {copiedKey === field.label ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3" />}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasNoForms ? (
        <div className="rounded-[var(--radius)] border border-dashed p-8 text-center bg-muted/20 space-y-3">
          <FileText className="mx-auto size-10 text-muted-foreground/40" />
          <p className="text-sm font-medium">No official forms generated yet</p>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            Click &quot;Auto-fill official forms&quot; to automatically map all your intake answers and documents into official embassy forms.
          </p>
          <Button onClick={onGenerate} disabled={loading} className="mt-2 text-xs font-semibold">
            {loading ? <Loader2 className="mr-2 size-4 animate-spin" /> : <Sparkles className="mr-2 size-4" />}
            Auto-fill forms now
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          {unifiedForms.map((form) => {
            const isDownloading = downloadingPdf === form.code;
            const isExpanded = Boolean(expandedFormKeys[form.key]);
            const search = (fieldSearchQueries[form.key] || "").toLowerCase().trim();
            const isComplete = form.missingFields.length === 0;

            const categorized = categorizeFields(form.filledFields);
            const totalMappedCount = categorized.reduce((sum, g) => sum + g.fields.length, 0);

            return (
              <div
                key={form.key}
                className="rounded-[var(--radius)] border bg-card p-5 space-y-4 shadow-xs transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                  <div className="space-y-1.5 min-w-0">
                    {form.titleJa && (
                      <h4 className="text-base font-bold text-foreground tracking-tight leading-snug">
                        {form.titleJa}
                      </h4>
                    )}
                    <p className={`text-xs ${form.titleJa ? "text-muted-foreground" : "text-sm font-semibold text-foreground"}`}>
                      {form.titleEn}
                    </p>

                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {form.pages && (
                        <Badge tone="muted" className="text-[10px] font-normal">
                          {form.pages} Pages
                        </Badge>
                      )}
                      <Badge
                        tone={isComplete ? "success" : form.requiredMissing.length === 0 ? "success" : "warning"}
                        className="text-[10px] font-medium"
                      >
                        {isComplete ? (
                          <>
                            <CheckCircle2 className="mr-1 size-3 text-emerald-500" /> 100% Ready
                          </>
                        ) : form.requiredMissing.length === 0 ? (
                          <>
                            <CheckCircle2 className="mr-1 size-3 text-emerald-500" /> All Required Complete ({form.optionalMissing.length} Optional)
                          </>
                        ) : (
                          <>
                            <AlertCircle className="mr-1 size-3 text-amber-500" /> {form.requiredMissing.length} Required Missing ({form.optionalMissing.length} Optional)
                          </>
                        )}
                      </Badge>
                      <span className="text-[11px] text-muted-foreground font-mono pl-1">
                        {form.authority}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <Button
                      onClick={() =>
                        form.isOfficialDownload
                          ? handleDownloadOfficialForm(form.code)
                          : handleDownloadPdf(form.code)
                      }
                      disabled={isDownloading}
                      className="h-8 text-xs font-semibold gap-1.5 shadow-sm"
                    >
                      {isDownloading ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Download className="size-3.5" />
                      )}
                      Download Filled PDF
                    </Button>
                  </div>
                </div>

                {form.note && (
                  <p className="text-xs text-muted-foreground bg-muted/30 p-2.5 rounded border border-border/50">
                    {form.note}
                  </p>
                )}

                {form.requiredMissing.length === 0 && (
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3.5 text-xs text-emerald-900 dark:text-emerald-200">
                    <div className="flex items-start sm:items-center gap-2.5">
                      <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400 mt-0.5 sm:mt-0" />
                      <div>
                        <p className="font-semibold text-foreground">All required statutory questions completed</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          Your intake responses are validated and mapped onto your official application sheet. Your form is ready to download.
                        </p>
                      </div>
                    </div>
                    {form.optionalMissing.length > 0 && (
                      <button
                        type="button"
                        onClick={() =>
                          setShowOptionalFields((prev) => ({
                            ...prev,
                            [form.key]: !prev[form.key],
                          }))
                        }
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer underline-offset-4 hover:underline shrink-0"
                      >
                        <span>
                          {showOptionalFields[form.key]
                            ? "Hide optional disclosures"
                            : `Optional disclosures (${form.optionalMissing.length})`}
                        </span>
                        {showOptionalFields[form.key] ? (
                          <ChevronUp className="size-3.5" />
                        ) : (
                          <ChevronDown className="size-3.5" />
                        )}
                      </button>
                    )}
                  </div>
                )}

                {form.missingFields.length > 0 &&
                  (form.requiredMissing.length > 0 || showOptionalFields[form.key]) &&
                  (() => {
                    const isOptionalOnly = form.requiredMissing.length === 0;
                    const filter =
                      missingFieldFilter[form.key] ?? (isOptionalOnly ? "optional" : "required");
                    const displayedFields = form.missingFields.filter((f) => {
                      const isReq = form.requiredMissing.includes(f) || isFieldRequired(f);
                      if (filter === "required") return isReq;
                      if (filter === "optional") return !isReq;
                      return true;
                    });

                    return (
                      <div
                        className={`rounded-lg border p-4 space-y-3 text-xs ${
                          isOptionalOnly
                            ? "border-border/70 bg-muted/20"
                            : "border-amber-500/30 bg-amber-500/5"
                        }`}
                      >
                        <div
                          className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 border-b pb-2.5 ${
                            isOptionalOnly ? "border-border/50" : "border-amber-500/20"
                          }`}
                        >
                          <div className="flex items-center gap-2 font-semibold">
                            {isOptionalOnly ? (
                              <FileText className="size-4 shrink-0 text-muted-foreground" />
                            ) : (
                              <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />
                            )}
                            <span
                              className={
                                isOptionalOnly
                                  ? "text-foreground"
                                  : "text-amber-900 dark:text-amber-200"
                              }
                            >
                              {form.requiredMissing.length > 0 ? (
                                <>
                                  Official Form Fields ({form.requiredMissing.length} Required ·{" "}
                                  {form.optionalMissing.length} Optional):
                                </>
                              ) : (
                                <>
                                  Optional Form Disclosures ({form.optionalMissing.length} items — leave
                                  blank if not applicable):
                                </>
                              )}
                            </span>
                          </div>

                          {/* Filter Tabs */}
                          <div className="flex items-center gap-1 bg-background/80 p-0.5 rounded-md border text-[11px] self-start sm:self-auto">
                            <button
                              type="button"
                              onClick={() =>
                                setMissingFieldFilter((prev) => ({ ...prev, [form.key]: "all" }))
                              }
                              className={`px-2 py-0.5 rounded font-medium transition-colors cursor-pointer ${
                                filter === "all"
                                  ? "bg-primary text-primary-foreground shadow-xs"
                                  : "text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              All ({form.missingFields.length})
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setMissingFieldFilter((prev) => ({
                                  ...prev,
                                  [form.key]: "required",
                                }))
                              }
                              className={`px-2 py-0.5 rounded font-medium transition-colors cursor-pointer ${
                                filter === "required"
                                  ? "bg-amber-600 text-white shadow-xs"
                                  : "text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              Required ({form.requiredMissing.length})
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                setMissingFieldFilter((prev) => ({
                                  ...prev,
                                  [form.key]: "optional",
                                }))
                              }
                              className={`px-2 py-0.5 rounded font-medium transition-colors cursor-pointer ${
                                filter === "optional"
                                  ? "bg-slate-600 text-white shadow-xs"
                                  : "text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              Optional ({form.optionalMissing.length})
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                          <span>
                            {filter === "required"
                              ? "Mandatory statutory fields needed to legally issue this official application:"
                              : filter === "optional"
                              ? "Optional background disclosures — only complete if applicable to your situation (e.g. Japanese high school, cash carried, legal guardian in Japan). Most applicants leave these blank:"
                              : "Fields required by immigration are marked Required; secondary questions are marked Optional:"}
                          </span>
                          <span className="hidden sm:inline text-[10px] text-muted-foreground/80 italic">
                            Values auto-save on paste, select, &amp; blur
                          </span>
                        </div>

                      {displayedFields.length === 0 ? (
                        <div className="py-6 text-center text-muted-foreground text-xs italic">
                          No {filter} fields missing.
                        </div>
                      ) : (
                        <div className="grid gap-2.5 sm:grid-cols-2 md:grid-cols-3 max-h-80 overflow-y-auto p-1.5 pt-2">
                          {displayedFields.map((field) => {
                            const cleanKey = field.split(".").pop() || field;
                            const label = cleanKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
                            const spec = getFieldControlSpec(cleanKey);
                            const val = missingFieldInputs[cleanKey] ?? "";
                            const isSaving = savingMissingField === cleanKey;
                            const isJustSaved = justSavedField === cleanKey;
                            const isReq = form.requiredMissing.includes(field) || isFieldRequired(cleanKey);

                            return (
                              <div
                                key={field}
                                className={`flex flex-col justify-between rounded-lg border bg-card p-3 shadow-2xs space-y-2 transition-all ${
                                  isReq ? "border-amber-500/40 bg-amber-500/[0.02]" : "border-border/60"
                                }`}
                              >
                                <div className="flex items-center justify-between gap-1.5">
                                  <label className="text-[11px] font-semibold text-foreground leading-tight block truncate" title={label}>
                                    {label}
                                  </label>
                                  {isReq ? (
                                    <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1">
                                      <span className="size-1 rounded-full bg-amber-500" /> Required
                                    </span>
                                  ) : (
                                    <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-medium bg-muted text-muted-foreground uppercase tracking-wider">
                                      Optional
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-1.5">
                                  {spec.type === "date" ? (
                                    <input
                                      type="date"
                                      value={val}
                                      onChange={(e) => {
                                        const nextVal = e.target.value;
                                        setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: nextVal }));
                                        if (nextVal) {
                                          void handleSaveMissingField(cleanKey, nextVal);
                                        }
                                      }}
                                      onBlur={() => {
                                        if (val) void handleSaveMissingField(cleanKey, val);
                                      }}
                                      className="h-8 w-full rounded border bg-background px-2 text-xs outline-none focus:ring-1 focus:ring-primary text-foreground"
                                    />
                                  ) : spec.type === "select" ? (
                                    <select
                                      value={val}
                                      onChange={(e) => {
                                        const nextVal = e.target.value;
                                        setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: nextVal }));
                                        if (nextVal) {
                                          void handleSaveMissingField(cleanKey, nextVal);
                                        }
                                      }}
                                      className="h-8 w-full rounded border bg-background px-2 text-xs outline-none focus:ring-1 focus:ring-primary text-foreground cursor-pointer"
                                    >
                                      <option value="">Select...</option>
                                      {spec.options?.map((opt) => (
                                        <option key={opt.value} value={opt.value}>
                                          {opt.label}
                                        </option>
                                      ))}
                                    </select>
                                  ) : spec.type === "number" ? (
                                    <input
                                      type="number"
                                      min={spec.min ?? 0}
                                      max={spec.max}
                                      placeholder={spec.placeholder || "Enter number..."}
                                      value={val}
                                      onChange={(e) =>
                                        setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: e.target.value }))
                                      }
                                      onPaste={(e) => {
                                        const text = e.clipboardData.getData("text").trim();
                                        if (text) {
                                          setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: text }));
                                          void handleSaveMissingField(cleanKey, text);
                                        }
                                      }}
                                      onBlur={() => {
                                        if (val) void handleSaveMissingField(cleanKey, val);
                                      }}
                                      onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                          e.preventDefault();
                                          void handleSaveMissingField(cleanKey);
                                          (e.target as HTMLElement).blur();
                                        }
                                      }}
                                      className="h-8 w-full rounded border bg-background px-2 text-xs outline-none focus:ring-1 focus:ring-primary text-foreground"
                                    />
                                  ) : (
                                    <input
                                      type="text"
                                      placeholder={spec.placeholder || `Enter ${label}...`}
                                      value={val}
                                      onChange={(e) =>
                                        setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: e.target.value }))
                                      }
                                      onPaste={(e) => {
                                        const text = e.clipboardData.getData("text").trim();
                                        if (text) {
                                          setMissingFieldInputs((prev) => ({ ...prev, [cleanKey]: text }));
                                          void handleSaveMissingField(cleanKey, text);
                                        }
                                      }}
                                      onBlur={() => {
                                        if (val) void handleSaveMissingField(cleanKey, val);
                                      }}
                                      onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                          e.preventDefault();
                                          void handleSaveMissingField(cleanKey);
                                          (e.target as HTMLElement).blur();
                                        }
                                      }}
                                      className="h-8 w-full rounded border bg-background px-2 text-xs outline-none focus:ring-1 focus:ring-primary text-foreground"
                                    />
                                  )}

                                  <Button
                                    disabled={!val || isSaving}
                                    onClick={() => handleSaveMissingField(cleanKey)}
                                    size="sm"
                                    className={`h-8 px-2.5 text-[10px] font-semibold shrink-0 transition-all ${
                                      isJustSaved
                                        ? "bg-emerald-600 hover:bg-emerald-600 text-white border-emerald-600"
                                        : ""
                                    }`}
                                    title={isJustSaved ? "Saved" : "Save field value (auto-saves on paste/blur)"}
                                  >
                                    {isSaving ? (
                                      <Loader2 className="size-3 animate-spin" />
                                    ) : isJustSaved ? (
                                      <>
                                        <Check className="mr-0.5 size-2.5" /> Saved
                                      </>
                                    ) : (
                                      <>
                                        <Zap className="mr-0.5 size-2.5 text-amber-300" /> Save
                                      </>
                                    )}
                                  </Button>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {totalMappedCount > 0 && (
                  <div className="border-t pt-3">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedFormKeys((prev) => ({
                          ...prev,
                          [form.key]: !prev[form.key],
                        }))
                      }
                      className="flex items-center justify-between w-full text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors py-1"
                    >
                      <span className="flex items-center gap-2">
                        <FileText className="size-3.5 text-primary" />
                        Preview Mapped Form Data ({totalMappedCount} fields)
                      </span>
                      <span className="flex items-center gap-1 text-[11px] font-medium text-primary">
                        {isExpanded ? "Hide data" : "Show data"}
                        {isExpanded ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="mt-3 space-y-4 animate-in fade-in duration-200">
                        <div className="relative">
                          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                          <input
                            type="text"
                            placeholder="Search mapped form fields (e.g. name, passport, salary, employer)..."
                            value={fieldSearchQueries[form.key] || ""}
                            onChange={(e) =>
                              setFieldSearchQueries((prev) => ({
                                ...prev,
                                [form.key]: e.target.value,
                              }))
                            }
                            className="h-8 w-full rounded-md border bg-background pl-8 pr-3 text-xs outline-none focus-visible:ring-1"
                          />
                        </div>

                        <div className="space-y-3.5 max-h-96 overflow-y-auto pr-1">
                          {categorized.map((group) => {
                            const groupFields = group.fields.filter(
                              (f) =>
                                !search ||
                                f.label.toLowerCase().includes(search) ||
                                f.value.toLowerCase().includes(search) ||
                                group.title.toLowerCase().includes(search)
                            );

                            if (groupFields.length === 0) return null;

                            return (
                              <div key={group.title} className="space-y-1.5">
                                <p className="text-[11px] font-bold text-foreground/80 uppercase tracking-wider">
                                  {group.title}
                                </p>
                                <div className="grid gap-1.5 sm:grid-cols-2 md:grid-cols-3">
                                  {groupFields.map((field) => {
                                    const isCopied = copiedKey === field.label;
                                    return (
                                      <div
                                        key={field.key}
                                        className="flex items-center justify-between rounded-md border bg-muted/20 px-2.5 py-1.5 text-xs hover:bg-accent/40 transition-colors"
                                      >
                                        <div className="min-w-0 flex-1 pr-1.5">
                                          <p className="text-[10px] text-muted-foreground truncate">
                                            {field.label}
                                          </p>
                                          <p className="font-semibold text-foreground truncate text-[11px] mt-0.5">
                                            {field.value || "—"}
                                          </p>
                                        </div>
                                        {field.value && (
                                          <button
                                            onClick={() => handleCopy(field.label, field.value)}
                                            title={`Copy ${field.label}`}
                                            className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-background transition-colors shrink-0"
                                          >
                                            {isCopied ? (
                                              <Check className="size-3 text-emerald-500" />
                                            ) : (
                                              <Copy className="size-3" />
                                            )}
                                          </button>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
