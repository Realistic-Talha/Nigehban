"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield } from "lucide-react";
import { useLocale } from "@/providers/locale-provider";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { LocaleToggle } from "@/components/shell/LocaleToggle";
import { cn } from "@/lib/utils";

const links = [
  { href: "/check", key: "nav.check" },
  { href: "/feed", key: "nav.feed" },
  { href: "/dashboard", key: "nav.dashboard" },
  { href: "/about", key: "nav.about" },
] as const;

export function Nav() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-paper/90 backdrop-blur-md">
      <div className="container-wide flex h-14 items-center justify-between gap-4">
        <Link href="/" className="flex min-h-11 items-center gap-2 font-semibold text-ink">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-on-accent">
            <Shield className="h-3.5 w-3.5" aria-hidden />
          </span>
          Nigehban
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
          {links.map(({ href, key }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "min-h-11 rounded-full px-3 py-2 text-sm font-medium transition-colors",
                pathname === href || pathname.startsWith(href + "/")
                  ? "bg-accent-muted text-accent"
                  : "text-ink-muted hover:text-ink",
              )}
            >
              {t(key)}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle className="hidden sm:inline-flex" />
          <LocaleToggle />
          <Link href="/check/scam" className="btn-cta hidden sm:inline-flex !min-h-10 !px-4 !py-2 text-xs">
            {t("nav.cta")}
          </Link>
        </div>
      </div>
    </header>
  );
}
