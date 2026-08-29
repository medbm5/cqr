import { describe, expect, it } from "vitest";

import {
  buildExceedanceSeries,
  decadeTicks,
  returnPeriodLabel,
} from "@/components/simulation/exceedance-series";
import type { ExceedanceCurve } from "@/lib/api";

/** A curve in the shape the API returns it. */
function curve(kind: "aep" | "oep", periods: number[], losses: number[]): ExceedanceCurve {
  return {
    kind,
    return_period_years: periods,
    exceedance_probability: periods.map((period) => 1 / period),
    loss_eur: losses,
  };
}

/**
 * The real shape: the first ten of 160 points read exactly zero, because 73.7%
 * of simulated years hold no incident and the curve starts at a 1-in-2-year
 * probability. These are the numbers that rendered nothing at all.
 */
const PERIODS = [
  2, 2.14, 2.29, 2.45, 2.63, 2.81, 3.01, 3.22, 3.45, 3.69, 3.95, 4.23, 20, 100, 1000,
];
const AEP_LOSSES = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3418, 9206, 832553, 6463909, 21000000];
const OEP_LOSSES = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3417, 9111, 799000, 5900000, 18000000];

const AEP = curve("aep", PERIODS, AEP_LOSSES);
const OEP = curve("oep", PERIODS, OEP_LOSSES);

describe("buildExceedanceSeries", () => {
  const series = buildExceedanceSeries(AEP, OEP);

  /**
   * The bug this whole change exists for.
   *
   * A single zero reaching a log axis maps to negative infinity, which recharts
   * turns into a NaN path command and discards the *entire* line - not the one
   * point. Nothing rendered, and nothing errored.
   */
  it("passes no nonpositive value to either plotted series", () => {
    for (const point of series.points) {
      for (const value of [point.aep, point.oep]) {
        if (value !== null) expect(value).toBeGreaterThan(0);
      }
    }
  });

  it("nulls the zero points rather than dropping the return periods", () => {
    // The x positions survive so the empty band can still be annotated; only
    // the values are withheld from the lines.
    expect(series.points).toHaveLength(PERIODS.length);
    expect(series.points.slice(0, 10).every((point) => point.aep === null)).toBe(true);
    expect(series.points[10]?.aep).toBe(3418);
  });

  it("starts each curve at its own first nonzero return period", () => {
    expect(series.firstPlottedPeriod).toBe(3.95);
    expect(series.zeroRegionEnd).toBe(3.69);
  });

  it("filters the two curves independently", () => {
    // OEP lifts off later than AEP here. AEP must not be truncated to match it,
    // and OEP must not be extended backwards to match AEP.
    const laterOep = curve("oep", PERIODS, [...Array(12).fill(0), 799000, 5900000, 18000000]);

    const mixed = buildExceedanceSeries(AEP, laterOep);

    expect(mixed.points[10]?.aep).toBe(3418);
    expect(mixed.points[10]?.oep).toBeNull();
    expect(mixed.points[12]?.oep).toBe(799000);
    expect(mixed.firstPlottedPeriod).toBe(3.95);
  });

  /**
   * The invariant the two curves are only meaningful together under: the
   * largest single loss of a year cannot exceed that year's total.
   */
  it("keeps AEP at or above OEP at every shared return period", () => {
    for (const point of series.points) {
      if (point.aep !== null && point.oep !== null) {
        expect(point.aep).toBeGreaterThanOrEqual(point.oep);
      }
    }
  });

  it("never lets the y domain start at zero", () => {
    expect(series.yDomain[0]).toBeGreaterThan(0);
    expect(series.yDomain[0]).toBeLessThanOrEqual(series.yDomain[1]);
  });

  it("drops the y floor to the smallest plotted value when one sits below it", () => {
    // Smallest plotted loss is EUR 3,417 - under the EUR 10k floor, so the
    // floor gives way. A domain above its own data clips the line.
    expect(series.yDomain[0]).toBe(3417);
    expect(series.yDomain[1]).toBe(21_000_000);
  });

  it("keeps the y floor when every plotted value is above it", () => {
    const rich = buildExceedanceSeries(
      curve("aep", [2, 20], [50_000, 900_000]),
      curve("oep", [2, 20], [40_000, 800_000]),
    );

    expect(rich.yDomain[0]).toBe(10_000);
  });

  it("spans the full x range including the zero band", () => {
    expect(series.xDomain).toEqual([2, 1000]);
  });

  it("reports no plottable curve when every point is zero", () => {
    const empty = buildExceedanceSeries(
      curve("aep", [2, 10], [0, 0]),
      curve("oep", [2, 10], [0, 0]),
    );

    expect(empty.firstPlottedPeriod).toBeNull();
    expect(empty.zeroRegionEnd).toBeNull();
    expect(empty.yDomain[0]).toBeGreaterThan(0);
  });

  it("annotates no zero band when the curves are positive from the start", () => {
    const clean = buildExceedanceSeries(
      curve("aep", [2, 10], [1_000, 9_000]),
      curve("oep", [2, 10], [900, 8_000]),
    );

    expect(clean.zeroRegionEnd).toBeNull();
    expect(clean.firstPlottedPeriod).toBe(2);
  });
});

describe("axis helpers", () => {
  it("keeps only decade ticks inside the domain", () => {
    expect(decadeTicks([3417, 21_000_000])).toEqual([1e4, 1e5, 1e6, 1e7]);
  });

  it("labels return periods the way an underwriter reads them", () => {
    expect(returnPeriodLabel(20)).toBe("1-in-20-year");
    expect(returnPeriodLabel(3.95)).toBe("1-in-4.0-year");
    expect(returnPeriodLabel(10_000)).toBe("1-in-10k-year");
  });
});
