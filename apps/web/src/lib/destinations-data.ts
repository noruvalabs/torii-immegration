export type DestinationVisa = {
  id: string;
  name: string;
  duration: string;
  entries: string;
  validity: string;
  processingTime: string;
  governmentFee: string;
  toriiFee: string;
  totalDisplay: string;
  requiredDocuments: string[];
  description: string;
};

export type DestinationInfo = {
  slug: string;
  code: string;
  name: string;
  flag: string;
  heroImage: string;
  bannerTag: string;
  tagline: string;
  shortDescription: string;
  overview: string;
  filingModeLabel: string;
  processingDays: string;
  visas: DestinationVisa[];
  requiredSummary: string[];
  faqs: { question: string; answer: string }[];
};

export const DESTINATIONS: Record<string, DestinationInfo> = {
  japan: {
    slug: "japan",
    code: "JP",
    name: "Japan",
    flag: "🇯🇵",
    heroImage: "/destinations/japan.jpg",
    bannerTag: "Guaranteed MOFA Dossier",
    tagline: "Experience the Land of the Rising Sun",
    shortDescription: "Short-stay tourist and family visit visa preparation for Tokyo, Kyoto, and beyond.",
    overview:
      "Planning to visit Japan for tourism, cherry blossom season, or meeting family and friends? Torii prepares your official Ministry of Foreign Affairs (MOFA) 2-page application form, day-by-day Schedule of Stay (滞在予定表), and formal Consular Cover Letter. Print, sign, and submit at VFS Global / Embassy of Japan with zero hassle.",
    filingModeLabel: "Official MOFA Form & Dossier (VFS Submission)",
    processingDays: "5–7 Days",
    visas: [
      {
        id: "tourist-short",
        name: "Tourist & Sightseeing Visa (短期滞在)",
        duration: "15 to 30 Days",
        entries: "Single Entry",
        validity: "3 Months from issue",
        processingTime: "5–7 Working Days",
        governmentFee: "৳2,700 (¥3,000) — Paid on approval only",
        toriiFee: "৳1,500",
        totalDisplay: "৳4,200",
        requiredDocuments: [
          "Original Passport (6+ months validity, 2+ blank pages)",
          "2 Copies Photos (45mm × 35mm, white background, matte finish)",
          "Bank Statement (Last 6 months) & Bank Solvency Certificate",
          "NOC from employer / Trade License with English translation",
          "Confirmed Flight Booking & Hotel Reservations",
          "Torii Auto-Generated Day-by-Day Schedule of Stay",
        ],
        description: "For independent leisure travelers exploring Japan's scenic culture and cities.",
      },
      {
        id: "visit-family",
        name: "Visiting Relatives & Friends (知人訪問)",
        duration: "Up to 90 Days",
        entries: "Single / Double Entry",
        validity: "3 Months",
        processingTime: "5–7 Working Days",
        governmentFee: "৳2,700 (¥3,000) — Paid on approval only",
        toriiFee: "৳1,500",
        totalDisplay: "৳4,200",
        requiredDocuments: [
          "Original Passport & Photos",
          "Invitation Letter & Letter of Guarantee from host in Japan",
          "Host's Juminhyo (Certificate of Residence) & Zairyu Card copy",
          "Applicant Bank Statements & Employment Proof",
          "Torii Consular Cover Letter",
        ],
        description: "For travelers invited by family members or friends residing in Japan.",
      },
    ],
    requiredSummary: [
      "Original passport with 6+ months validity",
      "2 Passport photos (45mm × 35mm, white background)",
      "Bank solvency certificate & 6 months statement",
      "Employment NOC / Student ID / Trade license",
      "Flight and hotel bookings (refundable reservation)",
    ],
    faqs: [
      {
        question: "Does the Japanese Embassy accept computer-typed forms?",
        answer:
          "Yes! The Ministry of Foreign Affairs (MOFA) strongly prefers typed forms to prevent handwriting errors. Torii generates a clean, typed PDF form where you only need to add your handwritten pen signature on the final page.",
      },
      {
        question: "When is the government visa fee paid for Japan in Bangladesh?",
        answer:
          "Japan operates on a unique 'No Visa, No Fee' principle! You pay the VFS service fee on the day you submit your documents, but the Japanese government visa fee (approx. ৳2,700) is ONLY paid when your visa is approved and you collect your passport.",
      },
      {
        question: "What is the 'Schedule of Stay' (滞在予定表)?",
        answer:
          "It is a mandatory document required by Japan immigration showing your day-by-day plan, hotel name, and contact details. Torii formats this itinerary cleanly according to official embassy requirements.",
      },
    ],
  },

  india: {
    slug: "india",
    code: "IN",
    name: "India",
    flag: "🇮🇳",
    heroImage: "/destinations/india.jpg",
    bannerTag: "Instant Embassy Cover Letter & Portal Links",
    tagline: "Medical Treatment, Attendant & Tourism Simplified",
    shortDescription: "Specialized Medical Visa (MED-1/MED-2) & Tourist Visa preparation for Indian Missions worldwide.",
    overview:
      "Applying for medical treatment in Kolkata, Chennai, Delhi, or touring India? Torii generates your formal Consular Embassy Cover Letter addressed to the Indian Mission, verifies all attendant and hospital invite requirements, and gives you the exact direct links to the official government registration and fee payment portals.",
    filingModeLabel: "Online Registration + IVAC Submission",
    processingDays: "3–5 Days",
    visas: [
      {
        id: "medical-new",
        name: "Medical Visa (MED-1) & Attendant (MED-2)",
        duration: "Up to 60 Days / 1 Year",
        entries: "Triple / Multiple Entry",
        validity: "Up to 1 Year",
        processingTime: "3–5 Working Days",
        governmentFee: "৳800 (Statutory consular fee at IVAC)",
        toriiFee: "৳1,200",
        totalDisplay: "৳2,000",
        requiredDocuments: [
          "Original Passport with 6+ months validity",
          "Official Indian Hospital Invitation Letter with treatment department",
          "Home Country Doctor Referral & Medical Diagnostic Reports",
          "Utility Bill (Proof of Residence / Address)",
          "Bank Statement or Endorsed International Credit Card",
          "Torii Consular Embassy Cover Letter (Auto-Generated)",
        ],
        description: "For patients seeking specialized medical care in recognized Indian hospitals and up to 2 accompanying attendants.",
      },
      {
        id: "tourist-new",
        name: "Regular Tourist Visa",
        duration: "30 to 90 Days",
        entries: "Single / Double Entry",
        validity: "Up to 1 Year",
        processingTime: "3–7 Working Days",
        governmentFee: "৳800 (Statutory fee at IVAC)",
        toriiFee: "৳1,200",
        totalDisplay: "৳2,000",
        requiredDocuments: [
          "Original Passport with 6+ months validity",
          "2 Recent 2x2 inch (50mm × 50mm) Photos on White Background",
          "Utility Bill (Electricity/Gas) for current address",
          "Bank Statement with minimum balance or card endorsement",
          "Employment NOC / Student ID / Trade License",
        ],
        description: "For sightseeing, casual travel, or visiting friends across India.",
      },
    ],
    requiredSummary: [
      "Original passport with 6+ months validity",
      "Recent 2x2 inch photos on white background",
      "Utility bill (Electricity/Gas) copy for address proof",
      "Hospital invitation letter (for Medical visa)",
      "Bank solvency proof or international card endorsement",
    ],
    faqs: [
      {
        question: "How do I fill the government form for an Indian Medical Visa?",
        answer:
          "Torii prepares your formal Consular Cover Letter and gives you the exact direct link to the government registration page (indianvisaonline.gov.in/visa/registration). On the government form, simply select 'Medical Visa' as Visa Type and 'For Medical Treatment' as Purpose.",
      },
      {
        question: "Can attendants accompany a medical patient?",
        answer:
          "Yes! Up to two medical attendants can travel under the Medical Attendant Visa (MED-2) category alongside the primary patient (MED-1). Torii includes attendant declarations right in your cover letter.",
      },
      {
        question: "Where do I submit the Indian visa in Bangladesh?",
        answer:
          "Applications are submitted at your nearest Indian Visa Application Centre (IVAC) located in Dhaka (Jamuna Future Park), Chittagong, Rajshahi, Sylhet, Khulna, etc.",
      },
    ],
  },

  "saudi-arabia": {
    slug: "saudi-arabia",
    code: "SA",
    name: "Saudi Arabia",
    flag: "🇸🇦",
    heroImage: "/destinations/saudi-arabia.jpg",
    bannerTag: "Instant e-Visa & Umrah Guidance",
    tagline: "Perform Umrah & Explore Modern Saudi Arabia",
    shortDescription: "Instant Tourist & Umrah eVisa guidance, requirements verification, and portal assistance.",
    overview:
      "Travel to Makkah, Madinah, Riyadh, and Al-Ula with ease. Saudi Arabia offers streamlined 1-Year Multiple Entry Tourist eVisas that allow tourism and performing Umrah (outside Hajj season). Torii verifies your eligibility, formats your passport scan, and guides you through the official KSA visa portal.",
    filingModeLabel: "Instant Electronic Visa (KSA Portal)",
    processingDays: "24–48 Hours",
    visas: [
      {
        id: "tourist-umrah-evisa",
        name: "Tourist & Umrah 1-Year Multiple Entry eVisa",
        duration: "Up to 90 Days stay per visit",
        entries: "Multiple Entry",
        validity: "1 Year from issuance",
        processingTime: "24 to 48 Hours",
        governmentFee: "Approx. ৳14,500 ($120 includes mandatory medical insurance)",
        toriiFee: "৳1,900",
        totalDisplay: "৳16,400",
        requiredDocuments: [
          "Original Passport with 6+ months validity",
          "Digital Passport Photo (200x200px, white background)",
          "Active email address for eVisa delivery",
          "Valid International Debit / Credit Card for portal fee",
          "Confirmed Accommodation details in Saudi Arabia",
        ],
        description: "Allows tourism, family visits, attending cultural events, and performing Umrah throughout the year.",
      },
    ],
    requiredSummary: [
      "Valid passport with minimum 6 months validity",
      "Digital passport-size photo (white background)",
      "Valid international payment card for statutory fee",
      "Confirmed flight and hotel accommodation details",
    ],
    faqs: [
      {
        question: "Can I perform Umrah on a Saudi Tourist Visa?",
        answer:
          "Yes! The Saudi Ministry of Hajj and Umrah permits holders of Tourist and eVisa visas to perform Umrah at any time of the year (except during the official Hajj pilgrimage season).",
      },
      {
        question: "How long can I stay in Saudi Arabia on this visa?",
        answer:
          "The visa is valid for 1 full year with multiple entries. You can stay for up to 90 consecutive days on each visit.",
      },
      {
        question: "Does the government fee include health insurance?",
        answer:
          "Yes, the statutory government fee automatically includes comprehensive medical insurance coverage for emergencies during your stay in the Kingdom.",
      },
    ],
  },
};

export const POPULAR_DESTINATIONS = [
  DESTINATIONS.japan,
  DESTINATIONS.india,
  DESTINATIONS["saudi-arabia"],
];
