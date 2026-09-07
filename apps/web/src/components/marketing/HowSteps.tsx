"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";

const steps = [
  {
    n: "01",
    title: "Submit",
    body: "Paste a forward, upload a screenshot, or drop media.",
  },
  {
    n: "02",
    title: "Agents",
    body: "Specialized steps extract signals and ground evidence.",
  },
  {
    n: "03",
    title: "Share",
    body: "Send the verdict link back into the conversation.",
  },
];

export function HowSteps() {
  const reduce = useReducedMotion();

  return (
    <section className="bg-[#fdfcf0] px-5 py-12 sm:py-16">
      <div className="mx-auto max-w-[1120px]">
        <Reveal>
          <h2 className="font-display text-[clamp(2rem,4vw,3.25rem)] tracking-[-0.03em] text-[#141414]">
            How it works
          </h2>
        </Reveal>
        <Stagger className="mt-10 grid gap-4 sm:grid-cols-3">
          {steps.map((s) => (
            <StaggerItem key={s.n}>
              <motion.div
                whileHover={reduce ? undefined : { y: -6 }}
                className="rounded-[28px] border border-[#e4e1d4] bg-white p-6 sm:p-7"
              >
                <span className="font-display text-4xl text-[#003e29]/30">{s.n}</span>
                <h3 className="mt-3 font-display text-2xl text-[#141414]">{s.title}</h3>
                <p className="mt-2 text-[14px] text-[#5c5c5c]">{s.body}</p>
              </motion.div>
            </StaggerItem>
          ))}
        </Stagger>
        <Reveal delay={0.15} className="mt-8">
          <Link href="/about" className="text-[14px] font-semibold text-[#003e29] hover:underline">
            Read the methodology →
          </Link>
        </Reveal>
      </div>
    </section>
  );
}
