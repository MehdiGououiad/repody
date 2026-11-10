import { ShieldCheck } from "lucide-react";
import { headers } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { safeCallbackUrl } from "@/lib/auth/public-paths";
import { auth, KEYCLOAK, oidcEnabled } from "@/lib/auth/server";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const [{ callbackUrl, error }, t] = await Promise.all([searchParams, getTranslations("auth")]);
  const destination = safeCallbackUrl(callbackUrl);
  // Better Auth sends sign-in failures here as `?error=<code>` (the proxy sends signed-in
  // visitors on to `callbackUrl`).
  const errorKey = !error ? null : error === "access_denied" ? "errorAccessDenied" : "errorOAuth";

  async function signInWithKeycloak() {
    "use server";
    const { url } = await auth.api.signInSocial({
      body: { provider: KEYCLOAK, callbackURL: destination, errorCallbackURL: "/login" },
      headers: await headers(),
    });
    if (!url) throw new Error("Keycloak sign-in did not return an authorization URL.");
    redirect(url);
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center px-4 py-12">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        aria-hidden
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(196,163,90,0.22), transparent 60%)",
        }}
      />
      <div className="relative w-full max-w-md rounded-2xl border border-border/80 bg-card/90 p-8 shadow-xl backdrop-blur-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-accent-blue/15 ring-1 ring-accent-blue/25 text-accent-blue shadow-[0_0_32px_-8px_var(--accent-blue-glow)]">
            <ShieldCheck className="h-7 w-7" aria-hidden />
          </div>
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{t("signInTitle")}</h1>
            <p className="text-sm text-muted-foreground">{t("signInSubtitle")}</p>
          </div>
        </div>

        {errorKey ? (
          <p
            role="alert"
            className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-center text-sm text-destructive"
          >
            {t(errorKey)}
          </p>
        ) : null}

        {oidcEnabled ? (
          <form action={signInWithKeycloak}>
            <Button type="submit" size="lg" className="w-full">
              {t("continueWithKeycloak")}
            </Button>
          </form>
        ) : (
          <div className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">{t("devModeOnLogin")}</p>
            <Button asChild className="w-full" size="lg">
              <Link href={destination}>{t("continueToApp")}</Link>
            </Button>
          </div>
        )}

        <p className="mt-6 text-center text-xs text-muted-foreground">{t("keycloakHint")}</p>
      </div>
    </div>
  );
}
