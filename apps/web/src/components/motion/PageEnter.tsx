"use client";

import { motion, useReducedMotion } from "framer-motion";
import { easeOut } from "@/components/motion/Reveal";

/** Soft fade-up when entering any product page. */
export function PageEnter({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  if (reduce) return <>{children}</>;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: easeOut }}
    >
      {children}
    </motion.div>
  );
}
