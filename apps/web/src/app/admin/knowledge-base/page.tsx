import { BookOpen } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function KnowledgeBasePage() {
  return (
    <SectionPlaceholder
      icon={BookOpen}
      title="Knowledge base"
      description="The product's factual foundation and its legal cover: the curated corpus of official government sources the platform reasons and cites from. If it can't be sourced, it isn't shown."
      capabilities={[
        "Add, update, and retire official-source material, each attributed to its origin",
        "Record origin and retrieval/version date so citations stay verifiable",
        "Government-change monitor flags for review before any live rule updates",
      ]}
      stories={["US-11", "US-25", "US-26"]}
    />
  );
}
