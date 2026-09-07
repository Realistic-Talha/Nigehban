"use client";

import Link from "next/link";
import { useLocale } from "@/providers/locale-provider";

export function Footer() {
  const { t } = useLocale();
  const year = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-border bg-paper-2">
      <div className="container-wide flex flex-col gap-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-ink-muted">{t("footer.tagline")}</p>
        <nav className="flex flex-wrap gap-4 text-sm" aria-label="Footer">
          <Link href="/about" className="min-h-11 inline-flex items-center text-ink-muted hover:text-ink">
            {t("footer.about")}
          </Link>
          <Link href="/privacy" className="min-h-11 inline-flex items-center text-ink-muted hover:text-ink">
            {t("footer.privacy")}
          </Link>
          <Link href="/terms" className="min-h-11 inline-flex items-center text-ink-muted hover:text-ink">
            {t("footer.terms")}
          </Link>
        </nav>
        <p className="text-xs text-ink-subtle">© {year} Nigehban</p>
      </div>
    </footer>
  );
}
