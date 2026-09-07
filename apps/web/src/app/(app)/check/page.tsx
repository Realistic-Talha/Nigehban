"use client";

import Link from "next/link";
import { AlertTriangle, FileSearch, ImageIcon, ArrowRight } from "lucide-react";
import { useLocale } from "@/providers/locale-provider";

const tools = [
  {
    href: "/check/scam",
    titleKey: "home.scamTitle" as const,
    descKey: "home.scamDesc" as const,
    icon: AlertTriangle,
  },
  {
    href: "/check/fact",
    titleKey: "home.factTitle" as const,
    descKey: "home.factDesc" as const,
    icon: FileSearch,
  },
  {
    href: "/check/media",
    titleKey: "home.mediaTitle" as const,
    descKey: "home.mediaDesc" as const,
    icon: ImageIcon,
  },
];

export default function CheckHubPage() {
  const { t } = useLocale();

  return (
    <div className="page-shell max-w-3xl space-y-10">
      <div className="max-w-2xl">
        <p className="page-eyebrow">Product</p>
        <h1 className="page-title mt-2">Choose a check</h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
          Three tools, one pipeline. Pick the threat you want to verify.
        </p>
      </div>

      <div className="grid gap-4">
        {tools.map(({ href, titleKey, descKey, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="group app-card flex items-start gap-5 p-6 transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] bg-accent-muted text-accent">
              <Icon className="h-6 w-6" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="font-display text-2xl">{t(titleKey)}</h2>
              <p className="mt-1 text-sm text-ink-muted">{t(descKey)}</p>
            </div>
            <ArrowRight
              className="mt-2 h-5 w-5 text-ink-subtle transition group-hover:translate-x-1 group-hover:text-accent"
              aria-hidden
            />
          </Link>
        ))}
      </div>
    </div>
  );
}
