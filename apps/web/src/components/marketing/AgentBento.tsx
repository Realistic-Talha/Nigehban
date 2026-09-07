"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, Stagger, StaggerItem, easeOut } from "@/components/motion/Reveal";

const tags = [
  "WhatsApp forwards",
  "Job scams",
  "OTP phishing",
  "Viral claims",
  "Deepfakes",
  "Health rumors",
  "Finance fraud",
  "Election noise",
  "Family groups",
];

export function AgentBento() {
  const reduce = useReducedMotion();

  return (
    <section className="px-3 py-3 sm:px-5 sm:py-5">
      <Reveal>
        <div className="mx-auto max-w-[1120px] overflow-hidden rounded-[40px] bg-[#141414] px-6 py-12 sm:rounded-[48px] sm:px-12 sm:py-16">
          <div className="grid items-center gap-10 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <h2 className="font-display text-[clamp(2rem,4vw,3.25rem)] tracking-[-0.035em] text-[#fdfcf0]">
                Made for the way you forward.
              </h2>
              <Stagger className="mt-7 flex flex-wrap gap-2">
                {tags.map((t) => (
                  <StaggerItem key={t}>
                    <motion.span
                      whileHover={reduce ? undefined : { scale: 1.05, y: -2 }}
                      className="inline-flex min-h-9 items-center rounded-full border border-white/20 px-3.5 text-[12px] text-white/85"
                    >
                      {t}
                    </motion.span>
                  </StaggerItem>
                ))}
              </Stagger>
              <p className="mt-7 max-w-md text-[14px] leading-relaxed text-white/50">
                Nigehban lives in the browser — paste from any chat, get a shareable verdict you can
                send straight back into the thread.
              </p>
              <motion.div className="mt-8 inline-block" whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
                <Link
                  href="/about"
                  className="inline-flex min-h-[44px] items-center rounded-full bg-[#e5d4ff] px-6 text-[13px] font-semibold text-[#1a1228]"
                >
                  How it works
                </Link>
              </motion.div>
            </div>

            <motion.div
              className="relative mx-auto w-full max-w-sm overflow-hidden rounded-[28px] bg-[#1c1c1c] p-6 text-center"
              initial={reduce ? false : { opacity: 0, scale: 0.92 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, ease: easeOut }}
              whileHover={reduce ? undefined : { y: -6 }}
            >
              <div className="relative mx-auto h-36 w-36 overflow-hidden rounded-full">
                <Image src="/marketing/work.jpg" alt="" fill className="object-cover" sizes="144px" />
              </div>
              <span className="mt-4 inline-flex rounded-full bg-[#e5d4ff] px-3 py-1 text-[11px] font-bold text-[#1a1228]">
                4 agents
              </span>
              <p className="mt-3 font-display text-2xl text-[#fdfcf0]">One tool. Your chats.</p>
              <p className="mt-2 text-[13px] text-white/50">Intake · Pattern · Evidence · Judge</p>
            </motion.div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
