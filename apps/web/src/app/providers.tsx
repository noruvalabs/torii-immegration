"use client";

import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth-context";
import { I18nProvider } from "@/lib/i18n";
import { CreditsProvider } from "@/lib/credits-context";
import { TopUpModal } from "@/components/credits/TopUpModal";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <I18nProvider>
        <AuthProvider>
          <CreditsProvider>
            {children}
            <TopUpModal />
          </CreditsProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
