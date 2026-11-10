"use client";

import { useTranslations } from "next-intl";
import { type ReactNode, Suspense } from "react";
import { useAccount } from "@/components/auth/account-context";
import { signOutToLogin } from "@/lib/auth/client";

type SignOutButtonProps = { className?: string; children: ReactNode; onSignedOut?: () => void };

/** Signs out; disabled without Keycloak sign-in (and while the account loads). */
export function SignOutButton(props: SignOutButtonProps) {
  return (
    <Suspense
      fallback={
        <button type="button" className={props.className} disabled>
          {props.children}
        </button>
      }
    >
      <AccountSignOutButton {...props} />
    </Suspense>
  );
}

function AccountSignOutButton({ className, children, onSignedOut }: SignOutButtonProps) {
  const t = useTranslations("auth");
  const account = useAccount();
  return (
    <button
      type="button"
      className={className}
      disabled={!account}
      title={account ? undefined : t("devModeHint")}
      onClick={() => {
        onSignedOut?.();
        void signOutToLogin();
      }}
    >
      {children}
    </button>
  );
}
