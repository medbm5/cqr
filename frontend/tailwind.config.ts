import type { Config } from "tailwindcss";

/**
 * "Risk cockpit" palette: deep navy surfaces, a single accent used only to mark
 * signal (selected series, active thresholds, primary actions). Loss severity
 * scales are defined per-chart, never here, so the accent stays unambiguous.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#050912",
          900: "#0A1120",
          800: "#111C31",
          700: "#1B2942",
        },
        accent: {
          DEFAULT: "#38BDF8",
          muted: "#0EA5E9",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
