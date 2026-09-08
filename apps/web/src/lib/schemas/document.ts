import { z } from "zod";

export const documentUploadSchema = z.object({
  selectedType: z.string().min(1, "Please select a document type"),
  docName: z.string().trim().optional().or(z.literal("")),
  issuedDate: z.string().trim().optional().or(z.literal("")),
  expiryDate: z.string().trim().optional().or(z.literal("")),
});

export type DocumentUploadFormData = z.infer<typeof documentUploadSchema>;

export const documentMetadataSchema = z.object({
  name: z.string().trim().min(1, "Document name is required"),
  issued_date: z.string().trim().optional().or(z.literal("")),
  expiry_date: z.string().trim().optional().or(z.literal("")),
});

export type DocumentMetadataFormData = z.infer<typeof documentMetadataSchema>;

export const documentVersionSchema = z.object({
  name: z.string().trim().optional().or(z.literal("")),
  issuedDate: z.string().trim().optional().or(z.literal("")),
  expiryDate: z.string().trim().optional().or(z.literal("")),
  notes: z.string().trim().optional().or(z.literal("")),
});

export type DocumentVersionFormData = z.infer<typeof documentVersionSchema>;

