import { useQuery } from "@tanstack/react-query";
import {
  checkCorridor,
  getCorridor,
  type CorridorCheckIn,
  type CorridorCheckOut,
} from "@/lib/api/corridors";

export const corridorKeys = {
  all: ["corridors"] as const,
  check: (params: CorridorCheckIn) =>
    [
      "corridors",
      "check",
      (params.destination_code || "").toUpperCase(),
      (params.purpose_code || "").toLowerCase(),
      (params.action_code || "").toLowerCase(),
      (params.nationality || "").toUpperCase(),
      (params.residence_country || "").toUpperCase(),
    ] as const,
  detail: (id: number) => ["corridors", "detail", id] as const,
};

export function useCorridorCheckQuery(
  params: CorridorCheckIn | null,
  token?: string | null,
  enabled = true,
) {
  const isEnabled = Boolean(
    enabled &&
      params &&
      params.destination_code &&
      params.purpose_code &&
      params.action_code,
  );

  return useQuery<CorridorCheckOut>({
    queryKey: params ? corridorKeys.check(params) : ["corridors", "disabled"],
    queryFn: async () => {
      if (!params) throw new Error("Missing corridor params");
      return await checkCorridor(params, token);
    },
    enabled: isEnabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      if (data.status === "queued" || data.status === "running") {
        return 2500;
      }
      return false;
    },
    refetchIntervalInBackground: false,
    staleTime: 5 * 60 * 1000,
  });
}
