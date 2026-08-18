import type { ReactNode } from "react";
import { Sidebar } from "@/components/admin/sidebar";
import { AdminHeader } from "@/components/admin/admin-header";
import { AuthGuard } from "@/components/auth-guard";
import { RoleGuard } from "@/components/role-guard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <RoleGuard allowedRoles={["admin", "ops", "employer"]}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
            <AdminHeader />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
        </div>
      </RoleGuard>
    </AuthGuard>
  );
}
