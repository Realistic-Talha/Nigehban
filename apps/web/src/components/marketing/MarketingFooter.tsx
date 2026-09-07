"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, easeOut } from "@/components/motion/Reveal";

export function MarketingFooter() {
  const year = new Date().getFullYear();
  const reduce = useReducedMotion();

  return (
    <footer className="bg-[#fdfcf0] pt-6 sm:pt-10">
      <div className="px-3 sm:px-5">
        <Reveal>
          <div className="mx-auto flex max-w-[1120px] flex-col items-start justify-between gap-5 rounded-[28px] border border-[#e4e1d4] bg-[#f7f5e8] px-6 py-7 sm:flex-row sm:items-center sm:px-10">
            <div>
              <p className="font-display text-2xl tracking-tight text-[#141414] sm:text-3xl">
                Take Nigehban with you
              </p>
              <p className="mt-1 text-[14px] text-[#5c5c5c]">
                Web today. Chat delivery on the roadmap.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  { href: "/check/scam", label: "Check scam", solid: true },
                  { href: "/check/fact", label: "Fact check", solid: false },
                  { href: "/check/media", label: "Media check", solid: false },
                ] as const
              ).map((b) => (
                <motion.div key={b.href} whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}>
                  <Link
                    href={b.href}
                    className={
                      b.solid
                        ? "inline-flex min-h-10 items-center rounded-full bg-[#e5d4ff] px-5 text-[13px] font-semibold text-[#1a1228]"
                        : "inline-flex min-h-10 items-center rounded-full border border-[#141414] px-5 text-[13px] font-semibold text-[#141414]"
                    }
                  >
                    {b.label}
                  </Link>
                </motion.div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>

      <div className="mx-auto max-w-[1120px] px-5 py-12">
        <Reveal>
          <div className="grid gap-10 sm:grid-cols-3">
            {(
              [
                {
                  title: "Company",
                  items: [
                    { href: "/about", label: "About" },
                    { href: "/privacy", label: "Privacy" },
                    { href: "/terms", label: "Terms" },
                  ],
                },
                {
                  title: "Product",
                  items: [
                    { href: "/check", label: "Tools" },
                    { href: "/feed", label: "Feed" },
                    { href: "/dashboard", label: "Dashboard" },
                  ],
                },
                {
                  title: "Resources",
                  items: [
                    { href: "/about", label: "Methodology" },
                    { href: "#", label: "API docs — soon" },
                  ],
                },
              ] as const
            ).map((col) => (
              <div key={col.title}>
                <p className="text-[12px] font-semibold uppercase tracking-[0.14em] text-[#8a8a8a]">
                  {col.title}
                </p>
                <ul className="mt-4 space-y-2.5 text-[14px] text-[#5c5c5c]">
                  {col.items.map((item) => (
                    <li key={item.label}>
                      {item.href === "#" ? (
                        <span className="text-[#8a8a8a]">{item.label}</span>
                      ) : (
                        <Link href={item.href} className="hover:text-[#141414]">
                          {item.label}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Reveal>

        <div className="mt-16 overflow-hidden border-t border-[#e4e1d4] pt-10">
          <motion.div
            className="flex items-end gap-4 sm:gap-5"
            initial={reduce ? false : { opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: easeOut }}
          >
            <div className="mb-3 flex gap-2.5" aria-hidden>
              {[0, 1, 2, 3].map((i) => (
                <motion.span
                  key={i}
                  className="h-3.5 w-3.5 rounded-full bg-[#141414] sm:h-4 sm:w-4"
                  initial={reduce ? false : { scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.1 * i, type: "spring", stiffness: 400, damping: 18 }}
                />
              ))}
            </div>
            <p className="select-none font-body text-[clamp(3rem,14vw,9rem)] font-bold leading-[0.82] tracking-[-0.055em] text-[#141414]">
              Nigehban
            </p>
          </motion.div>
          <p className="mt-1 font-display text-2xl text-[#8a8a8a] sm:text-3xl" dir="rtl">
            نگہبان
          </p>
        </div>

        <div className="mt-8 flex flex-col gap-2 text-[12px] text-[#8a8a8a] sm:flex-row sm:justify-between">
          <p>© {year} Nigehban. Verify before you share.</p>
          <p>Built for Pakistan.</p>
        </div>
      </div>
    </footer>
  );
}
