"use client";

import { useState } from "react";

import { ChartFrame } from "@/components/charts/chart-frame";
import { SEQUENTIAL, sequentialStep } from "@/components/charts/tokens";
import type { AssetRow } from "@/lib/api";
import { fullNumber } from "@/lib/format";

function shortWeek(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/**
 * Episodes per asset, per week.
 *
 * Magnitude on a grid, which is the heatmap's job — so the fill is a
 * **sequential** ramp: one hue, near-zero receding toward the surface and high
 * values advancing off it. Never a rainbow; the reader must be able to rank two
 * cells by eye without consulting a key.
 *
 * A scale legend is mandatory here, because a continuous fill is the only
 * encoding a cell carries. The table view holds every value as text.
 */
export function Heatmap({ assets, dimmed = false }: { assets: AssetRow[]; dimmed?: boolean }) {
  const [hovered, setHovered] = useState<{ asset: string; week: string; count: number } | null>(
    null,
  );

  const weeks = Array.from(
    new Set(assets.flatMap((asset) => Object.keys(asset.episodes_by_week))),
  ).sort();
  const peak = Math.max(
    1,
    ...assets.flatMap((asset) => Object.values(asset.episodes_by_week) as number[]),
  );
  const ordered = [...assets].sort((a, b) => a.asset_id.localeCompare(b.asset_id));

  return (
    <ChartFrame
      title="Episodes per asset, per week"
      term="episode"
      hint={`Darker is quieter; the busiest cell holds ${fullNumber(peak)} episodes`}
      dimmed={dimmed}
      columns={[
        { key: "asset", label: "Asset" },
        { key: "environment", label: "Environment" },
        { key: "criticality", label: "Criticality", numeric: true },
        { key: "episodes", label: "Episodes", numeric: true },
        { key: "busiest", label: "Busiest week", numeric: true },
      ]}
      rows={ordered.map((asset) => {
        const values = Object.values(asset.episodes_by_week) as number[];
        return {
          asset: asset.asset_id,
          environment: asset.environment ?? "—",
          criticality: asset.business_criticality ?? "—",
          episodes: fullNumber(asset.episodes),
          busiest: values.length > 0 ? fullNumber(Math.max(...values)) : "0",
        };
      })}
    >
      <div className="relative">
        <div className="overflow-x-auto">
          <table className="border-separate border-spacing-0.5">
            <caption className="sr-only">
              Episode counts for each asset in each week of the observation window
            </caption>
            <thead>
              <tr>
                <th scope="col" className="sr-only">
                  Asset
                </th>
                {weeks.map((week, index) => (
                  <th
                    key={week}
                    scope="col"
                    className="h-6 w-6 align-bottom text-[10px] font-normal text-ink-muted"
                  >
                    {/* Every fourth week is labelled: one label per column would
                        be unreadable at this density. */}
                    {index % 4 === 0 ? shortWeek(week).split(" ")[0] : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ordered.map((asset) => (
                <tr key={asset.asset_id}>
                  <th
                    scope="row"
                    className="tabular sticky left-0 z-10 bg-navy-900 pr-3 text-right text-[11px] font-normal text-ink-secondary"
                  >
                    {asset.asset_id.replace("asset-", "")}
                  </th>
                  {weeks.map((week) => {
                    const count = asset.episodes_by_week[week] ?? 0;
                    return (
                      <td key={week} className="p-0">
                        {/* The hit target is the whole cell plus its gap, so a
                            reader never has to land on painted pixels. */}
                        <button
                          type="button"
                          onMouseEnter={() =>
                            setHovered({ asset: asset.asset_id, week, count })
                          }
                          onFocus={() => setHovered({ asset: asset.asset_id, week, count })}
                          onMouseLeave={() => setHovered(null)}
                          onBlur={() => setHovered(null)}
                          style={{ background: sequentialStep(count / peak) }}
                          className="block h-6 w-6 rounded-sm transition-transform duration-150 hover:scale-110 focus-visible:scale-110"
                          aria-label={`${asset.asset_id}, week of ${shortWeek(week)}: ${count} episodes`}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Scale legend — mandatory: the fill is the cell's only encoding. */}
        <div className="mt-4 flex items-center gap-3">
          <span className="text-xs text-ink-muted">0</span>
          <div className="flex gap-0.5" aria-hidden>
            {SEQUENTIAL.map((step) => (
              <span key={step} style={{ background: step }} className="h-2.5 w-6 rounded-sm" />
            ))}
          </div>
          <span className="tabular text-xs text-ink-muted">{fullNumber(peak)} episodes</span>
        </div>

        <p className="mt-3 h-4 text-xs text-ink-secondary" aria-live="polite">
          {hovered
            ? `${hovered.asset} · week of ${shortWeek(hovered.week)} · ${fullNumber(hovered.count)} episodes`
            : ""}
        </p>
      </div>
    </ChartFrame>
  );
}
