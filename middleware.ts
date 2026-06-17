import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { auth, isOidcConfigured } from "@/auth";

const PUBLIC_PREFIXES = ["/login", "/unauthorized", "/api/auth", "/api/v1/healthz"];

function isPublicPath(path: string): boolean {
  return PUBLIC_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

/** Deployed workflow run API — workflow API key when client sends Bearer; else session JWT for builder test runs. */
const WORKFLOW_RUN_API = /^\/api\/v1\/workflows\/[^/]+\/runs(?:\/json)?$/;

function isWorkflowRunApi(path: string): boolean {
  return WORKFLOW_RUN_API.test(path);
}

function hasCallerBearer(request: { headers: Headers }): boolean {
  return Boolean(request.headers.get("authorization")?.trim());
}

function forwardWithSessionBearer(
  request: { auth?: { accessToken?: string | null } | null; headers: Headers }
): NextResponse {
  const accessToken = request.auth?.accessToken;
  if (!accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export default auth((request) => {
  const path = request.nextUrl.pathname;

  if (!isOidcConfigured()) {
    return NextResponse.next();
  }

  if (isPublicPath(path)) {
    return NextResponse.next();
  }

  if (path.startsWith("/api/v1/")) {
    if (isWorkflowRunApi(path) && hasCallerBearer(request)) {
      return NextResponse.next();
    }
    return forwardWithSessionBearer(request);
  }

  if (path.startsWith("/api/")) {
    return forwardWithSessionBearer(request);
  }

  if (!request.auth) {
    const loginUrl = new URL("/login", request.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", path);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
