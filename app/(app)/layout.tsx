import { headers } from "next/headers";
import { AppShell } from "@/components/layout/app-shell";
import { currentAccount } from "@/lib/auth/server";

/**
 * The signed-in pages. Access is checked by the proxy (optimistic) and by the Data Access Layer
 * on every API read (`lib/auth/dal.ts`); the layout only shows who is signed in. The account is
 * passed as a promise, so the shell streams without waiting for it.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell account={headers().then(currentAccount)}>{children}</AppShell>;
}
