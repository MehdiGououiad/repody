import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { auth, isOidcConfigured } from "@/auth";
import { resolveAuthCredential } from "@/lib/api/auth-policy";
import { getRequestAccessToken } from "@/lib/auth/access-token";
import { isPublicApi, isPublicPage } from "@/lib/auth/public-paths";

function hasCallerBearer(request: { headers: Headers }): boolean {
  return Boolean(request.headers.get("authorization")?.trim());
}

async function forwardWithSessionBearer(
  request: NextRequest & {
    auth?: {
      accessToken?: string | null;
      error?: string | null;
    } | null;
  }
): Promise<NextResponse> {
  if (request.auth?.error) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const accessToken = getRequestAccessToken(request);
  if (!accessToken) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

function redirectToLogin(request: { nextUrl: URL; url: string }): NextResponse {
  const login = new URL("/login", request.url);
  const path = request.nextUrl.pathname;
  if (path && path !== "/login") {
    login.searchParams.set("callbackUrl", path);
  }
  return NextResponse.redirect(login);
}

function hasValidSession(
  auth: {
    user?: unknown;
    error?: string | null;
  } | null
): boolean {
  return Boolean(auth?.user && !auth?.error);
}

export default auth(async (request) => {
  if (!isOidcConfigured()) {
    return NextResponse.next();
  }

  const path = request.nextUrl.pathname;

  if (!path.startsWith("/api/")) {
    const signedIn = hasValidSession(request.auth);
    if (path === "/login" && signedIn) {
      const callback = request.nextUrl.searchParams.get("callbackUrl");
      const dest =
        callback?.startsWith("/") && !callback.startsWith("//") ? callback : "/dashboard";
      return NextResponse.redirect(new URL(dest, request.url));
    }
    if (!isPublicPage(path) && !signedIn) {
      return redirectToLogin(request);
    }
    return NextResponse.next();
  }

  if (isPublicApi(path)) {
    return NextResponse.next();
  }

  if (path.startsWith("/api/v1/")) {
    // Workflow run API: a caller Bearer is the workflow API key; otherwise use the session JWT.
    if (resolveAuthCredential(path) === "workflow" && hasCallerBearer(request)) {
      return NextResponse.next();
    }
    return forwardWithSessionBearer(request);
  }

  return forwardWithSessionBearer(request);
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
