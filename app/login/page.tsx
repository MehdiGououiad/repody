"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn, signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthEnforcement } from "@/components/auth/auth-enforcement";
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

function safeCallbackUrl(raw: string | null): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) {
    return raw;
  }
  return "/dashboard";
}

function LoginContent() {
  const t = useTranslations("auth");
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = safeCallbackUrl(searchParams.get("callbackUrl"));
  const errorCode = searchParams.get("error");
  const { oidcEnabled, loading: authLoading } = usePlatformAuth();
  const enforceAuth = useAuthEnforcement();
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status !== "authenticated") return;
    if (session?.error || !session?.accessToken) {
      void signOut({ redirectTo: `/login?callbackUrl=${encodeURIComponent(callbackUrl)}` });
      return;
    }
    router.replace(callbackUrl);
  }, [status, session, callbackUrl, router]);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 px-4 text-muted-foreground">
        <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden />
        <p className="text-sm">{status === "authenticated" ? t("continueToApp") : t("checkingAuth")}</p>
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
        ) : !enforceAuth ? (
          <div className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">{t("devModeOnLogin")}</p>
            <Button asChild className="w-full" size="lg">
              <Link href="/dashboard">{t("continueToApp")}</Link>
            </Button>
          </div>
        ) : !oidcEnabled ? (
          <div className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">{t("authServiceStarting")}</p>
            <Button
              type="button"
              variant="outline"
              className="w-full"
              size="lg"
              onClick={() => window.location.reload()}
            >
              {t("retry")}
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            size="lg"
            className="w-full"
            onClick={() => signIn("keycloak", { redirectTo: callbackUrl })}
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
