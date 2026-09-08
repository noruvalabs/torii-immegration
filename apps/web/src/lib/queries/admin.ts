import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  adminListCases,
  adminCountCases,
  adminListUsers,
  adminCountUsers,
  type AdminCase,
  type AdminUser,
} from "@/lib/api/admin";
import {
  listJurisdictions,
  listScopes,
  type AdminJurisdiction,
  type Scope,
} from "@/lib/api/jurisdictions";

export const adminKeys = {
  all: ["admin"] as const,
  cases: (opts?: { status?: string; offset?: number; limit?: number }) =>
    ["admin", "cases", opts] as const,
  caseCounts: () => ["admin", "cases", "count"] as const,
  users: (opts?: { role?: string; offset?: number; limit?: number }) =>
    ["admin", "users", opts] as const,
  userCounts: () => ["admin", "users", "count"] as const,
  jurisdictions: () => ["admin", "jurisdictions"] as const,
  scopes: () => ["admin", "scopes"] as const,
};

export function useAdminCasesQuery(
  token: string | null,
  opts?: { status?: string; offset?: number; limit?: number },
) {
  return useQuery<AdminCase[]>({
    queryKey: adminKeys.cases(opts),
    queryFn: async () => {
      try {
        return await adminListCases(token!, opts);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token),
  });
}

export function useAdminCaseCountsQuery(token: string | null) {
  return useQuery<Record<string, number>>({
    queryKey: adminKeys.caseCounts(),
    queryFn: async () => {
      try {
        return await adminCountCases(token!);
      } catch {
        return {};
      }
    },
    enabled: Boolean(token),
  });
}

export function useAdminJurisdictionsQuery(token: string | null) {
  return useQuery<AdminJurisdiction[]>({
    queryKey: adminKeys.jurisdictions(),
    queryFn: async () => {
      try {
        return await listJurisdictions(token!);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token),
  });
}
