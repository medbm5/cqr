/**
 * Number formatting shared by every figure on screen.
 *
 * Kept in one place so a euro amount reads the same in a stat tile, a table and
 * a tooltip. Nothing here computes anything — the engine has already decided
 * what the number is.
 */

/** Compact a count: 1,284 · 12.9K · 4.2M. */
export function compactNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) < 10_000) return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

/** A full count with thousands separators, for tables and captions. */
export function fullNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

/**
 * Compact euros: €39K · €1.2M · €12.5B.
 *
 * Losses in this model span six orders of magnitude, so a stat tile that showed
 * every digit would be unreadable and a chart axis unusable. The full figure
 * stays available in captions and tooltips.
 */
export function compactEur(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

/** A full euro amount, for the caption under a compacted value. */
export function fullEur(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}

/** A ratio as a percentage: 0.298 → 29.8%. */
export function percent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** A rate per year, compacted the same way as a count. */
export function perYear(value: number): string {
  return `${compactNumber(value)}/yr`;
}

/**
 * How a figure should be rendered.
 *
 * A key rather than a function, because a stat tile is a client component and
 * React cannot serialize a function across that boundary. The server names the
 * format; the client resolves it.
 */
export type FormatKind = "count" | "fullCount" | "eur" | "percent" | "perYear";

export const FORMATTERS: Record<FormatKind, (value: number) => string> = {
  count: compactNumber,
  fullCount: fullNumber,
  eur: compactEur,
  percent: (value) => percent(value),
  perYear,
};
