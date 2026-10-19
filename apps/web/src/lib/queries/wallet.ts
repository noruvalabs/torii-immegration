import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getWallet,
  getWalletSummary,
  getDocumentTypes,
  getDocumentVersions,
  uploadDocument,
  deleteDocument,
  patchWalletDocument,
  type WalletDocument,
  type WalletSummary,
  type DocumentType,
  type DocumentVersion,
} from "@/lib/api/wallet";

import { caseKeys } from "./cases";

export const walletKeys = {
  all: ["wallet"] as const,
  list: () => ["wallet", "list"] as const,
  summary: () => ["wallet", "summary"] as const,
  types: () => ["wallet", "types"] as const,
  versions: (id: number) => ["wallet", "versions", id] as const,
};

export function useWalletQuery(token: string | null) {
  return useQuery<WalletDocument[]>({
    queryKey: walletKeys.list(),
    queryFn: async () => {
      try {
        return await getWallet(token);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token),
  });
}

export function useWalletSummaryQuery(token: string | null) {
  return useQuery<WalletSummary | null>({
    queryKey: walletKeys.summary(),
    queryFn: async () => {
      try {
        return await getWalletSummary(token);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token),
  });
}

export function useDocumentTypesQuery(token: string | null) {
  return useQuery<DocumentType[]>({
    queryKey: walletKeys.types(),
    queryFn: async () => {
      try {
        const res = await getDocumentTypes(token);
        return res.document_types || [];
      } catch {
        return [];
      }
    },
    enabled: Boolean(token),
  });
}

export function useDocumentVersionsQuery(token: string | null, documentId: number | null) {
  return useQuery<DocumentVersion[]>({
    queryKey: walletKeys.versions(documentId ?? 0),
    queryFn: async () => {
      if (!documentId) return [];
      try {
        return await getDocumentVersions(documentId, token);
      } catch {
        return [];
      }
    },
    enabled: Boolean(token && documentId),
  });
}

export function useUploadDocumentMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      docType,
      name,
      issuedDate,
      expiryDate,
      notes,
    }: {
      file: File;
      docType: string;
      name?: string;
      issuedDate?: string;
      expiryDate?: string;
      notes?: string;
    }) => uploadDocument(token, file, docType, name, issuedDate, expiryDate, notes),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: walletKeys.all });
      void queryClient.invalidateQueries({ queryKey: caseKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["auth"] });
    },
  });
}

export function useDeleteDocumentMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: number) => deleteDocument(documentId, token),
    onSuccess: (_, documentId) => {
      queryClient.setQueryData<WalletDocument[]>(walletKeys.list(), (prev) =>
        prev ? prev.filter((d) => d.id !== documentId) : [],
      );
      void queryClient.invalidateQueries({ queryKey: walletKeys.all });
    },
  });
}

export function usePatchDocumentMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      documentId,
      data,
    }: {
      documentId: number;
      data: { name?: string; issued_date?: string; expiry_date?: string; notes?: string };
    }) => patchWalletDocument(documentId, data, token),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: walletKeys.all });
    },
  });
}
