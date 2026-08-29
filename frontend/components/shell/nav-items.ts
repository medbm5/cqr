/** The five views, in the order the analysis runs. */
export const NAV_ITEMS = [
  { href: "/", label: "Overview", hint: "The headline figure" },
  { href: "/telemetry", label: "Telemetry", hint: "What the feeds saw" },
  { href: "/frequency", label: "Frequency", hint: "How often attacks land" },
  { href: "/severity", label: "Severity", hint: "What one costs" },
  { href: "/simulation", label: "Simulation", hint: "What a year costs" },
] as const;
