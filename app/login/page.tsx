import { headers } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { StatusGlyph } from "@/components/ui/status-glyph";
import { safeCallbackUrl } from "@/lib/auth/public-paths";
import { auth, KEYCLOAK, oidcEnabled } from "@/lib/auth/server";
import { currentBrand } from "@/lib/theme/brand";

export async function generateMetadata() {
  return { title: (await getTranslations("auth"))("signIn") };
}

/** Sign-in: the brand, one sentence, one action. The credentials page itself is Keycloak's. */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const [{ callbackUrl, error }, t] = await Promise.all([searchParams, getTranslations("auth")]);
  const brand = currentBrand();
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
    <main className="flex min-h-dvh items-center justify-center bg-canvas px-4">
      <div className="flex w-full max-w-sm flex-col gap-6 pb-[10vh]">
        {brand.logoUrl ? (
          // biome-ignore lint/performance/noImgElement: a client's logo comes from any URL.
          <img src={brand.logoUrl} alt={brand.name} className="h-7 w-auto self-start" />
        ) : (
          <span
            aria-hidden
            className="flex size-8 items-center justify-center rounded-md bg-accent text-sm font-semibold text-on-accent"
          >
            {brand.name.slice(0, 1).toUpperCase()}
          </span>
        )}
        <div className="flex flex-col gap-1.5">
          <h1 className="text-xl font-semibold text-ink">
            {t("signInTitle", { name: brand.name })}
          </h1>
          <p className="text-sm text-ink-3">{t("signInSubtitle")}</p>
        </div>
        {errorKey ? (
          <p role="alert" className="flex items-start gap-2 text-sm text-fail-ink">
            <StatusGlyph status="failed" className="mt-0.5" />
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
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink-3">{t("devModeOnLogin")}</p>
            <Button asChild size="lg" className="w-full">
              <Link href={destination}>{t("continueToApp")}</Link>
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
