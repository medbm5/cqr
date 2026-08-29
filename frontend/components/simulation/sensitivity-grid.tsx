"use client";

import { useState } from "react";

import { ChartFrame } from "@/components/charts/chart-frame";
import { SEQUENTIAL, inkOn, sequentialStep } from "@/components/charts/tokens";
import type { SimulationResponse } from "@/lib/api";
import { compactEur, fullEur, fullNumber } from "@/lib/format";

type Grid = NonNullable<SimulationResponse["sensitivity"]>;

const THRESHOLD_ORDER = ["medium", "high", "critical"] as const;

/**
 * What the answer would have been under the other defensible settings.
 *
 * Magnitude across a grid, so the fill is the sequential ramp with a scale
 * legend — and every cell is *also* direct-labelled, because this table is the
 * argument, not an illustration. A reader must be able to compare the corners
 * without measuring two shades against each other.
 *
 * The span across this grid is wider than any sampling error in the run. Quoting
 * the headline AAL without it would be quoting one cell of nine.
 */
export function SensitivityGrid({ grid }: { grid: Grid }) {
  const [hovered, setHovered] = useState<string | null>(null);

  const windows = Array.from(new Set(grid.cells.map((cell) => cell.session_window_hours))).sort(
    (a, b) => a - b,
  );
  const [low, high] = grid.aal_range as [number, number];
  const span = high - low || 1;

  return (
    <ChartFrame
      title="Sensitivity to the two frequency conventions"
      hint={`${fullNumber(grid.n_years)} years per cell, all on seed ${grid.seed}`}
      columns={[
        { key: "threshold", label: "Threshold" },
        { key: "window", label: "Session window" },
        { key: "episodes", label: "Episodes", numeric: true },
        { key: "detected", label: "detected / yr", numeric: true },
        { key: "incident", label: "incidents / yr", numeric: true },
        { key: "aal", label: "AAL", numeric: true },
      ]}
      rows={grid.cells.map((cell) => ({
        threshold: cell.severity_threshold,
        window: `${cell.session_window_hours}h`,
        episodes: fullNumber(cell.episodes),
        detected: fullNumber(Math.round(cell.lambda_detected)),
        incident: cell.lambda_incident.toFixed(4),
        aal: fullEur(cell.aal),
      }))}
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[30rem] border-separate border-spacing-1">
          <caption className="sr-only">
            Average annual loss for each combination of attack-grade threshold and session window
          </caption>
          <thead>
            <tr>
              <th scope="col" className="w-24 text-left text-xs font-medium text-ink-muted">
                threshold
              </th>
              {windows.map((window) => (
                <th
                  key={window}
                  scope="col"
                  className="tabular pb-1 text-xs font-medium text-ink-muted"
                >
                  {window}h window
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {THRESHOLD_ORDER.map((threshold) => (
              <tr key={threshold}>
                <th
                  scope="row"
                  className="text-left text-xs font-medium capitalize text-ink-secondary"
                >
                  {threshold}
                </th>
                {windows.map((window) => {
                  const cell = grid.cells.find(
                    (candidate) =>
                      candidate.severity_threshold === threshold &&
                      candidate.session_window_hours === window,
                  );
                  if (!cell) return <td key={window} />;

                  const fill = sequentialStep((cell.aal - low) / span);
                  const key = `${threshold}-${window}`;
                  return (
                    <td key={window} className="p-0">
                      <button
                        type="button"
                        onMouseEnter={() => setHovered(key)}
                        onFocus={() => setHovered(key)}
                        onMouseLeave={() => setHovered(null)}
                        onBlur={() => setHovered(null)}
                        style={{ background: fill, color: inkOn(fill) }}
                        className="block w-full rounded-lg px-3 py-4 text-center transition-transform duration-150 hover:scale-[1.03] focus-visible:scale-[1.03]"
                        aria-label={`${threshold} threshold, ${window} hour window: average annual loss ${fullEur(cell.aal)}, ${fullNumber(cell.episodes)} episodes`}
                      >
                        {/* Direct-labelled: the grid is the argument, so no value
                            is gated behind a hover. */}
                        <span className="tabular block text-sm font-semibold">
                          {compactEur(cell.aal)}
                        </span>
                        <span className="tabular mt-0.5 block text-[11px] opacity-80">
                          {fullNumber(Math.round(cell.lambda_detected))} detected/yr
                        </span>
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <span className="tabular text-xs text-ink-muted">{compactEur(low)}</span>
        <div className="flex gap-0.5" aria-hidden>
          {SEQUENTIAL.map((step) => (
            <span key={step} style={{ background: step }} className="h-2.5 w-6 rounded-sm" />
          ))}
        </div>
        <span className="tabular text-xs text-ink-muted">{compactEur(high)}</span>
        <span className="text-xs text-ink-secondary">
          a factor of {grid.spread_factor.toFixed(1)} between the corners
        </span>
      </div>

      <p className="mt-3 h-4 text-xs text-ink-secondary" aria-live="polite">
        {hovered
          ? (() => {
              const cell = grid.cells.find(
                (candidate) =>
                  `${candidate.severity_threshold}-${candidate.session_window_hours}` === hovered,
              );
              return cell
                ? `${cell.severity_threshold} threshold, ${cell.session_window_hours}h window · ${fullNumber(cell.episodes)} episodes · ${fullEur(cell.aal)}`
                : "";
            })()
          : ""}
      </p>
    </ChartFrame>
  );
}
