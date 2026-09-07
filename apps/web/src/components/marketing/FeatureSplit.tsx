"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Reveal, easeOut } from "@/components/motion/Reveal";

export function FeatureSplit() {
  const [tab, setTab] = useState<"web" | "soon">("web");
  const reduce = useReducedMotion();

  return (
    <section className="bg-[#fdfcf0] px-5 py-14 sm:py-20">
      <div className="mx-auto max-w-[1120px]">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-[clamp(2.4rem,5vw,4rem)] tracking-[-0.04em] text-[#141414]">
            From paste to verdict.
          </h2>
          <div className="mt-6 inline-flex rounded-full border border-[#e4e1d4] bg-white p-1">
            {(
              [
                { id: "web" as const, label: "Web" },
                { id: "soon" as const, label: "WhatsApp (soon)" },
              ] as const
            ).map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setTab(p.id)}
                className={cn(
                  "relative min-h-10 rounded-full px-5 text-[13px] font-medium transition-colors",
                  tab === p.id ? "text-[#fdfcf0]" : "text-[#5c5c5c] hover:text-[#141414]",
                )}
              >
                {tab === p.id && (
                  <motion.span
                    layoutId="platform-pill"
                    className="absolute inset-0 rounded-full bg-[#141414]"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative z-10">{p.label}</span>
              </button>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.1} className="relative mx-auto mt-12 max-w-4xl overflow-hidden rounded-[32px] sm:rounded-[40px]">
          <motion.div
            className="relative aspect-[16/10] w-full"
            whileHover={reduce ? undefined : { scale: 1.02 }}
            transition={{ duration: 0.6, ease: easeOut }}
          >
            <Image
              src="/marketing/speed.jpg"
              alt="Outdoor landscape — paste to verdict"
              fill
              className="object-cover"
              sizes="(max-width: 896px) 100vw, 896px"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/35 via-transparent to-black/10" />
          </motion.div>

          <motion.div
            className="absolute bottom-5 left-1/2 w-[min(92%,360px)] -translate-x-1/2 rounded-[24px] border border-white/40 bg-[#fdfcf0]/95 p-4 shadow-[0_20px_50px_rgba(0,0,0,0.25)] backdrop-blur-md sm:bottom-8"
            initial={reduce ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.25, duration: 0.55, ease: easeOut }}
          >
            <div className="mb-2 flex items-end gap-0.5">
              {Array.from({ length: 24 }).map((_, i) => (
                <motion.span
                  key={i}
                  className="inline-block w-1 rounded-full bg-[#003e29]"
                  animate={
                    reduce
                      ? undefined
                      : { height: [6 + Math.sin(i * 0.7) * 8, 10 + Math.sin(i * 0.7 + 1) * 12, 6 + Math.sin(i * 0.7) * 8] }
                  }
                  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.04, ease: "easeInOut" }}
                  style={{ height: `${6 + Math.sin(i * 0.7) * 10}px` }}
                />
              ))}
            </div>
            <AnimatePresence mode="wait">
              <motion.p
                key={tab}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.25 }}
                className="text-[13px] leading-relaxed text-[#141414]"
              >
                {tab === "web"
                  ? "“SBP approved your loan. Send OTP to release funds…”"
                  : "WhatsApp delivery is on the roadmap — same agents, chat handoff."}
              </motion.p>
            </AnimatePresence>
            <div className="mt-3 flex items-center justify-between">
              <span className="rounded-full bg-[#e5d4ff] px-3 py-1 text-[11px] font-semibold text-[#1a1228]">
                Verdict ready
              </span>
              <Link href="/check/scam" className="text-[12px] font-semibold text-[#003e29]">
                Try it →
              </Link>
            </div>
          </motion.div>
        </Reveal>
      </div>
    </section>
  );
}
