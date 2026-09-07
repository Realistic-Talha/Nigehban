"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, easeOut } from "@/components/motion/Reveal";

export function CloseBand() {
  const reduce = useReducedMotion();

  return (
    <section className="px-3 py-3 sm:px-5 sm:py-5">
      <Reveal>
        <div className="relative mx-auto max-w-[1120px] overflow-hidden rounded-[40px] sm:rounded-[48px]">
          <motion.div
            className="relative aspect-[16/9] min-h-[380px] w-full sm:min-h-[440px]"
            whileHover={reduce ? undefined : { scale: 1.03 }}
            transition={{ duration: 1.2, ease: easeOut }}
          >
            <Image src="/marketing/close.jpg" alt="" fill className="object-cover" sizes="1120px" />
            <div className="absolute inset-0 bg-black/45" />
          </motion.div>

          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 900 500"
            fill="none"
            aria-hidden
          >
            <motion.path
              d="M50 420 C 200 280, 280 80, 450 160 C 620 240, 700 90, 850 140"
              stroke="white"
              strokeOpacity="0.45"
              strokeWidth="1.5"
              strokeDasharray="3 10"
              strokeLinecap="round"
              initial={reduce ? false : { pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 1.8, ease: easeOut }}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
            <motion.h2
              className="font-display text-[clamp(2.75rem,7vw,5rem)] tracking-[-0.045em] text-white"
              initial={reduce ? false : { opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.65, ease: easeOut }}
            >
              Start verifying.
            </motion.h2>
            <motion.p
              className="mx-auto mt-4 max-w-md text-[15px] text-white/75"
              initial={reduce ? false : { opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.15, duration: 0.5 }}
            >
              Verify before you share — for yourself and everyone in the forward chain.
            </motion.p>
            <motion.div
              className="mt-9 flex flex-wrap items-center justify-center gap-3"
              initial={reduce ? false : { opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.25, duration: 0.5 }}
            >
              <motion.div whileHover={{ scale: 1.05, y: -2 }} whileTap={{ scale: 0.97 }}>
                <Link
                  href="/check/scam"
                  className="inline-flex min-h-[48px] items-center rounded-full bg-[#e5d4ff] px-7 text-[14px] font-semibold text-[#1a1228]"
                >
                  Download for free
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Link
                  href="/dashboard"
                  className="inline-flex min-h-[48px] items-center rounded-full border-[1.5px] border-white/70 px-7 text-[14px] font-semibold text-white"
                >
                  View pricing
                </Link>
              </motion.div>
            </motion.div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
