import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Inject the admin API token for browser → backend rewrites on UI routes.
 * `/api/v1/*` is the public workflow API surface — keep the client's Bearer
 * (workflow key) so the API panel and copied curl examples work through :3000.
 * Token stays server-side (AUDIT_ADMIN_API_TOKEN is not NEXT_PUBLIC_*).
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
