import { type NextRequest, NextResponse } from "next/server";
import { safeCallbackUrl } from "@/lib/auth/public-paths";
import { auth, oidcEnabled } from "@/lib/auth/server";

/**
 * Ends the session and goes to the login page. Server Components land here when the API refuses
 * their token (they cannot clear cookies themselves); `callbackUrl` is where to return after.
 */
export async function GET(request: NextRequest) {
  const login = new URL("/login", request.url);
  login.searchParams.set(
    "callbackUrl",
    safeCallbackUrl(request.nextUrl.searchParams.get("callbackUrl"))
  );
  const response = NextResponse.redirect(login);
  if (!oidcEnabled) return response;
  const { headers } = await auth.api
    .signOut({ headers: request.headers, returnHeaders: true })
    .catch(() => ({ headers: new Headers() }));
  for (const setCookie of headers.getSetCookie()) response.headers.append("set-cookie", setCookie);
  return response;
}
