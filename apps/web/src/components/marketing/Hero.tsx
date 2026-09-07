"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { easeOut } from "@/components/motion/Reveal";

export function Hero() {
  const reduce = useReducedMotion();

  return (
    <section className="relative overflow-hidden bg-[#fdfcf0] pb-6 pt-10 sm:pb-10 sm:pt-16">
      <svg
        className="pointer-events-none absolute left-0 top-0 h-[70%] w-full max-w-none"
        viewBox="0 0 1440 520"
        fill="none"
        aria-hidden
        preserveAspectRatio="none"
      >
        <motion.path
          d="M40 20 C 180 80, 140 200, 300 160 C 460 120, 400 280, 560 250 C 740 215, 680 380, 860 340 C 1020 305, 980 430, 1140 400 C 1260 380, 1300 460, 1400 500"
          stroke="#141414"
          strokeOpacity="0.22"
          strokeWidth="1.6"
          strokeDasharray="2.5 9"
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 2.4, ease: easeOut }}
        />
      </svg>

      <div className="relative mx-auto max-w-[720px] px-5 text-center">
        <motion.h1
          className="font-display text-[clamp(3rem,8vw,5.75rem)] leading-[1.02] tracking-[-0.04em] text-[#141414]"
          initial={reduce ? false : { opacity: 0, y: 22 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, ease: easeOut }}
        >
          Don&apos;t guess, just verify
        </motion.h1>
        <motion.p
          className="mx-auto mt-6 max-w-[28rem] text-[15px] leading-[1.65] text-[#5c5c5c]"
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, delay: 0.12, ease: easeOut }}
        >
          Check scams, viral claims, and synthetic media with an agent pipeline built for Pakistani
          forwards — then send the verdict back into the chat.
        </motion.p>
        <motion.div
          className="mt-9 flex flex-wrap items-center justify-center gap-3"
          initial={reduce ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.22, ease: easeOut }}
        >
          <motion.div whileHover={{ scale: 1.04, y: -2 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/check/scam"
              className="inline-flex min-h-[48px] items-center rounded-full bg-[#e5d4ff] px-7 text-[14px] font-semibold text-[#1a1228] transition hover:bg-[#d9c2ff]"
            >
              Download for free
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/feed"
              className="inline-flex min-h-[48px] items-center rounded-full border-[1.5px] border-[#003e29] px-7 text-[14px] font-semibold text-[#003e29] transition hover:bg-[#003e29] hover:text-[#fdfcf0]"
            >
              Join the feed
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
