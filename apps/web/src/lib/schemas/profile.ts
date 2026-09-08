import { z } from "zod";

export const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Full legal name is required"),
  nationality: z.string().trim().min(1, "Nationality is required"),
  passport_number: z.string().trim().optional().or(z.literal("")),
  passport_expiry: z.string().trim().optional().or(z.literal("")),
  date_of_birth: z.string().trim().optional().or(z.literal("")),
  current_country: z.string().trim().min(1, "Current residence country is required"),
});

export type ProfileFormData = z.infer<typeof profileSchema>;
