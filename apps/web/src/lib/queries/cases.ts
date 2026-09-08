import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listCases,
  deleteCase,
  archiveCase,
  unarchiveCase,
  getCase,
  getCaseGuidance,
  getIntake,
  getEligibility,
  getChecklist,
  getForms,
  getOfficialForms,
  getFiling,
  getPacket,
  answerIntake,
  evaluateEligibility,
  refreshChecklist,
  patchChecklistItem,
  generateForms,
  type Case,
  type CaseGuidance,
  type IntakeState,
  type EligibilityResult,
  type ChecklistItem,
  type GeneratedForm,
  type OfficialFormsResponse,
  type FilingInfo,
} from "@/lib/api/cases";

export const caseKeys = {
  all: ["cases"] as const,
  list: () => ["cases", "list"] as const,
  detail: (id: number) => ["cases", "detail", id] as const,
  guidance: (id: number) => ["cases", "guidance", id] as const,
  intake: (id: number) => ["cases", "intake", id] as const,
  eligibility: (id: number) => ["cases", "eligibility", id] as const,
  checklist: (id: number) => ["cases", "checklist", id] as const,
  forms: (id: number) => ["cases", "forms", id] as const,
  officialForms: (id: number) => ["cases", "officialForms", id] as const,
  filing: (id: number) => ["cases", "filing", id] as const,
  packet: (id: number) => ["cases", "packet", id] as const,
};

export function useCasesListQuery(token: string | null) {
  return useQuery<Case[]>({
    queryKey: caseKeys.list(),
    queryFn: async () => {
      try {
        return await listCases(token!);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token),
  });
}

export function useDeleteCaseMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (caseId: number) => deleteCase(token!, caseId),
    onSuccess: (_, caseId) => {
      queryClient.setQueryData<Case[]>(caseKeys.list(), (prev) =>
        prev ? prev.filter((c) => c.id !== caseId) : [],
      );
      void queryClient.invalidateQueries({ queryKey: caseKeys.list() });
      void queryClient.removeQueries({ queryKey: caseKeys.detail(caseId) });
    },
  });
}

export function useArchiveCaseMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (caseId: number) => archiveCase(token!, caseId),
    onSuccess: (updated) => {
      queryClient.setQueryData<Case[]>(caseKeys.list(), (prev) =>
        prev ? prev.map((c) => (c.id === updated.id ? updated : c)) : [],
      );
      void queryClient.invalidateQueries({ queryKey: caseKeys.list() });
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(updated.id) });
    },
  });
}

export function useUnarchiveCaseMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (caseId: number) => unarchiveCase(token!, caseId),
    onSuccess: (updated) => {
      queryClient.setQueryData<Case[]>(caseKeys.list(), (prev) =>
        prev ? prev.map((c) => (c.id === updated.id ? updated : c)) : [],
      );
      void queryClient.invalidateQueries({ queryKey: caseKeys.list() });
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(updated.id) });
    },
  });
}

export function useCaseQuery(token: string | null, caseId: number) {
  return useQuery<Case>({
    queryKey: caseKeys.detail(caseId),
    queryFn: () => getCase(token!, caseId),
    enabled: Boolean(token && caseId),
  });
}

export function useCaseGuidanceQuery(
  token: string | null,
  caseId: number,
  options?: { refetchInterval?: number | false | ((query: { state: { data: CaseGuidance | undefined } }) => number | false) },
) {
  return useQuery<CaseGuidance>({
    queryKey: caseKeys.guidance(caseId),
    queryFn: () => getCaseGuidance(token!, caseId),
    enabled: Boolean(token && caseId),
    refetchInterval: options?.refetchInterval,
  });
}

export function useIntakeQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<IntakeState | null>({
    queryKey: caseKeys.intake(caseId),
    queryFn: async () => {
      try {
        return await getIntake(token!, caseId);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function useEligibilityQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<EligibilityResult | null>({
    queryKey: caseKeys.eligibility(caseId),
    queryFn: async () => {
      try {
        return await getEligibility(token!, caseId);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function useChecklistQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<ChecklistItem[]>({
    queryKey: caseKeys.checklist(caseId),
    queryFn: async () => {
      try {
        return await getChecklist(token!, caseId);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function useFormsQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<GeneratedForm[]>({
    queryKey: caseKeys.forms(caseId),
    queryFn: async () => {
      try {
        return await getForms(token!, caseId);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function useOfficialFormsQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<OfficialFormsResponse | null>({
    queryKey: caseKeys.officialForms(caseId),
    queryFn: async () => {
      try {
        return await getOfficialForms(token!, caseId);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function useFilingQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<FilingInfo | null>({
    queryKey: caseKeys.filing(caseId),
    queryFn: async () => {
      try {
        return await getFiling(token!, caseId);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

export function usePacketQuery(token: string | null, caseId: number, enabled = true) {
  return useQuery<Record<string, unknown> | null>({
    queryKey: caseKeys.packet(caseId),
    queryFn: async () => {
      try {
        return await getPacket(token!, caseId);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token && caseId && enabled),
  });
}

// ── Mutations ──────────────────────────────────────────────────────────────────

export function useAnswerIntakeMutation(token: string | null, caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      answerIntake(token!, caseId, key, value),
    onSuccess: (updatedState) => {
      queryClient.setQueryData(caseKeys.intake(caseId), updatedState);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
    },
  });
}

export function useEvaluateEligibilityMutation(token: string | null, caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => evaluateEligibility(token!, caseId),
    onSuccess: (result) => {
      queryClient.setQueryData(caseKeys.eligibility(caseId), result);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    },
  });
}

export function usePatchChecklistItemMutation(token: string | null, caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, status }: { itemId: number; status: string }) =>
      patchChecklistItem(token!, caseId, itemId, status),
    onSuccess: (_, { itemId, status }) => {
      queryClient.setQueryData<ChecklistItem[]>(caseKeys.checklist(caseId), (prev) =>
        prev ? prev.map((item) => (item.id === itemId ? { ...item, status } : item)) : prev,
      );
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    },
  });
}

export function useRefreshChecklistMutation(token: string | null, caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => refreshChecklist(token!, caseId),
    onSuccess: (items) => {
      queryClient.setQueryData(caseKeys.checklist(caseId), items);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
      void queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
    },
  });
}

export function useGenerateFormsMutation(token: string | null, caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => generateForms(token!, caseId),
    onSuccess: (forms) => {
      queryClient.setQueryData(caseKeys.forms(caseId), forms);
      void queryClient.invalidateQueries({ queryKey: caseKeys.guidance(caseId) });
    },
  });
}
