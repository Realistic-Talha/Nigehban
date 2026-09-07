"use client";

import Link from "next/link";
import {
  MessageCircle,
  Shield,
  FileSearch,
  ImageIcon,
  Smartphone,
  Radio,
  Mail,
  Globe,
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, easeOut } from "@/components/motion/Reveal";

const apps = [
  { icon: MessageCircle, bg: "#25D366", label: "WhatsApp" },
  { icon: Mail, bg: "#5B8DEF", label: "Email" },
  { icon: Smartphone, bg: "#FF6B4A", label: "SMS" },
  { icon: FileSearch, bg: "#E5D4FF", label: "Claims", dark: true },
  { icon: Shield, bg: "#003E29", label: "SBP" },
  { icon: ImageIcon, bg: "#F0A05A", label: "Media" },
  { icon: Radio, bg: "#F5C542", label: "Viral", dark: true },
  { icon: Globe, bg: "#7EC8E3", label: "Urdu", dark: true },
];

export function DemoArc() {
  const reduce = useReducedMotion();

  return (
    <section className="px-3 py-4 sm:px-5 sm:py-6">
      <Reveal>
        <div className="mx-auto max-w-[1120px] overflow-hidden rounded-[40px] bg-[#141414] px-5 pb-12 pt-14 sm:rounded-[48px] sm:px-12 sm:pb-16 sm:pt-16">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="font-display text-[clamp(2rem,4.5vw,3.5rem)] leading-[1.08] tracking-[-0.035em] text-[#fdfcf0]">
              Verify faster in all your chats, every day.
            </h2>
            <p className="mx-auto mt-4 max-w-md text-[14px] leading-relaxed text-white/55">
              Specialized agents classify, match patterns, retrieve evidence, and judge confidence
              before you forward again.
            </p>
          </div>

          <div className="relative mx-auto mt-14 h-[120px] max-w-2xl sm:h-[150px]">
            {apps.map(({ icon: Icon, bg, label, dark }, i) => {
              const t = i / (apps.length - 1);
              const x = t * 100;
              const y = -Math.sin(t * Math.PI) * 48;
              const rot = (t - 0.5) * 36;
              return (
                <motion.div
                  key={label}
                  className="absolute flex h-[52px] w-[52px] -translate-x-1/2 items-center justify-center rounded-[16px] shadow-[0_12px_30px_rgba(0,0,0,0.35)] sm:h-[60px] sm:w-[60px] sm:rounded-[18px]"
                  style={{
                    left: `${x}%`,
                    top: `calc(70% + ${y}px)`,
                    background: bg,
                    color: dark ? "#141414" : "#fff",
                    rotate: rot,
                  }}
                  title={label}
                  initial={reduce ? false : { opacity: 0, scale: 0.7 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.05 * i, duration: 0.5, ease: easeOut }}
                >
                  <motion.span
                    className="flex h-full w-full items-center justify-center"
                    animate={reduce ? undefined : { y: [0, i % 2 === 0 ? -5 : 5, 0] }}
                    transition={{
                      duration: 3.2 + (i % 3) * 0.4,
                      repeat: Infinity,
                      ease: "easeInOut",
                      delay: i * 0.15,
                    }}
                  >
                    <Icon className="h-5 w-5 sm:h-6 sm:w-6" strokeWidth={2} aria-hidden />
                  </motion.span>
                </motion.div>
              );
            })}
          </div>

          <motion.div
            className="relative z-10 mx-auto mt-2 w-full max-w-[280px]"
            initial={reduce ? false : { opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.2, ease: easeOut }}
          >
            <div className="overflow-hidden rounded-[36px] border-[6px] border-[#2a2a2a] bg-[#fdfcf0] shadow-[0_30px_60px_rgba(0,0,0,0.45)]">
              <div className="mx-auto mt-2.5 h-5 w-24 rounded-full bg-[#141414]/10" />
              <div className="space-y-2.5 p-4 pb-7">
                <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8a8a8a]">
                  Live check
                </p>
                {[
                  { t: "WhatsApp forward", ok: true },
                  { t: "OTP / SBP pattern", ok: true },
                  { t: "Evidence sources", ok: true },
                  { t: "Judge confidence", ok: true },
                ].map((row, i) => (
                  <motion.div
                    key={row.t}
                    className="flex items-center gap-2.5 rounded-2xl border border-[#e4e1d4] bg-white px-3 py-2.5"
                    initial={reduce ? false : { opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.35 + i * 0.08, duration: 0.4 }}
                  >
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#003e29] text-[10px] text-white">
                      ✓
                    </span>
                    <span className="text-[12px] font-medium text-[#141414]">{row.t}</span>
                  </motion.div>
                ))}
                <div className="rounded-2xl bg-[#003e29]/10 px-3 py-2.5 text-[12px] font-semibold text-[#003e29]">
                  Verdict · needs caution
                </div>
              </div>
            </div>
          </motion.div>

          <div className="mt-10 text-center">
            <motion.div className="inline-block" whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
              <Link
                href="/check"
                className="inline-flex min-h-[44px] items-center rounded-full bg-[#e5d4ff] px-6 text-[13px] font-semibold text-[#1a1228]"
              >
                Open tools
              </Link>
            </motion.div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
