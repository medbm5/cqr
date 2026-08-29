"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Page transition.
 *
 * `template.tsx` rather than `layout.tsx`: a template remounts on navigation,
 * which is what gives each route its own entry animation. Roughly 200ms, fading
 * and rising a few pixels — long enough to register as a change of view, short
 * enough that a reader chasing a number never waits for it.
 */
export default function Template({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
