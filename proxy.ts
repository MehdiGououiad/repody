import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { auth, isOidcConfigured } from "@/auth";
import { backendOrigin } from "@/lib/api/backend-origin";
import { isPublicApi, isPublicPage } from "@/lib/auth/public-paths";

/** The run API also accepts a workflow API key, which the caller sends itself. */
const WORKFLOW_RUN_PATH = /^\/api\/v1\/workflows\/[^/]+\/runs$/;

/**
 * Browser `/api/v1/*` -> FastAPI `/v1/*`. A proxy rewrite to the runtime backend origin
 * (INTERNAL_API_URL), so the same web image works on Compose and Kubernetes.
 */
function toBackend(request: NextRequest, headers?: Headers): NextResponse {
  const target = new URL(
    `${request.nextUrl.pathname.replace(/^\/api/, "")}${request.nextUrl.search}`,
    backendOrigin()
  );
  return NextResponse.rewrite(target, headers ? { request: { headers } } : undefined);
}

function redirectToLogin(request: NextRequest): NextResponse {
  const login = new URL("/login", request.url);
  login.searchParams.set("callbackUrl", request.nextUrl.pathname);
  return NextResponse.redirect(login);
}

export default auth(async (request) => {
  const path = request.nextUrl.pathname;
  if (!isOidcConfigured()) {
    return path.startsWith("/api/v1/") ? toBackend(request) : NextResponse.next();
  }
  // The token Auth.js just refreshed (reading the cookie again would race a second refresh).
  const session = request.auth?.error ? null : request.auth;
  const token = session?.accessToken;

  if (!path.startsWith("/api/")) {
    const signedIn = Boolean(session?.user);
    if (path === "/login" && signedIn) {
      const callback = request.nextUrl.searchParams.get("callbackUrl");
      const dest =
        callback?.startsWith("/") && !callback.startsWith("//") ? callback : "/dashboard";
      return NextResponse.redirect(new URL(dest, request.url));
    }
    return isPublicPage(path) || signedIn ? NextResponse.next() : redirectToLogin(request);
  }

  if (isPublicApi(path)) {
    return path.startsWith("/api/v1/") ? toBackend(request) : NextResponse.next();
  }
  if (WORKFLOW_RUN_PATH.test(path) && request.headers.get("authorization")?.trim()) {
    return toBackend(request); // the caller's workflow API key
  }
  if (!token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return toBackend(request, headers);
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
