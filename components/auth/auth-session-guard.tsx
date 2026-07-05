"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { LoaderCircle } from "lucide-react";
import { useAuthEnforcement } from "@/components/auth/auth-enforcement";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";
import { useClientPathname } from "@/lib/hooks/use-client-pathname";
import { useHydrated } from "@/lib/hooks/use-hydrated";

const PUBLIC_PATHS = new Set(["/login", "/unauthorized"]);

function isSessionValid(session: {
  error?: string;
  accessToken?: string;
} | null): boolean {
  return Boolean(session?.accessToken && !session.error);
}

function AuthGateSpinner({ message }: { message: string }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 text-muted-foreground">
      <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden />
      <p className="text-sm">{message}</p>
    </div>
  );
}

export function AuthSessionGuard({ children }: { children: React.ReactNode }) {
  const t = useTranslations("auth");
  const router = useRouter();
  const pathname = useClientPathname();
  const hydrated = useHydrated();
  const enforceAuth = useAuthEnforcement();
  const { loading: authLoading } = usePlatformAuth();
  const { data: session, status } = useSession();
  const clearingSessionRef = useRef(false);

  const sessionError = session?.error;
  const accessToken = session?.accessToken;
  const isPublic = PUBLIC_PATHS.has(pathname);
  const sessionValid = isSessionValid(session);

  useEffect(() => {
    if (!hydrated || !pathname || isPublic || !enforceAuth || authLoading) {
      return;
    }

    if (status === "loading") {
      return;
    }

    if (status === "unauthenticated") {
      clearingSessionRef.current = false;
      const callback = encodeURIComponent(pathname);
      router.replace(`/login?callbackUrl=${callback}`);
      return;
    }

    if (status === "authenticated" && !sessionValid) {
      if (clearingSessionRef.current) {
        return;
      }
      clearingSessionRef.current = true;
      const callback = encodeURIComponent(pathname);
      void signOut({ redirectTo: `/login?callbackUrl=${callback}` });
    }
  }, [
    accessToken,
    authLoading,
    enforceAuth,
    hydrated,
    isPublic,
    pathname,
    router,
    sessionError,
    sessionValid,
    status,
  ]);

  if (isPublic || !enforceAuth) {
    return <>{children}</>;
  }

  if (!hydrated || !pathname || authLoading || status === "loading") {
    return <AuthGateSpinner message={t("checkingAuth")} />;
  }

  if (status === "unauthenticated" || !sessionValid) {
    return <AuthGateSpinner message={t("redirectingToSignIn")} />;
  }

  return <>{children}</>;
}
