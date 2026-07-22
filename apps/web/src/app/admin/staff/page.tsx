import { Users } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function StaffPage() {
  return (
    <SectionPlaceholder
      icon={Users}
      title="Staff & roles"
      description="Least-privilege access over highly sensitive immigration data: operations, admins, and partner lawyers each work within safe, configurable limits."
      capabilities={[
        "Define roles and assign permissions over back-office, employer, and review functions",
        "Grant, change, and revoke access, effective on the member's next actions",
        "Audit who accessed or changed sensitive case data, and when",
      ]}
      stories={["US-30", "NF-4", "NF-6"]}
    />
  );
}
