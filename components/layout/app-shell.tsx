import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { AccountProvider } from "@/components/auth/account-context";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Account } from "@/lib/auth/account";
import { AppSidebar } from "./app-sidebar";
import { TopBar } from "./topbar";

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
      <TooltipProvider delayDuration={150}>
        <Link
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-card focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-foreground focus:shadow-md focus:ring-2 focus:ring-ring"
        >
          {t("skipToContent")}
        </Link>
        <div className="app-grain relative flex min-h-dvh bg-surface">
          <div className="app-mesh" aria-hidden />
          <AppSidebar />
          <div className="relative z-[1] flex min-w-0 max-w-full flex-1 flex-col md:ml-[248px]">
            <TopBar />
            <main id="main-content" className="flex-1 min-w-0 scroll-mt-16">
              {children}
            </main>
          </div>
        </div>
      </TooltipProvider>
    </AccountProvider>
  );
}
