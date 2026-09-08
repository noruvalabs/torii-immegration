import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getProfile,
  updateProfile,
  uploadAvatar,
  type User,
  type ProfileUpdate,
} from "@/lib/api/auth";

export const profileKeys = {
  all: ["profile"] as const,
  current: () => ["profile", "current"] as const,
};

export function useProfileQuery(token: string | null, initialData?: User | null) {
  return useQuery<User | null>({
    queryKey: profileKeys.current(),
    queryFn: async () => {
      try {
        return await getProfile(token!);
      } catch {
        return null;
      }
    },
    enabled: Boolean(token),
    initialData: initialData || undefined,
  });
}

export function useUpdateProfileMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProfileUpdate) => updateProfile(token!, payload),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(profileKeys.current(), updatedUser);
    },
  });
}

export function useUploadAvatarMutation(token: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadAvatar(token!, file),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(profileKeys.current(), updatedUser);
    },
  });
}
