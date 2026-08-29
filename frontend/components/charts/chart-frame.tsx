"use client";

import { useId, useState, type ReactNode } from "react";

import { CHROME } from "./tokens";

export interface LegendEntry {
  label: string;
  color: string;
  /** `line` for line series, `rect` for bars and areas — the legend mirrors the mark. */
  shape?: "rect" | "line";
}

export interface TableColumn {
  key: string;
  label: string;
  numeric?: boolean;
}

/**
 * The frame every chart sits in: title, legend, and a table view of the same data.
 *
 * The table is not a nicety. A colour-encoded chart gates its values behind
 * vision and behind hovering; the table is the WCAG-clean twin where every value
 * is plain text, and it is what makes a tooltip an enhancement rather than the
 * only way to read the chart.
 */
export function ChartFrame({
  title,
  hint,
  legend,
  columns,
  rows,
  children,
  dimmed = false,
}: {
  title: string;
  hint?: string;
  legend?: LegendEntry[];
  columns: TableColumn[];
  rows: Record<string, string | number>[];
  children: ReactNode;
  dimmed?: boolean;
}) {
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();

  return (
    <section className="rounded-xl border border-navy-800 bg-navy-900 shadow-card">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 px-5 pt-4">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>
          {hint ? <p className="mt-0.5 text-xs text-ink-muted">{hint}</p> : null}
        </div>
        <button
          type="button"
          onClick={() => setShowTable((open) => !open)}
          aria-expanded={showTable}
          aria-controls={tableId}
          className="rounded-md border border-navy-700 px-2.5 py-1 text-xs text-ink-secondary transition-colors hover:border-accent/50 hover:text-ink"
        >
          {showTable ? "Show chart" : "Show table"}
        </button>
      </header>

      {/* A legend is always present for two or more series; one series needs
          none, because the title already names what is plotted. */}
      {legend && legend.length > 1 ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1.5 px-5 pt-3">
          {legend.map((entry) => (
            <li key={entry.label} className="flex items-center gap-2 text-xs text-ink-secondary">
              <span
                aria-hidden
                style={{ background: entry.color }}
                className={entry.shape === "line" ? "h-0.5 w-4 rounded-full" : "h-2.5 w-2.5 rounded-sm"}
              />
              {entry.label}
            </li>
          ))}
        </ul>
      ) : null}

      <div className="px-5 pb-5 pt-4">
        {showTable ? (
          <DataTable id={tableId} columns={columns} rows={rows} />
        ) : (
          // Refetch holds the previous render at reduced opacity: no skeleton
          // flash, no layout jump while the numbers change under the reader.
          <div
            className="transition-opacity duration-200"
            style={{ opacity: dimmed ? 0.45 : 1 }}
            aria-busy={dimmed}
          >
            {children}
          </div>
        )}
      </div>
    </section>
  );
}

/** The chart's values as plain text — reachable without colour, hover or a mouse. */
export function DataTable({
  id,
  columns,
  rows,
}: {
  id?: string;
  columns: TableColumn[];
  rows: Record<string, string | number>[];
}) {
  return (
    <div id={id} className="max-h-80 overflow-auto rounded-lg border border-navy-800">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-navy-850">
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={[
                  "border-b border-navy-800 px-3 py-2 font-medium text-ink-secondary",
                  column.numeric ? "text-right" : "text-left",
                ].join(" ")}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-navy-800/60 last:border-0">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={[
                    "px-3 py-1.5 text-ink",
                    column.numeric ? "tabular text-right" : "text-left",
                  ].join(" ")}
                >
                  {row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Shared axis styling: hairline, solid, one step off the surface. */
export const AXIS_PROPS = {
  stroke: CHROME.axis,
  tick: { fill: CHROME.inkMuted, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: CHROME.grid },
} as const;
