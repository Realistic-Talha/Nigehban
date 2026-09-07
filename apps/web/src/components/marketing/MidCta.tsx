"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";

export function MidCta() {
  const reduce = useReducedMotion();

  return (
    <section className="px-3 py-3 sm:px-5 sm:py-5">
      <Reveal>
        <motion.div
          className="mx-auto max-w-[1120px] rounded-[40px] bg-[#e5d4ff] px-6 py-14 text-center sm:rounded-[48px] sm:px-12 sm:py-16"
          whileHover={reduce ? undefined : { scale: 1.005 }}
          transition={{ duration: 0.4 }}
        >
          <Stagger className="mb-6 flex flex-wrap items-center justify-center gap-2">
            {["Scam", "Fact", "Media", "Feed", "Share"].map((p) => (
              <StaggerItem key={p}>
                <span className="inline-flex min-h-9 items-center rounded-full border border-[#141414]/12 bg-[#fdfcf0]/60 px-3.5 text-[12px] font-medium text-[#141414]">
                  {p}
                </span>
              </StaggerItem>
            ))}
          </Stagger>
          <h2 className="font-display text-[clamp(2rem,4vw,3.25rem)] tracking-[-0.035em] text-[#141414]">
            Nigehban, wherever you share.
          </h2>
          <motion.div className="mt-8 inline-block" whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }}>
            <Link
              href="/check"
              className="inline-flex min-h-[44px] items-center rounded-full bg-[#141414] px-7 text-[13px] font-semibold text-[#fdfcf0]"
            >
              Open tools
            </Link>
          </motion.div>
        </motion.div>
      </Reveal>
    </section>
  );
}
