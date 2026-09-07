"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import en from "@/lib/i18n/en.json";
import ur from "@/lib/i18n/ur.json";

type Locale = "en" | "ur";
type Messages = typeof en;

const catalogs: Record<Locale, Messages> = { en, ur };

function resolve(obj: Record<string, unknown>, key: string): string {
  let cur: unknown = obj;
  for (const part of key.split(".")) {
    if (!cur || typeof cur !== "object") return key;
    cur = (cur as Record<string, unknown>)[part];
  }
  return typeof cur === "string" ? cur : key;
}

interface LocaleCtx {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const Ctx = createContext<LocaleCtx | null>(null);

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const stored = localStorage.getItem("nigehban-locale");
    if (stored === "en" || stored === "ur") setLocaleState(stored);
  }, []);

  useEffect(() => {
    const dir = locale === "ur" ? "rtl" : "ltr";
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
    localStorage.setItem("nigehban-locale", locale);
  }, [locale]);

  const setLocale = useCallback((l: Locale) => setLocaleState(l), []);
  const t = useCallback((key: string) => resolve(catalogs[locale] as unknown as Record<string, unknown>, key), [locale]);

  const value = useMemo(
    () => ({ locale, dir: locale === "ur" ? "rtl" as const : "ltr" as const, setLocale, t }),
    [locale, setLocale, t],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useLocale() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useLocale outside provider");
  return ctx;
}
