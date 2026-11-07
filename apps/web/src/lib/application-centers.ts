export interface ApplicationCenter {
  id: string;
  name: string;
  shortName: string;
  city: string;
  address: string;
  landmark?: string;
  hours: string;
  submissionHours?: string;
  phone?: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  mapsUrl: string;
}

export interface CorridorCenters {
  jurisdictionCode: string;
  corridorName: string;
  operator: string;
  defaultCenterId: string;
  centers: ApplicationCenter[];
}

// Distance calculation using Haversine formula
export function calculateDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10;
}

export const CORRIDOR_CENTERS: Record<string, CorridorCenters> = {
  SA: {
    jurisdictionCode: "SA",
    corridorName: "Saudi Arabia (Tasheer)",
    operator: "Tasheer (Saudi Visa Service Center)",
    defaultCenterId: "sa-dhaka",
    centers: [
      {
        id: "sa-dhaka",
        name: "Tasheer Saudi Visa Center — Dhaka (Jamuna Future Park)",
        shortName: "Dhaka (Jamuna Future Park)",
        city: "Dhaka",
        address: "Level B2, South Court, Jamuna Future Park, Ka-244 Pragati Sharani, Kuril, Baridhara, Dhaka 1229",
        landmark: "Inside Jamuna Future Park Shopping Mall, Basement 2",
        hours: "Sunday – Thursday: 09:00 AM – 05:00 PM",
        submissionHours: "Token Issuance: 09:00 AM – 03:00 PM",
        phone: "+880 9610 203040",
        coordinates: { lat: 23.8135, lng: 90.4242 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=Tasheer+Visa+Service+Centre+Jamuna+Future+Park+Dhaka",
      },
      {
        id: "sa-chittagong",
        name: "Tasheer Saudi Visa Center — Chittagong",
        shortName: "Chittagong (Agrabad)",
        city: "Chittagong",
        address: "World Trade Center / Akhtaruzzaman Centre, Agrabad Commercial Area, Chittagong 4100",
        landmark: "Agrabad Commercial Area",
        hours: "Sunday – Thursday: 09:00 AM – 05:00 PM",
        submissionHours: "Token Issuance: 09:00 AM – 03:00 PM",
        phone: "+880 9610 203040",
        coordinates: { lat: 22.3275, lng: 91.8123 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=Tasheer+Saudi+Visa+Center+Agrabad+Chittagong",
      },
      {
        id: "sa-sylhet",
        name: "Tasheer Saudi Visa Center — Sylhet",
        shortName: "Sylhet (Mendibagh)",
        city: "Sylhet",
        address: "Garden Tower (3rd Floor), Shahjalal Bridge Road, Mendibagh / Amberkhana, Sylhet 3100",
        landmark: "Near Shahjalal Bridge",
        hours: "Sunday – Thursday: 09:00 AM – 05:00 PM",
        submissionHours: "Token Issuance: 09:00 AM – 03:00 PM",
        phone: "+880 9610 203040",
        coordinates: { lat: 24.8949, lng: 91.8687 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=Tasheer+Saudi+Visa+Center+Sylhet",
      },
    ],
  },
  IN: {
    jurisdictionCode: "IN",
    corridorName: "India (IVAC)",
    operator: "IVAC (Indian Visa Application Center)",
    defaultCenterId: "in-dhaka",
    centers: [
      {
        id: "in-dhaka",
        name: "IVAC Dhaka (Main) — Jamuna Future Park",
        shortName: "Dhaka (Jamuna Future Park)",
        city: "Dhaka",
        address: "Level G1, South Court, Jamuna Future Park, Progoti Sharani, Kuril, Dhaka 1229",
        landmark: "Ground Floor South Court, Jamuna Future Park",
        hours: "Sunday – Thursday: 09:00 AM – 05:00 PM",
        submissionHours: "Submission: 09:00 AM – 01:00 PM | Delivery: 02:00 PM – 05:00 PM",
        coordinates: { lat: 23.8135, lng: 90.4242 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=IVAC+Jamuna+Future+Park+Dhaka",
      },
      {
        id: "in-chittagong",
        name: "IVAC Chittagong — Habib Lane",
        shortName: "Chittagong (Chawkbazar)",
        city: "Chittagong",
        address: "2 Habib Lane, Shonir Akhra, Chawkbazar, Chittagong",
        hours: "Sunday – Thursday: 09:00 AM – 01:00 PM",
        coordinates: { lat: 22.3569, lng: 91.8335 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=IVAC+Chittagong",
      },
      {
        id: "in-sylhet",
        name: "IVAC Sylhet — Subidbazar",
        shortName: "Sylhet (Subidbazar)",
        city: "Sylhet",
        address: "Rose View Complex / Subidbazar Road, Sylhet 3100",
        hours: "Sunday – Thursday: 09:00 AM – 01:00 PM",
        coordinates: { lat: 24.9015, lng: 91.8596 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=IVAC+Sylhet",
      },
      {
        id: "in-rajshahi",
        name: "IVAC Rajshahi — Morupara",
        shortName: "Rajshahi (Morupara)",
        city: "Rajshahi",
        address: "Holding No. 284/2, Morupara, Rajshahi",
        hours: "Sunday – Thursday: 09:00 AM – 01:00 PM",
        coordinates: { lat: 24.3745, lng: 88.6042 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=IVAC+Rajshahi",
      },
      {
        id: "in-khulna",
        name: "IVAC Khulna — KDA Avenue",
        shortName: "Khulna (KDA Avenue)",
        city: "Khulna",
        address: "KDA Avenue, Choto Boyra, Khulna 9000",
        hours: "Sunday – Thursday: 09:00 AM – 01:00 PM",
        coordinates: { lat: 22.8456, lng: 89.5403 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=IVAC+Khulna",
      },
    ],
  },
  DEFAULT: {
    jurisdictionCode: "DEFAULT",
    corridorName: "VFS Global / Consular VAC",
    operator: "VFS Global Joint Visa Application Center",
    defaultCenterId: "vfs-dhaka",
    centers: [
      {
        id: "vfs-dhaka",
        name: "VFS Global Joint Visa Application Center — Dhaka",
        shortName: "Dhaka (Gulshan)",
        city: "Dhaka",
        address: "Delta Life Tower (4th & 5th Floor), Plot 37, Road 90, Gulshan North C/A, Dhaka 1212",
        landmark: "Delta Life Tower, Gulshan-2 Circle",
        hours: "Sunday – Thursday: 08:30 AM – 04:30 PM",
        submissionHours: "Passport Submission: 09:00 AM – 02:00 PM",
        coordinates: { lat: 23.7925, lng: 90.4152 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=VFS+Global+Delta+Life+Tower+Gulshan+Dhaka",
      },
      {
        id: "vfs-chittagong",
        name: "VFS Global Center — Chittagong",
        shortName: "Chittagong (Agrabad)",
        city: "Chittagong",
        address: "World Trade Center, Agrabad C/A, Chittagong 4100",
        landmark: "World Trade Center",
        hours: "Sunday – Thursday: 09:00 AM – 04:00 PM",
        coordinates: { lat: 22.3275, lng: 91.8123 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=VFS+Global+Chittagong",
      },
      {
        id: "vfs-sylhet",
        name: "VFS Global Center — Sylhet",
        shortName: "Sylhet (Ramkrishna Mission Rd)",
        city: "Sylhet",
        address: "7th Floor, Nirvana Inn, Ramkrishna Mission Road, Sylhet 3100",
        landmark: "Nirvana Inn Hotel Building",
        hours: "Sunday – Thursday: 09:00 AM – 04:00 PM",
        coordinates: { lat: 24.8917, lng: 91.8744 },
        mapsUrl: "https://www.google.com/maps/search/?api=1&query=VFS+Global+Sylhet",
      },
    ],
  },
};

export function getCorridorCenters(jurisdictionCode?: string | null): CorridorCenters {
  const code = (jurisdictionCode || "").toUpperCase();
  if (code in CORRIDOR_CENTERS) {
    return CORRIDOR_CENTERS[code];
  }
  return CORRIDOR_CENTERS.DEFAULT;
}

export function findNearestCenter(
  userLat: number,
  userLng: number,
  centers: ApplicationCenter[]
): { center: ApplicationCenter; distanceKm: number } {
  let nearest = centers[0];
  let minDistance = calculateDistanceKm(
    userLat,
    userLng,
    centers[0].coordinates.lat,
    centers[0].coordinates.lng
  );

  for (let i = 1; i < centers.length; i++) {
    const d = calculateDistanceKm(
      userLat,
      userLng,
      centers[i].coordinates.lat,
      centers[i].coordinates.lng
    );
    if (d < minDistance) {
      minDistance = d;
      nearest = centers[i];
    }
  }

  return { center: nearest, distanceKm: minDistance };
}

