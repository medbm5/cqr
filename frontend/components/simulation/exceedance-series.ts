import type { ExceedanceCurve } from "@/lib/api";

/**
 * One plotted point: a return period and what each curve reads there.
 *
 * `null` rather than `0` for a curve that has nothing to say at this return
 * period. A log axis has no coordinate for zero — it maps to negative infinity,
 * which recharts turns into a NaN path command that discards *the whole line*,
 * not merely the offending point. Null is skipped instead.
 */
export interface ExceedancePoint {
  period: number;
  aep: number | null;
  oep: number | null;
}

export interface ExceedanceSeries {
  points: ExceedancePoint[];
  /** Shortest return period at which either curve has a positive loss. */
  firstPlottedPeriod: number | null;
  /** Longest return period at which both curves still read zero, if any. */
  zeroRegionEnd: number | null;
  /** Full x range including the zero region, so it can still be annotated. */
  xDomain: [number, number];
  /** Log-safe y range: never starts at zero. */
  yDomain: [number, number];
}

/** Where the y axis starts unless a plotted value sits below it. */
const Y_FLOOR_EUR = 10_000;

/**
 * Turn the two API curves into something a log-log chart can actually draw.
 *
 * The short return periods carry a loss of exactly zero, because most years hold
 * no incident at all: with 73.7% of years loss-free, the loss exceeded with
 * probability 0.5 — a 1-in-2-year loss — is nothing. That is a true and
 * interesting fact, and it is also unplottable on a log axis. It is therefore
 * dropped from the series and annotated separately rather than silently
 * breaking the render.
 *
 * The two curves are filtered independently. They happen to reach zero at the
 * same point on this data, but nothing guarantees it: OEP is the largest single
 * loss and AEP the annual total, and a run where they part company at the left
 * edge must not force one curve to inherit the other's starting point.
 *
 * @param aep Aggregate exceedance curve — the year's total.
 * @param oep Occurrence exceedance curve — the year's largest single loss.
 * @returns The plottable points and the domains they need.
 */
export function buildExceedanceSeries(
  aep: ExceedanceCurve,
  oep: ExceedanceCurve,
): ExceedanceSeries {
  const periods = aep.return_period_years;

  const points: ExceedancePoint[] = periods.map((period, index) => {
    const aepValue = aep.loss_eur[index] ?? 0;
    const oepValue = oep.loss_eur[index] ?? 0;
    return {
      period,
      aep: aepValue > 0 ? aepValue : null,
      oep: oepValue > 0 ? oepValue : null,
    };
  });

  const plotted = points.filter((point) => point.aep !== null || point.oep !== null);
  const firstPlottedPeriod = plotted[0]?.period ?? null;

  // The last return period before either curve lifts off zero. Null when the
  // curves are positive from the very first point — there is no region to
  // annotate, and inventing one would annotate an empty band.
  const zeroIndex = points.findIndex((point) => point.aep !== null || point.oep !== null);
  const zeroRegionEnd = zeroIndex > 0 ? (points[zeroIndex - 1]?.period ?? null) : null;

  const values = plotted.flatMap((point) =>
    [point.aep, point.oep].filter((value): value is number => value !== null),
  );
  const lowest = values.length > 0 ? Math.min(...values) : Y_FLOOR_EUR;
  const highest = values.length > 0 ? Math.max(...values) : Y_FLOOR_EUR * 10;

  return {
    points,
    firstPlottedPeriod,
    zeroRegionEnd,
    xDomain: [periods[0] ?? 1, periods[periods.length - 1] ?? 1],
    // Start at the floor, or lower if a real value sits beneath it. Never at
    // zero, and never above the smallest thing being drawn.
    yDomain: [Math.min(Y_FLOOR_EUR, lowest), highest],
  };
}

/** Decade ticks in euros, filtered to those inside a domain. */
export function decadeTicks([low, high]: [number, number]): number[] {
  return [1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9].filter((tick) => tick >= low && tick <= high);
}

/** "1-in-20-year", or "1-in-10k-year" once the numbers get long. */
export function returnPeriodLabel(years: number): string {
  if (years >= 1000) return `1-in-${Math.round(years / 1000)}k-year`;
  if (years >= 10) return `1-in-${Math.round(years)}-year`;
  return `1-in-${years.toFixed(1)}-year`;
}
