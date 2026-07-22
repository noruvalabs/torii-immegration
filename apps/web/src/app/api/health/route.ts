import { NextResponse } from "next/server";

// Container/uptime probe for the web service (the Docker HEALTHCHECK hits this).
export async function GET() {
  return NextResponse.json({ status: "ok", service: "web" });
}
