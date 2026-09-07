"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { LocaleToggle } from "@/components/shell/LocaleToggle";
import { cn } from "@/lib/utils";
import { easeOut } from "@/components/motion/Reveal";

const links = [
  { href: "/check", label: "Product" },
  { href: "/feed", label: "Feed" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/about", label: "About" },
  { href: "/check", label: "Connect" },
];

function BrandMark({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("group flex items-center gap-2.5 text-ink", className)}>
      {/* Flow-style four dots */}
      <span className="flex items-center gap-[5px]" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <motion.span
            key={i}
            className="h-[7px] w-[7px] rounded-full bg-ink"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.05 * i, duration: 0.35, ease: easeOut }}
          />
        ))}
      </span>
      <span className="text-[15px] font-semibold tracking-[-0.03em] transition-opacity group-hover:opacity-70">
        Nigehban
      </span>
    </Link>
  );
}

export function MarketingNav() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const reduce = useReducedMotion();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <motion.header
      initial={reduce ? false : { y: -16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.55, ease: easeOut }}
      className={cn(
        "sticky top-0 z-50 transition-[background,box-shadow,backdrop-filter] duration-300",
        scrolled
          ? "bg-[#fdfcf0]/80 shadow-[0_1px_0_rgba(20,20,20,0.06)] backdrop-blur-xl"
          : "bg-[#fdfcf0]/0",
      )}
    >
      <div className="relative mx-auto flex h-[72px] w-full max-w-[1180px] items-center justify-between px-5 sm:px-8">
        <BrandMark />

        <nav
          className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 items-center gap-0.5 lg:flex"
          aria-label="Main"
        >
          {links.map((l) => {
            const active =
              l.label !== "Connect" &&
              (pathname === l.href || pathname.startsWith(l.href + "/"));
            return (
              <Link
                key={`${l.label}-${l.href}`}
                href={l.href}
                className={cn(
                  "relative rounded-full px-3.5 py-2 text-[13px] font-medium tracking-[-0.01em] transition-colors",
                  active ? "text-ink" : "text-[#6b6b6b] hover:text-ink",
                )}
              >
                {l.label}
                {active && (
                  <motion.span
                    layoutId="nav-dot"
                    className="absolute inset-x-3 -bottom-0.5 mx-auto h-[3px] w-1 rounded-full bg-ink"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-2.5">
          <div className="hidden sm:block">
            <LocaleToggle />
          </div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/check/scam"
              className="inline-flex h-10 items-center rounded-full bg-[#e5d4ff] px-5 text-[13px] font-semibold text-[#1a1228] shadow-[0_1px_0_rgba(0,0,0,0.04)] transition hover:bg-[#d9c2ff]"
            >
              Get Nigehban
            </Link>
          </motion.div>
          <button
            type="button"
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/80 bg-white/60 lg:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: easeOut }}
            className="overflow-hidden border-t border-border/50 bg-[#fdfcf0] lg:hidden"
          >
            <div className="flex flex-col gap-1 px-5 py-4">
              {links.map((l, i) => (
                <motion.div
                  key={`${l.label}-m`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.04 * i }}
                >
                  <Link
                    href={l.href}
                    className="block rounded-2xl px-4 py-3 text-[15px] font-medium text-ink hover:bg-paper-2"
                  >
                    {l.label}
                  </Link>
                </motion.div>
              ))}
              <div className="mt-2 px-4 pb-2 sm:hidden">
                <LocaleToggle />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
