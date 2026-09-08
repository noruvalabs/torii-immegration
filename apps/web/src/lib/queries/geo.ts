import { useQuery } from "@tanstack/react-query";
import {
  getAllGeoData,
  getVisaTypes,
  getApplicationTypes,
  type GeoData,
  type VisaType,
  type ApplicationType,
} from "@/lib/api/geo";

export const geoKeys = {
  all: ["geo"] as const,
  data: () => ["geo", "data"] as const,
  visaTypes: (destinationCode: string) => ["geo", "visaTypes", destinationCode] as const,
  appTypes: (destinationCode: string, visaCode: string) =>
    ["geo", "appTypes", destinationCode, visaCode] as const,
};

export function useGeoDataQuery(enabled = true) {
  return useQuery<GeoData>({
    queryKey: geoKeys.data(),
    queryFn: () => getAllGeoData(),
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes cache
  });
}

export function useVisaTypesQuery(destinationCode?: string | null) {
  return useQuery<VisaType[]>({
    queryKey: geoKeys.visaTypes(destinationCode || ""),
    queryFn: () => getVisaTypes(destinationCode!),
    enabled: Boolean(destinationCode),
    staleTime: 10 * 60 * 1000,
  });
}

export function useApplicationTypesQuery(
  destinationCode?: string | null,
  visaCode?: string | null,
) {
  return useQuery<ApplicationType[]>({
    queryKey: geoKeys.appTypes(destinationCode || "", visaCode || ""),
    queryFn: () => getApplicationTypes(destinationCode!, visaCode!),
    enabled: Boolean(destinationCode && visaCode),
    staleTime: 10 * 60 * 1000,
  });
}
