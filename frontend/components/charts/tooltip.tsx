"use client";

import type { ReactNode } from "react";

/**
 * The shared tooltip body.
 *
 * Values lead and labels follow — the reader already knows which series they
 * are pointing at and wants the number. Series are keyed by a short stroke
 * rather than a filled box: at this density a box is data-weight ink doing a
 * label's job.
 *
 * Names come from API responses, so they are inserted as text nodes by React
 * rather than composed into markup.
 */
export function TooltipShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="pointer-events-none rounded-lg border border-navy-700 bg-navy-850/95 px-3 py-2 shadow-lift backdrop-blur">
      <p className="text-xs font-medium text-ink-secondary">{title}</p>
      <ul className="mt-1.5 space-y-1">{children}</ul>
    </div>
  );
}

export function TooltipRow({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value: string;
}) {
  return (
    <li className="flex items-baseline gap-2">
      <span aria-hidden style={{ background: color }} className="h-0.5 w-3 shrink-0 rounded-full" />
      <span className="tabular text-sm font-semibold text-ink">{value}</span>
      <span className="text-xs text-ink-muted">{label}</span>
    </li>
  );
}
