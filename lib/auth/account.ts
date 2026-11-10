/** The signed-in user as the app shell shows them (null when Keycloak sign-in is off). */
export type Account = { name: string | null; email: string | null; roles: string[] };

export function initials({ name, email }: Account): string {
  const source = (name?.trim() || email?.trim() || "?").replace(/@.+$/, "");
  const [first, second] = source.split(/\s+/).filter(Boolean);
  return (second ? `${first?.[0] ?? ""}${second[0]}` : source.slice(0, 2)).toUpperCase();
}
