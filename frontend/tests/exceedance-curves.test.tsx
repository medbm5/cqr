import { render, screen } from "@testing-library/react";
import { cloneElement, type ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { ExceedanceCurves } from "@/components/simulation/exceedance-curves";
import type { ExceedanceCurve, SimulationResponse } from "@/lib/api";

/**
 * Give the chart a size.
 *
 * `ResponsiveContainer` measures its parent, and in jsdom every element is
 * 0x0 - so recharts renders an empty SVG and every assertion below would pass
 * vacuously against a chart that draws nothing. Replacing it with a fixed size
 * is what makes this a real render test rather than a smoke test.
 *
 * `vi.mock` is hoisted above the imports by vitest, so the static import of the
 * component below still resolves against this mock.
 */
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: ReactElement }) =>
      cloneElement(children, { width: 800, height: 400 }),
  };
});

const PERIODS = [2, 2.45, 3.01, 3.69, 3.95, 4.23, 20, 100, 1000, 10000];
const AEP = [0, 0, 0, 0, 3418, 9206, 832553, 6463909, 21000000, 37142208];
const OEP = [0, 0, 0, 0, 3417, 9111, 799000, 5900000, 18000000, 23476094];

function curve(kind: "aep" | "oep", losses: number[]): ExceedanceCurve {
  return {
    kind,
    return_period_years: PERIODS,
    exceedance_probability: PERIODS.map((period) => 1 / period),
    loss_eur: losses,
  };
}

const METRICS: SimulationResponse["metrics"] = {
  aal: 273_704,
  median: 0,
  var_95: 816_323,
  var_99: 6_665_810,
  tvar_95: 4_820_816,
  tvar_99: 15_134_257,
  probability_of_no_loss: 0.7371,
  maximum: 43_066_333,
};

function paths(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll("path.recharts-line-curve")).map(
    (node) => node.getAttribute("d") ?? "",
  );
}

describe("ExceedanceCurves", () => {
  it("draws both lines", () => {
    const { container } = render(
      <ExceedanceCurves aep={curve("aep", AEP)} oep={curve("oep", OEP)} metrics={METRICS} />,
    );

    const drawn = paths(container);
    expect(drawn).toHaveLength(2);
    for (const d of drawn) expect(d.length).toBeGreaterThan(20);
  });

  /**
   * The regression. A zero reaching a log axis becomes negative infinity, and
   * recharts writes that straight into the path data as `NaN` - which the
   * browser discards silently, taking the whole line with it. The chart showed
   * axes, a legend and no curves, and nothing errored.
   */
  it("emits no NaN or Infinity in the path data", () => {
    const { container } = render(
      <ExceedanceCurves aep={curve("aep", AEP)} oep={curve("oep", OEP)} metrics={METRICS} />,
    );

    for (const d of paths(container)) {
      expect(d).not.toMatch(/NaN/);
      expect(d).not.toMatch(/Infinity/);
    }
  });

  it("shades the zero-loss band and says what it is", () => {
    const { container } = render(
      <ExceedanceCurves aep={curve("aep", AEP)} oep={curve("oep", OEP)} metrics={METRICS} />,
    );

    expect(container.querySelector(".recharts-reference-area")).toBeInTheDocument();
    expect(screen.getByText("expected year costs €0")).toBeInTheDocument();
  });

  it("marks both VaR tiles on the curve", () => {
    const { container } = render(
      <ExceedanceCurves aep={curve("aep", AEP)} oep={curve("oep", OEP)} metrics={METRICS} />,
    );

    expect(container.querySelectorAll(".recharts-reference-dot")).toHaveLength(2);
    expect(screen.getByText(/VaR 95/)).toBeInTheDocument();
    expect(screen.getByText(/VaR 99/)).toBeInTheDocument();
  });

  it("states the zero region in the footnote with the run's own numbers", () => {
    render(
      <ExceedanceCurves aep={curve("aep", AEP)} oep={curve("oep", OEP)} metrics={METRICS} />,
    );

    expect(screen.getByText(/~4.0-year return period the expected year costs €0/)).toBeVisible();
    expect(screen.getByText(/73.7% of years are loss-free/)).toBeVisible();
  });

  it("falls back to a stated absence when no year carried a loss", () => {
    const zeros = PERIODS.map(() => 0);
    const { container } = render(
      <ExceedanceCurves
        aep={curve("aep", zeros)}
        oep={curve("oep", zeros)}
        metrics={{ ...METRICS, var_95: 0, var_99: 0, probability_of_no_loss: 1 }}
      />,
    );

    expect(paths(container)).toHaveLength(0);
    expect(screen.getByText(/Every simulated year cost €0/)).toBeInTheDocument();
  });
});
