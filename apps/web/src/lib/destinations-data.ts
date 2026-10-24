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
  overview?: string;
  filingModeLabel: string;
  processingDays: string;
  serviceModel?: "portal_payment_concierge" | "official_dossier_kit";
  serviceHeadline?: string;
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
    serviceModel: "official_dossier_kit",
    serviceHeadline: "Low Service Charge: Official typed MOFA form & itinerary kit. Pay embassy fee only on approval.",
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
        question: "When is the government visa fee paid for Japan?",
        answer:
          "Japan operates on a unique 'No Visa, No Fee' principle! You pay the consular or VAC appointment service fee upon document submission, but the Japanese government visa fee is only collected once your visa is approved and issued.",
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
    serviceModel: "portal_payment_concierge",
    serviceHeadline: "Full Portal Submission: We register your application on the official Indian portal and pay the IVAC statutory fee for you.",
    visas: [
      {
        id: "medical-new",
        name: "Medical Visa (MED-1) & Attendant (MED-2)",
        duration: "Up to 60 Days / 1 Year",
        entries: "Triple / Multiple Entry",
        validity: "Up to 1 Year",
        processingTime: "3–5 Working Days",
        governmentFee: "$10 (Statutory consular fee at IVAC / Mission)",
        toriiFee: "$15",
        totalDisplay: "$25",
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
        governmentFee: "$10 (Statutory fee at IVAC / Mission)",
        toriiFee: "$15",
        totalDisplay: "$25",
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
        question: "Do I have to fill the government online form myself?",
        answer:
          "No! You do not need to fill any government forms or visit foreign portals. Simply provide your basic details once on Torii, and our dedicated staff team submits your full application directly on the official Indian Visa Online portal, pays the embassy fee, and delivers your official IVAC appointment confirmation.",
      },
      {
        question: "Can attendants accompany a medical patient?",
        answer:
          "Yes! Up to two medical attendants can travel under the Medical Attendant Visa (MED-2) category alongside the primary patient (MED-1). Torii includes attendant declarations right in your cover letter.",
      },
      {
        question: "Where do I submit my Indian visa application?",
        answer:
          "Applications are submitted at your nearest authorized Indian Visa Application Centre (IVAC / VFS) or Indian diplomatic mission in your country of residence.",
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
    serviceModel: "portal_payment_concierge",
    serviceHeadline: "Full Online e-Visa: We submit on the official KSA portal, handle foreign currency fee & mandatory medical insurance.",
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

  "united-states": {
    slug: "united-states",
    code: "US",
    name: "United States",
    flag: "🇺🇸",
    heroImage: "/destinations/united-states.jpg",
    bannerTag: "B1/B2 DS-160 Dossier",
    tagline: "Explore America from Coast to Coast",
    shortDescription: "Complete DS-160 electronic filing preparation, consular cover letter, and embassy interview binder.",
    overview:
      "Applying for a US B1/B2 Visitor Visa? Torii helps you prepare your DS-160 application form without errors, generates your formal travel plan, and structures your interview documentation to establish strong economic and familial ties to your home country.",
    filingModeLabel: "DS-160 Form + Consular Interview",
    processingDays: "Interview Appointment",
    visas: [
      {
        id: "b1-b2-visitor",
        name: "B1/B2 Tourist & Business Visitor Visa",
        duration: "Up to 6 Months per visit",
        entries: "Multiple Entry",
        validity: "Up to 5 Years",
        processingTime: "Based on US Embassy interview availability",
        governmentFee: "৳22,500 ($185 MRV statutory fee)",
        toriiFee: "৳2,500",
        totalDisplay: "৳25,000",
        requiredDocuments: [
          "Original Passport (valid at least 6 months beyond intended stay)",
          "DS-160 Barcode Confirmation Page",
          "MRV Fee Payment Receipt",
          "Recent 2x2 inch (51mm × 51mm) Color Photo (white background)",
          "Employment NOC, Salary Certificates & Last 6 Months Bank Statement",
          "Torii Consular Cover Letter & Structured Travel Itinerary",
        ],
        description: "For tourism, vacation, visiting friends and family, or attending business conferences across the United States.",
      },
    ],
    requiredSummary: [
      "Original passport with 6+ months validity",
      "DS-160 barcode confirmation page",
      "MRV visa appointment confirmation receipt",
      "2x2 inch photo complying with US consular standards",
      "Bank solvency proof & 6 months statement",
    ],
    faqs: [
      {
        question: "Does Torii schedule the US Embassy interview appointment?",
        answer:
          "Torii prepares your full DS-160 application package and consular interview folder. You then book your preferred interview date directly via the official ustraveldocs / US Embassy appointment system.",
      },
      {
        question: "How long is the US B1/B2 visa valid for international travelers?",
        answer:
          "Depending on reciprocity with your country of citizenship, US visitor visas are commonly issued for 1 to 10 years multiple-entry. Upon arrival, the US CBP officer generally stamps permission to stay for up to 6 months per visit.",
      },
    ],
  },

  canada: {
    slug: "canada",
    code: "CA",
    name: "Canada",
    flag: "🇨🇦",
    heroImage: "/destinations/canada.jpg",
    bannerTag: "IRCC Portal Preparation",
    tagline: "Experience Canada's Natural Wonders & Cities",
    shortDescription: "Temporary Resident Visa (TRV) application, IMM 5257 form preparation, and IRCC portal filing.",
    overview:
      "Planning to visit Canada for leisure, tourism, or visiting family? Torii formats your official IRCC IMM 5257 application, prepares your Purpose of Travel statement, and organizes your financial and employment documentation for biometric submission at VFS Dhaka.",
    filingModeLabel: "IRCC Online Portal + VFS Dhaka Biometrics",
    processingDays: "15–30 Days",
    visas: [
      {
        id: "visitor-trv",
        name: "Temporary Resident Visitor Visa (V-1 / TRV)",
        duration: "Up to 6 Months per stay",
        entries: "Multiple Entry",
        validity: "Up to 10 Years (or passport expiry)",
        processingTime: "2 to 4 Weeks",
        governmentFee: "৳15,000 (CAD 100 Visa + CAD 85 Biometrics)",
        toriiFee: "৳2,500",
        totalDisplay: "৳17,500",
        requiredDocuments: [
          "Original Passport with 2+ blank pages",
          "Digital Photo (35mm × 45mm, white background, neutral expression)",
          "Bank Statements (Last 6 Months) with Solvency Certificate",
          "Employment NOC / Trade License with English notarization",
          "Torii Purpose of Travel & Client Information Summary Letter",
        ],
        description: "For tourism, visiting family members or friends, and exploratory travel across Canada.",
      },
    ],
    requiredSummary: [
      "Valid passport with 6+ months validity",
      "Digital biometric photograph",
      "6-month bank statement & proof of financial solvency",
      "Employment NOC or business registration",
      "Detailed travel itinerary & invitation letter (if visiting family)",
    ],
    faqs: [
      {
        question: "Do I need to submit biometrics for a Canadian visa?",
        answer:
          "Yes, most international applicants are required to give biometrics (fingerprints and photo) at an authorized Visa Application Centre (VAC) in their country of residence after submitting the online application.",
      },
      {
        question: "Can I get a 10-year Canadian visitor visa?",
        answer:
          "Canada commonly issues multiple-entry visitor visas valid up to the expiration date of your passport (maximum 10 years).",
      },
    ],
  },

  france: {
    slug: "france",
    code: "FR",
    name: "France",
    flag: "🇫🇷",
    heroImage: "/destinations/france.jpg",
    bannerTag: "France-Visas Schengen Kit",
    tagline: "Visit Paris & Explore the Schengen Area",
    shortDescription: "Short-stay Schengen Tourist Visa (Type C) preparation, France-Visas form, and VFS dossier.",
    overview:
      "Travel to France and all 29 Schengen member states. Torii auto-generates your official Cerfa Schengen application form, day-by-day travel itinerary, and consular cover letter formatted according to the Embassy of France in Dhaka guidelines.",
    filingModeLabel: "France-Visas + VFS Global Submission",
    processingDays: "10–15 Days",
    visas: [
      {
        id: "schengen-tourist-fr",
        name: "Schengen Short-Stay Tourist Visa (Type C)",
        duration: "Up to 90 Days in any 180-day period",
        entries: "Single / Multiple Entry",
        validity: "Up to 6 Months",
        processingTime: "10–15 Working Days",
        governmentFee: "৳11,500 (€90 statutory consular fee)",
        toriiFee: "৳2,000",
        totalDisplay: "৳13,500",
        requiredDocuments: [
          "Original Passport (issued within 10 years, 3+ months validity post-stay)",
          "2 Schengen Photos (35mm × 45mm, grey/white background)",
          "Travel Medical Insurance (€30,000 minimum Schengen coverage)",
          "Confirmed Flight Itinerary & Hotel Bookings across France",
          "Bank Statement (Last 6 Months) & Tax Assessment (TIN)",
          "Torii Consular Cover Letter & Day-by-Day Travel Plan",
        ],
        description: "Allows free travel throughout France and all 29 Schengen countries for leisure and sightseeing.",
      },
    ],
    requiredSummary: [
      "Original passport with 3+ months validity past return date",
      "2 Biometric Schengen photos (35x45mm)",
      "€30,000 Schengen travel health insurance policy",
      "Bank solvency certificate & 6 months statement",
      "Flight and accommodation reservations",
    ],
    faqs: [
      {
        question: "Can I travel to other European countries with a French Schengen Visa?",
        answer:
          "Yes! A uniform Schengen visa issued by France allows you to travel freely throughout all 29 Schengen zone countries (including Germany, Italy, Spain, Switzerland, etc.).",
      },
      {
        question: "What is the minimum travel insurance required?",
        answer:
          "The Schengen regulation mandates travel medical insurance with minimum coverage of €30,000 covering emergency hospitalization and repatriation.",
      },
    ],
  },

  spain: {
    slug: "spain",
    code: "ES",
    name: "Spain",
    flag: "🇪🇸",
    heroImage: "/destinations/spain.jpg",
    bannerTag: "BLS Schengen Dossier",
    tagline: "Discover Barcelona, Madrid & Andalusia",
    shortDescription: "Spain Tourist Schengen Visa (Type C) preparation and BLS International Dhaka submission kit.",
    overview:
      "Planning a holiday to Spain? Torii organizes your official Schengen application form, hotel bookings, flight route itinerary, and cover letter for submission at BLS International in Dhaka with complete accuracy.",
    filingModeLabel: "Schengen Form + BLS International Dhaka",
    processingDays: "10–15 Days",
    visas: [
      {
        id: "schengen-tourist-es",
        name: "Spain Tourist Schengen Visa (Type C)",
        duration: "Up to 90 Days",
        entries: "Single / Multiple Entry",
        validity: "Up to 6 Months",
        processingTime: "10–15 Working Days",
        governmentFee: "৳11,500 (€90 statutory fee + BLS service fee)",
        toriiFee: "৳2,000",
        totalDisplay: "৳13,500",
        requiredDocuments: [
          "Original Passport with 2+ blank pages",
          "2 Recent Biometric Photos (35mm × 45mm, white background)",
          "Travel Medical Insurance with minimum €30,000 coverage",
          "6 Months Bank Statement & Solvency Certificate",
          "Employment NOC / Student ID / Trade License with translation",
          "Torii Consular Cover Letter & Day-by-Day Stay Itinerary",
        ],
        description: "For independent leisure travelers exploring Spain and the wider Schengen area.",
      },
    ],
    requiredSummary: [
      "Valid passport with 2+ blank pages",
      "2 Schengen-standard biometric photos",
      "Travel insurance with minimum €30,000 coverage",
      "6-month bank statement & solvency proof",
      "Confirmed round-trip flight booking & hotel vouchers",
    ],
    faqs: [
      {
        question: "Where do I submit my Spain Schengen visa?",
        answer:
          "Schengen visa applications for Spain are officially submitted through authorized VAC centers (such as BLS International) or the Spanish consular mission in your region.",
      },
      {
        question: "How long before travel should I apply for Spain?",
        answer:
          "You can apply up to 6 months before your intended departure date. We recommend applying at least 3 to 4 weeks ahead.",
      },
    ],
  },

  germany: {
    slug: "germany",
    code: "DE",
    name: "Germany",
    flag: "🇩🇪",
    heroImage: "/destinations/germany.jpg",
    bannerTag: "VIDEX Schengen Kit",
    tagline: "Visit Germany & the Heart of Europe",
    shortDescription: "Official VIDEX electronic Schengen form generation and German Embassy Dhaka submission file.",
    overview:
      "Visiting Germany for tourism, trade fairs, or visiting family? Torii prepares your official VIDEX electronic form, Day-by-Day schedule, and consular declaration according to the German Embassy in Dhaka.",
    filingModeLabel: "VIDEX Electronic Form + German Embassy Submission",
    processingDays: "10–15 Days",
    visas: [
      {
        id: "schengen-tourist-de",
        name: "Germany Schengen Tourist & Visitor Visa",
        duration: "Up to 90 Days",
        entries: "Single / Multiple Entry",
        validity: "Up to 6 Months",
        processingTime: "10–15 Working Days",
        governmentFee: "৳11,500 (€90 statutory consular fee)",
        toriiFee: "৳2,000",
        totalDisplay: "৳13,500",
        requiredDocuments: [
          "Original Passport (valid 3+ months beyond intended return)",
          "VIDEX Online Application Form with 2D Barcode",
          "2 Recent Biometric Photos (35mm × 45mm, light background)",
          "Schengen Travel Medical Insurance (€30,000 cover)",
          "6 Months Bank Statement & Tax Return Certificate",
          "Employment NOC or Trade License with English translation",
        ],
        description: "For holidaymakers, cultural visitors, and attending exhibitions across Germany and Europe.",
      },
    ],
    requiredSummary: [
      "Original passport with 3+ months validity post-return",
      "VIDEX application form with 2D barcode",
      "€30,000 Schengen travel health insurance",
      "Bank solvency certificate & last 6 months statement",
      "Employment NOC / business registration documents",
    ],
    faqs: [
      {
        question: "What is the VIDEX form?",
        answer:
          "VIDEX is the official online application system utilized by the German Federal Foreign Office. Torii formats your responses into the official VIDEX format with the required 2D barcode.",
      },
      {
        question: "Can I attend trade fairs in Germany on this visa?",
        answer:
          "Yes! The short-stay Schengen visa permits attending trade fairs, exhibitions, and business meetings in Germany.",
      },
    ],
  },

  "south-korea": {
    slug: "south-korea",
    code: "KR",
    name: "South Korea",
    flag: "🇰🇷",
    heroImage: "/destinations/south-korea.jpg",
    bannerTag: "C-3-9 Tourist Dossier",
    tagline: "Experience K-Culture & Modern Seoul",
    shortDescription: "Short-Term General Tourist Visa (C-3-9) preparation for the Embassy of the Republic of Korea.",
    overview:
      "Explore Seoul, Busan, and Jeju Island. Torii formats your official Republic of Korea visa application form, prepares your travel itinerary and financial capability binder, and ensures compliance with Korean consular standards in Dhaka.",
    filingModeLabel: "Official Form + Embassy of Korea Dhaka Submission",
    processingDays: "7–10 Days",
    visas: [
      {
        id: "tourist-c39",
        name: "Short-Term General Tourist Visa (C-3-9)",
        duration: "Up to 90 Days",
        entries: "Single Entry",
        validity: "3 Months from issue date",
        processingTime: "7–10 Working Days",
        governmentFee: "৳4,800 ($40 statutory single entry fee)",
        toriiFee: "৳1,500",
        totalDisplay: "৳6,300",
        requiredDocuments: [
          "Original Passport with 6+ months validity",
          "1 Color Photo (35mm × 45mm, white background, taken within 6 months)",
          "Official Korean Visa Application Form (Typed & Completed)",
          "Bank Statement (Last 6 months) & Bank Solvency Certificate",
          "Company NOC / Student ID / Trade License",
          "Detailed Day-by-Day Travel Schedule in Korea",
        ],
        description: "For independent leisure travel, sightseeing, and cultural exploration in South Korea.",
      },
    ],
    requiredSummary: [
      "Original passport with 6+ months validity",
      "Recent passport-size photo (35x45mm, white background)",
      "Bank solvency certificate & 6 months statement",
      "Employment NOC / Student ID / Trade license",
      "Day-by-day travel plan and confirmed flight booking",
    ],
    faqs: [
      {
        question: "Does the Embassy of South Korea in Dhaka accept typed forms?",
        answer:
          "Yes! The consular section strongly prefers cleanly typed forms. Torii fills out the official MOFA Republic of Korea form so you only sign at the end.",
      },
      {
        question: "How long can I stay in South Korea as a tourist?",
        answer:
          "Standard C-3-9 tourist visas permit a stay of up to 90 consecutive days from the date of entry.",
      },
    ],
  },
};

export const POPULAR_DESTINATIONS = [
  DESTINATIONS.japan,
  DESTINATIONS.india,
  DESTINATIONS["saudi-arabia"],
  DESTINATIONS["united-states"],
  DESTINATIONS.canada,
  DESTINATIONS.france,
  DESTINATIONS.spain,
  DESTINATIONS.germany,
  DESTINATIONS["south-korea"],
];

