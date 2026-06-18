"use client";

import type { ReactNode } from "react";
import { signOut } from "next-auth/react";
import { useTranslations } from "next-intl";
import { usePlatformAuth } from "@/lib/hooks/use-platform-auth";

type SignOutButtonProps = {
  className?: string;
  children: ReactNode;
  onSignedOut?: () => void;
};

export function SignOutButton({ className, children, onSignedOut }: SignOutButtonProps) {
  const t = useTranslations("auth");
  const { oidcEnabled, loading } = usePlatformAuth();

  if (loading) {
    return (
      <button type="button" className={className} disabled>
        {children}
      </button>
    );
  }

  if (!oidcEnabled) {
    return (
      <button
        type="button"
        className={className}
        disabled
        title={t("devModeHint")}
      >
        {children}
      </button>
    );
  }

  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        onSignedOut?.();
        void signOut({ redirectTo: "/login" });
      }}
    >
      {children}
    </button>
  );
}
