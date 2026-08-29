/**
 * Chart colour roles — validated, not chosen by eye.
 *
 * Every value here was checked with the data-viz validator against this app's
 * chart surface (`navy.900`, `#0A1120`) in dark mode. The first palette tried —
 * the UI accent `#38BDF8` beside amber and violet — FAILED: the accent sits
 * outside the dark lightness band, and sky↔violet collapse under deuteranopia
 * at ΔE 5.2 against a floor of 6. These are the values that passed.
 *
 * The UI accent stays what it always was: chrome, focus, the active route. It
 * is deliberately *not* a series colour, so a blue mark in a chart always means
 * a series and never "this is interactive".
 */

/**
 * Categorical slots — identity, for series a reader must tell apart.
 *
 * Validated all-pairs (the harder test) on `#0A1120`: lightness band PASS,
 * chroma floor PASS, worst CVD ΔE 9.4 (deutan) against a target of 8, worst
 * normal-vision ΔE 20.9 against a floor of 15, contrast ≥ 3:1 PASS.
 *
 * Assigned in fixed order and never cycled. Colour follows the entity: the SIEM
 * feed is slot 1 wherever it appears, so a filter that drops a series never
 * repaints the survivors.
 */
export const SERIES = {
  siem: "#3987e5",
  edr: "#d95926",
  both: "#199e70",
} as const;

/**
 * Ordinal ramp — position in an ordered sequence (funnel stages, severity).
 *
 * One hue, monotone lightness. Validated with `--ordinal`: monotone PASS,
 * adjacent ΔL ≥ 0.06 PASS, light-end contrast 2.33:1 against a 2.0 floor,
 * single hue (3° spread) PASS.
 *
 * Ordered dark → light, so on a dark surface the *later, smaller* stage of a
 * funnel recedes and the *more severe* class advances. Both are the direction a
 * reader expects on this ground.
 */
export const ORDINAL_4 = ["#184f95", "#2a78d6", "#5598e7", "#9ec5f4"] as const;

/**
 * Sequential ramp — continuous magnitude (the heatmap).
 *
 * The full documented blue ramp, anchored for dark: near-zero recedes toward
 * the surface, high values advance. Sequential ramps are checked for lightness
 * monotonicity, not adjacency CVD — running the categorical validator on one
 * fails by design.
 */
export const SEQUENTIAL = [
  "#0d366b",
  "#184f95",
  "#1c5cab",
  "#256abf",
  "#2a78d6",
  "#3987e5",
  "#5598e7",
  "#86b6ef",
  "#b7d3f6",
] as const;

/** Severity classes, low → critical, on the ordinal ramp. */
export const SEVERITY_COLORS: Record<string, string> = {
  low: ORDINAL_4[0],
  medium: ORDINAL_4[1],
  high: ORDINAL_4[2],
  critical: ORDINAL_4[3],
  // Not a point on the scale: an ungraded event is unknown, not mild. A neutral
  // keeps it out of the ordered ramp so it cannot be misread as a severity.
  unknown: "#4B5A72",
};

/** Chart chrome. Recessive by construction — the data is the only loud thing. */
export const CHROME = {
  surface: "#0A1120",
  grid: "#1B2942",
  axis: "#7A8AA0",
  ink: "#F1F5F9",
  inkSecondary: "#94A3B8",
  inkMuted: "#7A8AA0",
} as const;

/** The 2px surface gap that separates touching marks, as a stroke colour. */
export const SURFACE_GAP = CHROME.surface;

/** Pick ink or white for a label sitting inside a coloured fill. */
export function inkOn(fill: string): string {
  const r = parseInt(fill.slice(1, 3), 16);
  const g = parseInt(fill.slice(3, 5), 16);
  const b = parseInt(fill.slice(5, 7), 16);
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luminance > 0.6 ? "#0A1120" : "#F1F5F9";
}

/** Map a 0–1 magnitude onto the sequential ramp. */
export function sequentialStep(fraction: number): string {
  if (!Number.isFinite(fraction) || fraction <= 0) return CHROME.grid;
  const index = Math.min(SEQUENTIAL.length - 1, Math.floor(fraction * SEQUENTIAL.length));
  return SEQUENTIAL[index] ?? SEQUENTIAL[0];
}
