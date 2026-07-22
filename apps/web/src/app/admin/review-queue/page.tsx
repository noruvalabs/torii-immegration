import { ClipboardCheck } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function ReviewQueuePage() {
  return (
    <SectionPlaceholder
      icon={ClipboardCheck}
      title="Review queue"
      description="Where the platform's honesty about its limits becomes a real service: every escalated or low-confidence case, with full context, waiting for a human."
      capabilities={[
        "See each queued case with its escalation reason and inputs",
        "Open a case's generated work and resolve it, recording the outcome",
        "Access limited to authorized reviewers (least-privilege)",
      ]}
      stories={["US-13", "US-15", "US-27"]}
    />
  );
}
