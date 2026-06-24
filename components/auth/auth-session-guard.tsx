"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { LoaderCircle } from "lucide-react";
import { useAuthEnforcement } from "@/components/auth/auth-enforcement";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";
import { useClientPathname } from "@/lib/hooks/use-client-pathname";

const PUBLIC_PATHS = new Set(["/login", "/unauthorized"]);

function isSessionValid(session: {
  error?: string;
  accessToken?: string;
} | null): boolean {
  return Boolean(session?.accessToken && !session.error);
}

export function AuthSessionGuard({ children }: { children: React.ReactNode }) {
  const t = useTranslations("auth");
  const router = useRouter();
  const pathname = useClientPathname();
  const enforceAuth = useAuthEnforcement();
  const { loading: authLoading } = usePlatformAuth();
  const { data: session, status } = useSession();

  const isPublic = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (isPublic || !enforceAuth || authLoading) {
      return;
    }

    if (status === "loading") {
      return;
    }

    if (status === "unauthenticated") {
      const callback = encodeURIComponent(pathname);
      router.replace(`/login?callbackUrl=${callback}`);
      return;
    }

    if (status === "authenticated" && !isSessionValid(session)) {
      const callback = encodeURIComponent(pathname);
      void signOut({ redirectTo: `/login?callbackUrl=${callback}` });
    }
  }, [
    authLoading,
    enforceAuth,
    isPublic,
    pathname,
    router,
    session,
    status,
  ]);

  if (isPublic || !enforceAuth) {
    return <>{children}</>;
  }

  if (authLoading || status === "loading") {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 text-muted-foreground">
        <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden />
        <p className="text-sm">{t("checkingAuth")}</p>
      </div>
    );
  }

  if (status === "unauthenticated" || !isSessionValid(session)) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center gap-3 text-muted-foreground">
        <LoaderCircle className="h-6 w-6 animate-spin" aria-hidden />
        <p className="text-sm">{t("redirectingToSignIn")}</p>
      </div>
    );
  }

  return <>{children}</>;
}
