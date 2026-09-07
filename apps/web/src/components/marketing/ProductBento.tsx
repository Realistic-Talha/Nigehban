"use client";

import Image from "next/image";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Reveal, Stagger, StaggerItem, easeOut } from "@/components/motion/Reveal";

export function ProductBento() {
  const reduce = useReducedMotion();

  return (
    <section className="bg-[#fdfcf0] px-5 py-12 sm:py-16">
      <Stagger className="mx-auto grid max-w-[1120px] gap-4 sm:gap-5">
        <div className="grid gap-4 sm:gap-5 lg:grid-cols-[1.15fr_0.85fr]">
          <StaggerItem>
            <motion.div
              className="relative min-h-[360px] overflow-hidden rounded-[32px] sm:rounded-[36px]"
              whileHover={reduce ? undefined : { scale: 1.01 }}
              transition={{ duration: 0.45, ease: easeOut }}
            >
              <Image
                src="/marketing/portrait.jpg"
                alt="Scam check"
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 60vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
              <div className="absolute inset-x-0 bottom-0 p-7 sm:p-9">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/60">
                  Scam check
                </p>
                <h3 className="mt-2 font-display text-3xl text-white sm:text-4xl">
                  Catch the OTP trap.
                </h3>
                <p className="mt-2 max-w-sm text-[14px] text-white/70">
                  Camera capture and paste — agents match Pakistani scam patterns before you reply.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link
                    href="/check/scam"
                    className="inline-flex min-h-10 items-center rounded-full bg-[#e5d4ff] px-5 text-[13px] font-semibold text-[#1a1228]"
                  >
                    Check now
                  </Link>
                  <Link
                    href="/about"
                    className="inline-flex min-h-10 items-center rounded-full border border-white/40 px-5 text-[13px] font-semibold text-white"
                  >
                    Watch pipeline
                  </Link>
                </div>
              </div>
            </motion.div>
          </StaggerItem>

          <StaggerItem>
            <div className="flex h-full flex-col justify-between rounded-[32px] border border-[#e4e1d4] bg-white p-7 sm:rounded-[36px] sm:p-8">
              <div>
                <p className="font-display text-2xl text-[#141414] sm:text-3xl">Personal dictionary</p>
                <p className="mt-2 text-[13px] text-[#5c5c5c]">
                  Terms the pipeline already knows from Pakistani forwards.
                </p>
              </div>
              <ul className="mt-8 space-y-2">
                {["BISP · subsidy", "SBP · OTP", "FIA · cybercrime", "NADRA · CNIC"].map((row, i) => (
                  <motion.li
                    key={row}
                    className="rounded-2xl border border-[#e4e1d4] bg-[#fdfcf0] px-4 py-3 text-[13px] font-medium text-[#141414]"
                    initial={reduce ? false : { opacity: 0, x: 12 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.1 * i, duration: 0.4 }}
                  >
                    {row}
                  </motion.li>
                ))}
              </ul>
            </div>
          </StaggerItem>
        </div>

        <div className="grid gap-4 sm:grid-cols-3 sm:gap-5">
          {[
            {
              title: "Snippet library",
              body: "Save explanations you reuse when friends ask “is this real?”",
              dark: false,
              extra: (
                <div className="mt-5 rounded-2xl border border-[#e4e1d4] bg-[#fdfcf0] p-3">
                  <div className="h-8 rounded-full bg-[#e4e1d4]/80" />
                  <div className="mt-3 h-2.5 w-[80%] rounded bg-[#e4e1d4]" />
                  <div className="mt-2 h-2.5 w-[55%] rounded bg-[#e4e1d4]" />
                </div>
              ),
            },
            {
              title: "Urdu + EN",
              body: "Explanations in both languages with RTL-aware layout.",
              dark: true,
              link: { href: "/check/fact", label: "Open fact check →" },
            },
            {
              title: "Media signals",
              body: "EXIF, perceptual hash, visual heuristics — structured signals, not vibes.",
              dark: false,
              soft: true,
              link: { href: "/check/media", label: "Open media check →" },
            },
          ].map((card) => (
            <StaggerItem key={card.title}>
              <motion.div
                whileHover={reduce ? undefined : { y: -5 }}
                className={
                  card.dark
                    ? "rounded-[28px] bg-[#141414] p-6 text-[#fdfcf0]"
                    : card.soft
                      ? "rounded-[28px] border border-[#e4e1d4] bg-[#f7f5e8] p-6"
                      : "rounded-[28px] border border-[#e4e1d4] bg-white p-6"
                }
              >
                <p className={`font-display ${card.dark ? "text-3xl" : "text-xl"} text-inherit`}>
                  {card.title}
                </p>
                <p className={`mt-2 text-[13px] ${card.dark ? "text-white/55" : "text-[#5c5c5c]"}`}>
                  {card.body}
                </p>
                {card.extra}
                {card.link && (
                  <Link
                    href={card.link.href}
                    className={`mt-6 inline-block text-[13px] font-semibold ${
                      card.dark ? "text-[#e5d4ff]" : "text-[#003e29]"
                    }`}
                  >
                    {card.link.label}
                  </Link>
                )}
              </motion.div>
            </StaggerItem>
          ))}
        </div>
      </Stagger>
    </section>
  );
}
