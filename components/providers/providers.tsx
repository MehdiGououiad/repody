"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import type { ReactNode } from "react";
import { TimeZoneSync } from "@/components/providers/time-zone-sync";
import { getQueryClient } from "@/lib/query/get-query-client";

/** Client-side providers: TanStack Query, the theme (next-themes) and URL state (nuqs). */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={getQueryClient()}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <NuqsAdapter>
          <TimeZoneSync />
          {children}
        </NuqsAdapter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
