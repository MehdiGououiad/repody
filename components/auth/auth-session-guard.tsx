"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useRef } from "react";
import { useAuthEnforcement } from "@/components/auth/auth-enforcement";
import { isPublicPage } from "@/lib/auth/public-paths";
import { useClientPathname } from "@/lib/hooks/use-client-pathname";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";

function AuthGateSpinner({ message }: { message: string }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-3 text-muted-foreground">
      <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden />
      <p className="text-sm">{message}</p>
    </div>
  );
}

/**
 * Client-side session error / unauthenticated recovery.
 * Proxy already gates pages — do not block the shell behind a hydration spinner.
 */
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
  // Empty pathname = pre-hydration snapshot from useClientPathname — do not gate.
  const isPublic = !pathname || isPublicPage(pathname);
  const redirecting =
    !isPublic &&
    enforceAuth &&
    hydrated &&
    Boolean(pathname) &&
    !authLoading &&
    status !== "loading" &&
    (status === "unauthenticated" || Boolean(sessionError));

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

    if (status === "authenticated" && sessionError) {
      if (clearingSessionRef.current) {
        return;
      }
      clearingSessionRef.current = true;
      const callback = encodeURIComponent(pathname);
      void signOut({ redirectTo: `/login?callbackUrl=${callback}` });
    }
  }, [authLoading, enforceAuth, hydrated, isPublic, pathname, router, sessionError, status]);

  if (isPublic || !enforceAuth) {
    return <>{children}</>;
  }

  // Proxy already authenticated the page; keep rendering while session hydrates.
  // Spinner only once we know we are redirecting away.
  if (redirecting) {
    return <AuthGateSpinner message={t("redirectingToSignIn")} />;
  }

  return <>{children}</>;
}
