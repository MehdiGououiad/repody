"use client";

import { Suspense } from "react";
import Link from "next/link";
import { signIn, useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";

const ERROR_KEYS: Record<string, string> = {
  Configuration: "errorConfiguration",
  AccessDenied: "errorAccessDenied",
  Verification: "errorVerification",
  OAuthSignin: "errorOAuth",
  OAuthCallback: "errorOAuth",
  OAuthAccountNotLinked: "errorOAuth",
  Callback: "errorOAuth",
  Default: "errorDefault",
};

function LoginContent() {
  const t = useTranslations("auth");
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") ?? "/dashboard";
  const errorCode = searchParams.get("error");
  const { oidcEnabled, keycloakConfigured, loading: authLoading } = usePlatformAuth();
  const { status } = useSession();

  if (status === "authenticated") {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-4 px-4">
        <p className="text-sm text-muted-foreground">{t("alreadySignedIn")}</p>
        <Button asChild>
          <Link href={callbackUrl.startsWith("/") ? callbackUrl : "/dashboard"}>{t("continueToApp")}</Link>
        </Button>
      </div>
    );
  }

  const errorKey = errorCode ? (ERROR_KEYS[errorCode] ?? ERROR_KEYS.Default) : null;

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
          <p className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-center text-sm text-destructive">
            {t(errorKey)}
          </p>
        ) : null}

        {authLoading ? (
          <p className="text-center text-sm text-muted-foreground">{t("checkingAuth")}</p>
        ) : !keycloakConfigured ? (
          <div className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">{t("devModeOnLogin")}</p>
            <Button asChild className="w-full" size="lg">
              <Link href="/dashboard">{t("continueToApp")}</Link>
            </Button>
          </div>
        ) : !oidcEnabled ? (
          <div className="space-y-4 text-center">
            <p className="text-sm text-destructive">{t("keycloakNotRunning")}</p>
            <Button asChild className="w-full" size="lg" variant="outline">
              <Link href="/dashboard">{t("continueToApp")}</Link>
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => signIn("keycloak", { callbackUrl })}
          >
            {t("continueWithKeycloak")}
          </Button>
        )}

        <p className="mt-6 text-center text-xs text-muted-foreground">{t("keycloakHint")}</p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const t = useTranslations("auth");
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center text-sm text-muted-foreground">
          {t("checkingAuth")}
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
