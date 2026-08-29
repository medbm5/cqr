"use client";

import { HintTip } from "@/components/HintTip";
import type { SeverityClass } from "@/lib/api";

const THRESHOLDS: { value: SeverityClass; label: string }[] = [
  { value: "low", label: "Low and above" },
  { value: "medium", label: "Medium and above" },
  { value: "high", label: "High and above" },
  { value: "critical", label: "Critical only" },
];

const WINDOWS = [1, 4, 8, 12, 24, 48, 72, 168] as const;

/**
 * The two conventions the frequency estimate rests on.
 *
 * One row, above everything it scopes, so every chart below re-renders against
 * the same slice and the numbers on the page always agree. Neither parameter is
 * derivable from the data — they are judgment calls, and putting them on screen
 * as controls is the honest way to say so.
 */
export function ParamPanel({
  threshold,
  windowHours,
  pending,
  onChange,
}: {
  threshold: SeverityClass;
  windowHours: number;
  pending: boolean;
  onChange: (next: { threshold: SeverityClass; windowHours: number }) => void;
}) {
  const windowIndex = Math.max(0, WINDOWS.indexOf(windowHours as (typeof WINDOWS)[number]));

  return (
    <div className="mb-6 flex flex-wrap items-end gap-x-8 gap-y-4 rounded-xl border border-navy-800 bg-navy-900 px-5 py-4">
      <div>
        {/* The hint sits beside the label, not inside it: a button inside a
            `for`-bound label activates the control it labels on every click. */}
        <div className="flex items-baseline">
          <label htmlFor="threshold" className="text-xs font-medium text-ink-secondary">
            Attack-grade threshold
          </label>
          <HintTip term="attack_grade" />
        </div>
        <select
          id="threshold"
          value={threshold}
          onChange={(event) =>
            onChange({ threshold: event.target.value as SeverityClass, windowHours })
          }
          className="mt-1.5 rounded-lg border border-navy-700 bg-navy-850 px-3 py-1.5 text-sm text-ink transition-colors hover:border-navy-600"
        >
          {THRESHOLDS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="min-w-56 flex-1">
        <div className="flex items-baseline justify-between text-xs">
          <span className="flex items-baseline">
            <label htmlFor="window" className="font-medium text-ink-secondary">
              Session window
            </label>
            <HintTip term="session_window" />
          </span>
          <span className="tabular text-ink">{windowHours}h</span>
        </div>
        <input
          id="window"
          type="range"
          min={0}
          max={WINDOWS.length - 1}
          step={1}
          value={windowIndex}
          onChange={(event) =>
            onChange({ threshold, windowHours: WINDOWS[Number(event.target.value)] ?? 24 })
          }
          className="mt-3 h-1 w-full cursor-pointer appearance-none rounded-full bg-navy-700 accent-accent"
        />
        <p className="mt-1.5 text-xs text-ink-muted">
          Quiet period that separates two attacks on one asset
        </p>
      </div>

      {/* The refetch indicator lives with the controls, not over the charts —
          the charts hold their previous render instead of flashing a skeleton. */}
      <p className="text-xs text-ink-muted" aria-live="polite">
        {pending ? "Recomputing…" : " "}
      </p>
    </div>
  );
}
