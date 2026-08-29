"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "./nav-items";

/**
 * Primary navigation.
 *
 * A fixed rail from `lg` up, where there is room for the pipeline to read as an
 * ordered list; a scrollable strip below that. The active item is marked by the
 * accent and by a shared-layout indicator, so the current position survives a
 * route change as a movement rather than a repaint.
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Sections"
      className="sticky top-0 z-20 border-b border-navy-800 bg-navy-950/85 backdrop-blur lg:h-dvh lg:w-64 lg:shrink-0 lg:border-b-0 lg:border-r"
    >
      <div className="flex items-center gap-3 px-5 py-4 lg:py-6">
        <span
          aria-hidden
          className="h-6 w-1.5 rounded-full bg-accent shadow-[0_0_12px] shadow-accent/50"
        />
        <div>
          <p className="text-sm font-semibold leading-tight tracking-tight text-ink">
            Citalid
          </p>
          <p className="text-xs leading-tight text-ink-muted">Risk Engine</p>
        </div>
      </div>

      <ul className="flex gap-1 overflow-x-auto px-3 pb-3 lg:mt-2 lg:flex-col lg:overflow-visible lg:px-3">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

          return (
            <li key={item.href} className="relative shrink-0 lg:shrink">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "relative block rounded-lg px-3 py-2 text-sm transition-colors duration-200",
                  active
                    ? "text-ink"
                    : "text-ink-secondary hover:bg-navy-900 hover:text-ink",
                ].join(" ")}
              >
                {active ? (
                  <motion.span
                    layoutId="nav-active"
                    aria-hidden
                    className="absolute inset-0 rounded-lg border border-accent/30 bg-accent-soft"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                ) : null}
                <span className="relative flex flex-col">
                  <span className="font-medium">{item.label}</span>
                  <span className="hidden text-xs text-ink-muted lg:block">{item.hint}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
