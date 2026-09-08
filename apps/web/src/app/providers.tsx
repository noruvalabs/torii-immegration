"use client";

import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/lib/auth-context";
import { I18nProvider } from "@/lib/i18n";
import { CreditsProvider } from "@/lib/credits-context";
import { TopUpModal } from "@/components/credits/TopUpModal";
import { Toaster } from "@/components/ui/sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // Data remains fresh for 1 minute (instant tab transitions)
            gcTime: 5 * 60 * 1000, // Garbage collect unused queries after 5 minutes
            refetchOnWindowFocus: false, // Avoid refetching when window regains focus
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        <I18nProvider>
          <AuthProvider>
            <CreditsProvider>
              {children}
              <TopUpModal />
              <Toaster position="top-right" richColors />
            </CreditsProvider>
          </AuthProvider>
        </I18nProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

