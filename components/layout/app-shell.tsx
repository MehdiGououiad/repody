"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { AppSidebar } from "./app-sidebar";
import { TopBar } from "./topbar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useClientPathname } from "@/lib/hooks/use-client-pathname";

const MINIMAL_LAYOUT_PATHS = new Set(["/login", "/unauthorized"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("common");
  const pathname = useClientPathname();
  const minimal = MINIMAL_LAYOUT_PATHS.has(pathname);

  if (minimal) {
    return <>{children}</>;
  }

  return (
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
  );
}
