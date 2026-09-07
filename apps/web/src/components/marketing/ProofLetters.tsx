"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";

const letters = [
  {
    name: "Intake",
    handle: "agent · classify",
    body: "Routes Urdu and English forwards so the right specialists run.",
    img: "/marketing/avatar1.jpg",
  },
  {
    name: "Pattern",
    handle: "agent · match",
    body: "Matches SBP, BISP, job, and OTP templates already seen in Pakistan.",
    img: "/marketing/avatar2.jpg",
  },
  {
    name: "Evidence",
    handle: "agent · ground",
    body: "Pulls curated and open sources before a claim is labeled.",
    img: "/marketing/avatar3.jpg",
  },
  {
    name: "Judge",
    handle: "agent · decide",
    body: "Low confidence stays unverified — no confident guessing.",
    img: "/marketing/avatar4.jpg",
  },
];

const benefits = [
  { title: "Private & careful", body: "Share only the verdict link you choose." },
  { title: "Works everywhere", body: "Browser-first. Paste from any chat." },
  { title: "Agent trail", body: "Every step logged for audit pages." },
  { title: "Bilingual", body: "English and Urdu with RTL layout." },
];

export function ProofLetters() {
  const reduce = useReducedMotion();

  return (
    <section className="px-3 py-3 sm:px-5 sm:py-5">
      <Reveal>
        <div className="mx-auto max-w-[1120px] overflow-hidden rounded-[40px] bg-[#141414] px-6 py-12 sm:rounded-[48px] sm:px-10 sm:py-16">
          <h2 className="font-display text-[clamp(2rem,4.5vw,3.5rem)] tracking-[-0.04em] text-[#fdfcf0]">
            Love letters to the pipeline.
          </h2>

          <div className="mt-10 flex gap-4 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {letters.map((l, i) => (
              <motion.article
                key={l.name}
                className="w-[270px] shrink-0 rounded-[28px] bg-[#fdfcf0] p-6 text-[#141414] sm:w-[290px]"
                initial={reduce ? false : { opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.08 * i, duration: 0.5 }}
                whileHover={reduce ? undefined : { y: -6, boxShadow: "0 16px 40px rgba(0,0,0,0.18)" }}
              >
                <div className="flex items-center gap-3">
                  <div className="relative h-10 w-10 overflow-hidden rounded-full">
                    <Image src={l.img} alt="" fill className="object-cover" sizes="40px" />
                  </div>
                  <div>
                    <p className="text-[14px] font-semibold">{l.name}</p>
                    <p className="text-[11px] text-[#8a8a8a]">{l.handle}</p>
                  </div>
                </div>
                <p className="mt-4 text-[14px] leading-relaxed text-[#5c5c5c]">{l.body}</p>
              </motion.article>
            ))}
          </div>

          <Stagger className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {benefits.map((b) => (
              <StaggerItem key={b.title}>
                <motion.div
                  whileHover={reduce ? undefined : { y: -4 }}
                  className="rounded-[22px] border border-white/10 bg-[#003e29] p-5 text-[#fdfcf0]"
                >
                  <span className="text-[#e5d4ff]" aria-hidden>
                    ↑
                  </span>
                  <p className="mt-2 font-display text-xl leading-tight">{b.title}</p>
                  <p className="mt-2 text-[12px] text-white/60">{b.body}</p>
                </motion.div>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </Reveal>
    </section>
  );
}
