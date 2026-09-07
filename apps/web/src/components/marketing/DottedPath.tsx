"use client";

import { motion, useReducedMotion } from "framer-motion";

export function DottedPath({ className }: { className?: string }) {
  const reduce = useReducedMotion();

  return (
    <svg
      className={className}
      viewBox="0 0 200 800"
      fill="none"
      aria-hidden
      preserveAspectRatio="none"
    >
      <motion.path
        d="M40 0 C 120 80, 20 160, 100 240 C 180 320, 40 400, 120 480 C 200 560, 60 640, 100 800"
        stroke="var(--path-stroke)"
        strokeWidth="1.5"
        strokeDasharray="4 8"
        strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0, opacity: 0 }}
        whileInView={reduce ? undefined : { pathLength: 1, opacity: 1 }}
        viewport={{ once: true, amount: 0.1 }}
        transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
      />
    </svg>
  );
}
