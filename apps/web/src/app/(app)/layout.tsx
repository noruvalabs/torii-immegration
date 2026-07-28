import type { ReactNode } from "react";
import { ApplicantSidebar } from "@/components/applicant/sidebar";
import { AuthGuard } from "@/components/auth-guard";

export default function ApplicantLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <ApplicantSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
