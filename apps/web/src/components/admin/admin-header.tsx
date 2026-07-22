"use client";

import { usePathname } from "next/navigation";
import { NAV } from "./nav";
import { Topbar } from "./topbar";

/** Derives the page title from the active nav item so section pages stay declarative. */
export function AdminHeader() {
  const pathname = usePathname();
  const items = NAV.flatMap((g) => g.items);
  const active =
    items
      .filter((i) => (i.href === "/admin" ? pathname === "/admin" : pathname.startsWith(i.href)))
      .sort((a, b) => b.href.length - a.href.length)[0] ?? null;
  return <Topbar title={active?.label ?? "Admin"} />;
}
