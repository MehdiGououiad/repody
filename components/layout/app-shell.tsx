import { getTranslations } from "next-intl/server";
import { AccountProvider } from "@/components/auth/account-context";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Account } from "@/lib/auth/account";
import { AppSidebar } from "./app-sidebar";
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
  const t = await getTranslations("common");
  return (
    <AccountProvider value={account}>
      <TooltipProvider>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:start-3 focus:top-3 focus:z-[100] focus:rounded-md focus:bg-overlay focus:px-3 focus:py-2 focus:text-sm focus:shadow-pop"
        >
          {t("skipToContent")}
        </a>
        <div className="flex h-dvh overflow-hidden bg-canvas">
          <AppSidebar />
          <div className="flex min-w-0 flex-1 flex-col md:py-2 md:pe-2">
            <MobileNav />
            <main
              id="main-content"
              className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-panel md:rounded-lg md:shadow-panel"
            >
              {children}
            </main>
          </div>
        </div>
      </TooltipProvider>
    </AccountProvider>
  );
}
