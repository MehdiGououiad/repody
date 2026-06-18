"use client";

import { SessionProvider } from "next-auth/react";
import type { ReactNode } from "react";

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  return (
    <SessionProvider refetchInterval={4 * 60} refetchOnWindowFocus refetchWhenOffline={false}>
      {children}
    </SessionProvider>
  );
}
