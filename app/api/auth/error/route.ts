import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Send Auth.js error callbacks to the login page with the error query preserved. */
export function GET(request: NextRequest) {
  const login = new URL("/login", request.url);
  for (const [key, value] of request.nextUrl.searchParams) {
    login.searchParams.set(key, value);
  }
  return NextResponse.redirect(login);
}
