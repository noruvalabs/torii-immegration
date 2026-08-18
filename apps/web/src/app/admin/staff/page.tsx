"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Shield, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PaginationBar } from "@/components/ui/pagination";
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
  const [search, setSearch] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

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

  // Reset pagination to page 1 on filter or search change
  useEffect(() => {
    setCurrentPage(1);
  }, [filterRole, search]);

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        u.email.toLowerCase().includes(q) ||
        (u.username && u.username.toLowerCase().includes(q))
      );
    });
  }, [users, search]);

  const totalPages = Math.ceil(filteredUsers.length / pageSize) || 1;
  const paginatedUsers = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return filteredUsers.slice(startIndex, startIndex + pageSize);
  }, [filteredUsers, currentPage, pageSize]);

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
                ? "border-primary bg-primary/5 shadow-xs"
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

      {/* Search and filter bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email or username…"
            className="h-9 w-full rounded-[var(--radius)] border bg-background pl-9 pr-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        {filterRole && (
          <Badge tone="default" className="text-xs">
            Role: {filterRole}
          </Badge>
        )}
      </div>

      <div className="space-y-4">
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <p className="p-5 text-sm text-muted-foreground">Loading…</p>
            ) : filteredUsers.length === 0 ? (
              <p className="p-5 text-sm text-muted-foreground">
                {filterRole || search
                  ? "No matching users found."
                  : "No users yet."}
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="px-5">User</TableHead>
                    <TableHead className="px-5">Role</TableHead>
                    <TableHead className="px-5">Status</TableHead>
                    <TableHead className="px-5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedUsers.map((u) => (
                    <TableRow key={u.id}>
                      <TableCell className="px-5">
                        <div>
                          <p className="font-medium text-foreground">{u.email}</p>
                          {u.username && (
                            <p className="text-xs text-muted-foreground">
                              @{u.username}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="px-5">
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
                      </TableCell>
                      <TableCell className="px-5">
                        <Badge tone={u.is_active ? "success" : "danger"}>
                          {u.is_active ? "active" : "inactive"}
                        </Badge>
                        {u.email_verified && (
                          <Badge tone="muted" className="ml-1">
                            verified
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="px-5 text-right">
                        {u.id !== currentUser?.id && (
                          <button
                            onClick={() => toggleActive(u.id, !u.is_active)}
                            className="rounded-[var(--radius)] px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                          >
                            {u.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <PaginationBar
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={filteredUsers.length}
          pageSize={pageSize}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setCurrentPage(1);
          }}
          itemName="users"
        />
      </div>
    </div>
  );
}

