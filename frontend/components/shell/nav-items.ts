export interface NavItem {
  href: string;
  label: string;
  hint: string;
  /** Marks a section that is not part of the analysis itself. */
  badge?: string;
}

/**
 * The five analysis views in the order the pipeline runs, then the roadmap.
 *
 * Roadmap sits last and carries a badge because it is the one entry that is not
 * a result: everything above it is what the engine computed, and it is what the
 * engine would compute next. Without the mark it would read as a sixth stage.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Overview", hint: "The headline figure" },
  { href: "/telemetry", label: "Telemetry", hint: "What the feeds saw" },
  { href: "/frequency", label: "Frequency", hint: "How often attacks land" },
  { href: "/severity", label: "Severity", hint: "What one costs" },
  { href: "/simulation", label: "Simulation", hint: "What a year costs" },
  { href: "/roadmap", label: "Roadmap", hint: "Where this goes next", badge: "vision" },
] as const;
