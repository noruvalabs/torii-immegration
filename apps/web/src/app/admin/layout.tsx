import type { ReactNode } from "react";
import { Sidebar } from "@/components/admin/sidebar";
import { AdminHeader } from "@/components/admin/admin-header";
import { AdminSidebarProvider } from "@/components/admin/admin-sidebar-context";
import { AuthGuard } from "@/components/auth-guard";
import { RoleGuard } from "@/components/role-guard";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <RoleGuard allowedRoles={["admin", "ops", "employer"]}>
        <AdminSidebarProvider>
          <div className="flex h-screen overflow-hidden flex-col md:flex-row">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
              <AdminHeader />
              <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
            </div>
          </div>
        </AdminSidebarProvider>
      </RoleGuard>
    </AuthGuard>
  );
}
