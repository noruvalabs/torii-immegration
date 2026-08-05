"use client";

import { useCallback, useEffect, useState } from "react";
import { Shield } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth-context";

type User = {
  id: number;
  email: string;
  username: string | null;
  role: string;
  is_active: boolean;
  email_verified: boolean;
};

const API = "/backend/v1/admin/users";

const ROLE_OPTIONS = ["applicant", "ops", "employer", "admin"];

export default function StaffPage() {
  const { token, user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterRole, setFilterRole] = useState<string>("");

  const headers = useCallback(
    (): Record<string, string> => {
      const h: Record<string, string> = { "content-type": "application/json" };
      if (token) h.Authorization = `Bearer ${token}`;
      return h;
    },
    [token],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = filterRole ? `?role=${filterRole}` : "";
      const [usersRes, countRes] = await Promise.all([
        fetch(`${API}${params}`, { cache: "no-store", headers: headers() }),
        fetch(`${API}/count`, { cache: "no-store", headers: headers() }),
      ]);
      if (!usersRes.ok) throw new Error(`API returned ${usersRes.status}`);
      setUsers(await usersRes.json());
      if (countRes.ok) setCounts(await countRes.json());
    } catch {
      setError("Could not reach the API. Is torii-api running on :8000?");
    } finally {
      setLoading(false);
    }
  }, [headers, filterRole]);

  useEffect(() => {
    void load();
  }, [load]);

  async function changeRole(userId: number, role: string) {
    setError(null);
    try {
      const res = await fetch(`${API}/${userId}/role`, {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({ role }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to change role");
    }
  }

  async function toggleActive(userId: number, isActive: boolean) {
    setError(null);
    try {
      const res = await fetch(`${API}/${userId}/active`, {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({ is_active: isActive }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API returned ${res.status}`);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update user");
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-start gap-4">
        <div className="flex size-11 items-center justify-center rounded-[var(--radius)] bg-accent text-accent-foreground">
          <Shield className="size-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Staff & roles</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage user accounts and role-based access. Roles control what each
            team member can do across the platform (US-30).
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-[var(--radius)] border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {error}
        </p>
      )}

      {/* Role summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {ROLE_OPTIONS.map((r) => (
          <button
            key={r}
            onClick={() => setFilterRole(filterRole === r ? "" : r)}
            className={`rounded-[var(--radius)] border p-3 text-left transition-colors ${
              filterRole === r
                ? "border-primary bg-primary/5"
                : "bg-card hover:bg-accent"
            }`}
          >
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {r}
            </p>
            <p className="mt-1 text-2xl font-semibold">{counts[r] ?? 0}</p>
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-5 text-sm text-muted-foreground">Loading…</p>
          ) : users.length === 0 ? (
            <p className="p-5 text-sm text-muted-foreground">
              {filterRole
                ? `No ${filterRole} users found.`
                : "No users yet."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-3 font-medium">User</th>
                    <th className="px-5 py-3 font-medium">Role</th>
                    <th className="px-5 py-3 font-medium">Status</th>
                    <th className="px-5 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b last:border-0">
                      <td className="px-5 py-3">
                        <div>
                          <p className="font-medium">{u.email}</p>
                          {u.username && (
                            <p className="text-xs text-muted-foreground">
                              @{u.username}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <select
                          value={u.role}
                          disabled={u.id === currentUser?.id}
                          onChange={(e) => changeRole(u.id, e.target.value)}
                          className="h-8 rounded-[var(--radius)] border bg-background px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-3">
                        <Badge tone={u.is_active ? "success" : "danger"}>
                          {u.is_active ? "active" : "inactive"}
                        </Badge>
                        {u.email_verified && (
                          <Badge tone="muted" className="ml-1">
                            verified
                          </Badge>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {u.id !== currentUser?.id && (
                          <button
                            onClick={() => toggleActive(u.id, !u.is_active)}
                            className="rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
