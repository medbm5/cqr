"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Entry transition shared by the cockpit sections. Kept around 200ms so the
 * numbers arrive fast: this is a decision-support tool, not a slideshow.
 */
export function FadeIn({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
