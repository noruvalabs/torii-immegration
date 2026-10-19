import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (pathname.startsWith("/backend/")) {
    const apiBase =
      process.env.API_PROXY_TARGET ||
      process.env.API_INTERNAL_BASE_URL ||
      "http://localhost:8000";
    const subpath = pathname.replace(/^\/backend/, "");
    const dest = `${apiBase.replace(/\/$/, "")}${subpath}${search}`;
    return NextResponse.rewrite(new URL(dest));
  }

  if (pathname.startsWith("/assistant/")) {
    const aiBase =
      process.env.AI_PROXY_TARGET ||
      process.env.API_PROXY_TARGET ||
      process.env.API_INTERNAL_BASE_URL ||
      "http://localhost:8000";
    const subpath = pathname.replace(/^\/assistant/, "");
    const dest = `${aiBase.replace(/\/$/, "")}${subpath}${search}`;
    return NextResponse.rewrite(new URL(dest));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/backend/:path*", "/assistant/:path*"],
};
