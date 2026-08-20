"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "ja";

const STORAGE_KEY = "torii-landing-lang";

const LangContext = createContext<{ lang: Lang; setLang: (lang: Lang) => void }>({
  lang: "en",
  setLang: () => {},
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const stored = window.localStorage.getItem("torii_lang") || window.localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "ja") {
      setLangState(stored);
      return;
    }
    if (navigator.language?.toLowerCase().startsWith("ja")) {
      setLangState("ja");
    }
  }, []);

  const setLang = (next: Lang) => {
    setLangState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    window.localStorage.setItem("torii_lang", next);
  };

  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export function useLang() {
  return useContext(LangContext);
}
