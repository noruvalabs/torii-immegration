import { FolderKanban } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function CasesPage() {
  return (
    <SectionPlaceholder
      icon={FolderKanban}
      title="Cases"
      description="The single canonical case pipeline — self-serve, employer-managed, or lawyer-returned, all one case model with one status lifecycle, one document vault, one citation trail."
      capabilities={[
        "Browse and filter cases by jurisdiction, status, and owner",
        "Open a case: intake answers, documents, generated forms, citations, and history",
        "Track the status lifecycle from draft through submission and renewal",
      ]}
      stories={["US-03", "US-18", "NF-6"]}
    />
  );
}
