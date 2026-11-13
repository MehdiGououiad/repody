/**
 * Demo mode (the public playground, its own deployment): no sign-in; each browser is an
 * anonymous visitor, named by a random id in a cookie. The proxy sends it to the API, which
 * shows the visitor the shared examples and their own workflows only (backend `api/deps.py`).
 */
export const demoMode = process.env.AUDIT_DEMO_MODE === "true";

export const VISITOR_COOKIE = "repody_visitor";
export const VISITOR_HEADER = "X-Repody-Visitor";
/** The API deletes a visitor's workflows after 14 days unedited; the cookie outlives them. */
export const VISITOR_COOKIE_SECONDS = 30 * 24 * 60 * 60;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The visitor id a cookie holds, or null when it is missing or not one we issued. */
export function visitorId(cookie: string | undefined): string | null {
  return cookie && UUID.test(cookie) ? cookie : null;
}
