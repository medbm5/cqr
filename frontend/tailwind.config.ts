import type { Config } from "tailwindcss";

/**
 * "Risk cockpit" palette: deep navy surfaces, a single accent.
 *
 * The accent marks signal only — the active route, a focused control, the live
 * value in a chart. It is never decoration, so that when it appears the eye is
 * right to go there. Loss severity scales are defined per chart, never here, so
 * the accent keeps one meaning.
 *
 * Every ink token clears WCAG AA (4.5:1) on both `navy.900` and `navy.800`:
 * primary 17.2:1, secondary 7.4:1, muted 5.4:1, accent 8.8:1.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#050912", // page
          900: "#0A1120", // card
          850: "#0E1526", // raised
          800: "#111C31", // border, hovered card
          700: "#1B2942", // strong border
          600: "#26374F",
        },
        ink: {
          DEFAULT: "#F1F5F9",
          secondary: "#94A3B8",
          muted: "#7A8AA0",
        },
        accent: {
          DEFAULT: "#38BDF8",
          strong: "#0EA5E9",
          soft: "#0B2E44",
        },
        positive: "#34D399",
        caution: "#FBBF24",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.4)",
        lift: "0 12px 32px -12px rgb(0 0 0 / 0.7)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
