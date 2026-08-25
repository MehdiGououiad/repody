import "server-only";

import { auth } from "@/auth";

/** RSC / Route Handlers: Keycloak access token from the Auth.js session. */
export async function getServerAccessToken(): Promise<string | undefined> {
  const session = await auth();
  if (!session || session.error) {
    return undefined;
  }
  const accessToken = session.accessToken;
  return typeof accessToken === "string" && accessToken.length > 0 ? accessToken : undefined;
}
