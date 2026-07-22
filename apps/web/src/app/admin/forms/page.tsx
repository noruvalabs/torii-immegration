import { FileText } from "lucide-react";
import { SectionPlaceholder } from "@/components/admin/section-placeholder";

export default function FormsPage() {
  return (
    <SectionPlaceholder
      icon={FileText}
      title="Forms & mappings"
      description="Government form templates and the pre-validated mapping from intake answers to their fields — first-class content owned by ops, not code, so form generation keeps pace with government changes."
      capabilities={[
        "Define a form template tied to a specific form and version",
        "Author and validate the intake-to-field mapping against test inputs",
        "Mark a version live, superseded, or draft — generation uses only live versions",
      ]}
      stories={["US-07", "US-08", "US-28"]}
    />
  );
}
