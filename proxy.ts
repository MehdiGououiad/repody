import { NextResponse } from "next/server";
import { auth, isOidcConfigured } from "@/auth";
import { isPublicApi } from "@/lib/auth/public-paths";

/** Workflow run API: caller Bearer means workflow API key; otherwise use the UI session JWT for builder test runs. */
const WORKFLOW_RUN_API = /^\/api\/v1\/workflows\/[^/]+\/runs(?:\/json)?$/;

function isWorkflowRunApi(path: string): boolean {
  return WORKFLOW_RUN_API.test(path);
}

function hasCallerBearer(request: { headers: Headers }): boolean {
  return Boolean(request.headers.get("authorization")?.trim());
}

function forwardWithSessionBearer(
  request: { auth?: { accessToken?: string | null; error?: string | null } | null; headers: Headers }
): NextResponse {
  const accessToken = request.auth?.accessToken;
  if (!accessToken || request.auth?.error) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export default auth((request) => {
  if (!isOidcConfigured()) {
    return NextResponse.next();
  }

  const path = request.nextUrl.pathname;

  if (!path.startsWith("/api/")) {
    return NextResponse.next();
  }

  if (isPublicApi(path)) {
    return NextResponse.next();
  }

  if (path.startsWith("/api/v1/")) {
    if (isWorkflowRunApi(path) && hasCallerBearer(request)) {
      return NextResponse.next();
    }
    return forwardWithSessionBearer(request);
  }

  return forwardWithSessionBearer(request);
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
