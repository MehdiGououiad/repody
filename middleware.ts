import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Inject the admin API token for browser → backend rewrites on UI routes.
 * Credential rules are documented in `lib/api/auth-policy.ts`.
 * `/api/v1/*` keeps the client's Bearer (workflow key).
 */
export function middleware(request: NextRequest) {
  const token = process.env.AUDIT_ADMIN_API_TOKEN;
  const path = request.nextUrl.pathname;
  if (!token || !path.startsWith("/api/") || path.startsWith("/api/v1/")) {
    return NextResponse.next();
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Authorization", `Bearer ${token}`);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: "/api/:path*",
};
