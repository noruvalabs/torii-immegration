import { Settings } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function SettingsPage() {
  return (
    <SectionPlaceholder
      icon={Settings}
      title="Settings"
      description="Platform-level configuration owned by the overseer — the levers that let the system run itself within safe legal bounds without a developer."
      capabilities={[
        "Consent, data-residency, and retention policy defaults (GDPR-grade)",
        "Notification channels and renewal-reminder lead times",
        "Pricing, packaging, and entitlement configuration",
      ]}
      stories={["US-21", "US-22", "US-29"]}
    />
  );
}
