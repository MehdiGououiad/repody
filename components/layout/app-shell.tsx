import { getTranslations } from "next-intl/server";
import { AccessProvider } from "@/components/auth/access-context";
import { AccountProvider } from "@/components/auth/account-context";
import { PlaygroundBanner, PlaygroundProvider } from "@/components/playground/playground";
import { Overlays } from "@/components/ui/overlays";
import { fetchAccess } from "@/lib/api/server";
import type { Account } from "@/lib/auth/account";
import { playgroundContact } from "@/lib/playground/config";
import { AppSidebar } from "./app-sidebar";
import { GlobalShortcuts } from "./global-shortcuts";
import { MobileNav } from "./mobile-nav";

/**
 * The inverted L: the sidebar sits on the canvas and recedes; the page sits on its own panel,
 * the brightest surface, where the work happens.
 */
export async function AppShell({
  account,
  children,
}: {
  account: Promise<Account | null>;
  children: React.ReactNode;
}) {
  const [t, access] = await Promise.all([getTranslations("common"), fetchAccess()]);
  return (
    <AccountProvider value={account}>
      <AccessProvider value={access}>
        <PlaygroundProvider contact={playgroundContact()}>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:start-3 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-overlay focus:px-3 focus:py-2 focus:text-sm focus:shadow-pop"
          >
            {t("skipToContent")}
          </a>
          <div className="flex h-dvh overflow-hidden bg-canvas">
            <AppSidebar />
            <div className="flex min-w-0 flex-1 flex-col md:py-1.5 md:pe-1.5">
              <MobileNav />
              <PlaygroundBanner />
              <main
                id="main-content"
                className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain bg-panel md:rounded-lg md:shadow-panel"
              >
                {children}
              </main>
            </div>
          </div>
          <GlobalShortcuts />
          <Overlays />
        </PlaygroundProvider>
      </AccessProvider>
    </AccountProvider>
  );
}
