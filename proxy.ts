import { getSessionCookie } from "better-auth/cookies";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { backendOrigin, coreOrigin, fraudOrigin } from "@/lib/api/backend-origin";
import {
  acceptsWorkflowKey,
  isPublicApi,
  isPublicPage,
  safeCallbackUrl,
} from "@/lib/auth/public-paths";
import { accessToken, oidcEnabled } from "@/lib/auth/server";

type Token = Awaited<ReturnType<typeof accessToken>>;

// Requests that arrive together for one session share one token read: Keycloak rotates refresh
// tokens, so two parallel refreshes with the same one would end the session.
const inFlight = new Map<string, Promise<Token>>();

function sessionToken(request: NextRequest): Promise<Token> {
  const key = getSessionCookie(request);
  if (!key) return Promise.resolve(null);
  const pending =
    inFlight.get(key) ?? accessToken(request.headers).finally(() => inFlight.delete(key));
  inFlight.set(key, pending);
  return pending;
}

/** The request as the app sees it: refreshed session cookies, and the API token if given. */
function forwardedHeaders(request: NextRequest, token: Token, bearer: boolean): Headers {
  const headers = new Headers(request.headers);
  if (token?.setCookies.length) {
    const cookies = new Map(request.cookies.getAll().map((c) => [c.name, c.value]));
    for (const setCookie of token.setCookies) {
      const [pair = ""] = setCookie.split(";");
      const at = pair.indexOf("=");
      if (at > 0) cookies.set(pair.slice(0, at), pair.slice(at + 1));
    }
    headers.set("cookie", [...cookies].map(([name, value]) => `${name}=${value}`).join("; "));
  }
  if (bearer && token) headers.set("Authorization", `Bearer ${token.token}`);
  return headers;
}

/** The browser keeps the refreshed tokens too. */
function withCookies(response: NextResponse, token: Token): NextResponse {
  for (const setCookie of token?.setCookies ?? []) response.headers.append("set-cookie", setCookie);
  return response;
}

type UpstreamTarget = { origin: string; upstreamPath: string } | "unconfigured" | null;

function resolveUpstream(path: string): UpstreamTarget {
  if (path.startsWith("/api/core/v1/")) {
    const origin = coreOrigin();
    return origin ? { origin, upstreamPath: path.replace(/^\/api\/core/, "") } : "unconfigured";
  }
  if (path.startsWith("/api/fraud/v1/")) {
    const origin = fraudOrigin();
    return origin ? { origin, upstreamPath: path.replace(/^\/api\/fraud/, "") } : "unconfigured";
  }
  if (path.startsWith("/api/idp/v1/")) {
    return { origin: backendOrigin(), upstreamPath: path.replace(/^\/api\/idp/, "") };
  }
  if (path.startsWith("/api/v1/")) {
    return { origin: backendOrigin(), upstreamPath: path.replace(/^\/api/, "") };
  }
  return null;
}

/**
 * Multi-service runtime BFF proxy:
 * - `/api/core/v1/*` -> `repody-core` (`INTERNAL_CORE_API_URL`)
 * - `/api/fraud/v1/*` -> `repody-fraud` (`INTERNAL_FRAUD_API_URL`)
 * - `/api/idp/v1/*` and `/api/v1/*` -> `repody-idp` (`INTERNAL_API_URL`)
 */
function toBackend(request: NextRequest, headers?: Headers): NextResponse {
  const upstream = resolveUpstream(request.nextUrl.pathname);
  if (upstream === "unconfigured" || upstream === null) {
    return NextResponse.json({ detail: "Module service is not enabled." }, { status: 404 });
  }
  const target = new URL(`${upstream.upstreamPath}${request.nextUrl.search}`, upstream.origin);
  return NextResponse.rewrite(target, headers ? { request: { headers } } : undefined);
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const APP_ORIGIN = process.env.BETTER_AUTH_URL ? new URL(process.env.BETTER_AUTH_URL).origin : null;

/**
 * A change sent with the session cookie from another site (cross-site request forgery). The
 * session cookie is SameSite=Lax already; this also refuses what Lax lets through. Browsers
 * send Origin with every cross-origin request that changes something; requests without it
 * (servers, scripts with a workflow API key) are not a browser's and pass.
 */
function crossSite(request: NextRequest): boolean {
  if (SAFE_METHODS.has(request.method)) return false;
  const origin = request.headers.get("origin");
  if (!origin) return false;
  return origin !== request.nextUrl.origin && origin !== APP_ORIGIN;
}

function redirectToLogin(request: NextRequest): NextResponse {
  const login = new URL("/login", request.url);
  login.searchParams.set("callbackUrl", request.nextUrl.pathname);
  return NextResponse.redirect(login);
}

export default async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const isProxiedApi = resolveUpstream(path) !== null;
  if (!oidcEnabled) {
    return isProxiedApi ? toBackend(request) : NextResponse.next();
  }
  if (isPublicApi(path)) {
    return isProxiedApi ? toBackend(request) : NextResponse.next();
  }
  if (acceptsWorkflowKey(request.method, path) && request.headers.get("authorization")?.trim()) {
    return toBackend(request); // the caller's workflow API key, checked by the API
  }

  // Signed in means a session whose Keycloak token is still valid (or was just refreshed).
  const token = await sessionToken(request);

  if (!path.startsWith("/api/")) {
    if (path === "/login" && token) {
      const dest = safeCallbackUrl(request.nextUrl.searchParams.get("callbackUrl"));
      return withCookies(NextResponse.redirect(new URL(dest, request.url)), token);
    }
    if (!token && !isPublicPage(path)) return redirectToLogin(request);
    const headers = forwardedHeaders(request, token, false);
    return withCookies(NextResponse.next({ request: { headers } }), token);
  }

  if (!token) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  if (crossSite(request)) {
    console.warn(
      JSON.stringify({
        event: "cross_site_request_refused",
        path: request.nextUrl.pathname,
        origin: request.headers.get("origin"),
      }),
    );
    return NextResponse.json({ detail: "Cross-site request refused." }, { status: 403 });
  }
  return withCookies(toBackend(request, forwardedHeaders(request, token, true)), token);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
