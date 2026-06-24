"use client";

import { createContext, use } from "react";

const AuthEnforcementContext = createContext(false);

export function AuthEnforcementProvider({
  enforceAuth,
  children,
}: {
  enforceAuth: boolean;
  children: React.ReactNode;
}) {
  return (
    <AuthEnforcementContext value={enforceAuth}>{children}</AuthEnforcementContext>
  );
}

export function useAuthEnforcement(): boolean {
  return use(AuthEnforcementContext);
}
