import { Building2 } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function EmployersPage() {
  return (
    <SectionPlaceholder
      icon={Building2}
      title="Employers"
      description="The B2B seam: HR teams sponsoring a foreign workforce, managing many visa cases from one place with compliance and deadline oversight."
      capabilities={[
        "One view of every employee's case, status, and owner",
        "Initiate and manage cases on behalf of employees (with their consent)",
        "Workforce-wide visa validity, upcoming deadlines, and exportable compliance view",
      ]}
      stories={["US-23", "US-24", "C15"]}
    />
  );
}
