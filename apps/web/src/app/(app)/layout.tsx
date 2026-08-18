import type { ReactNode } from "react";
import { ApplicantSidebar } from "@/components/applicant/sidebar";
import { FloatingAssistant } from "@/components/applicant/FloatingAssistant";
import { AuthGuard } from "@/components/auth-guard";

export default function ApplicantLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden flex-col md:flex-row relative">
        <ApplicantSidebar />
        <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</main>
        </div>
        <FloatingAssistant />
      </div>
    </AuthGuard>
  );
}

