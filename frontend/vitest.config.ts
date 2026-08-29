import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vitest/config";

/**
 * The frontend's test runner.
 *
 * jsdom rather than a browser: what these tests assert is behaviour and
 * accessibility wiring — which element is focusable, what `aria-describedby`
 * points at, what Escape does — none of which needs a real compositor.
 */
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": resolve(__dirname, ".") } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
  },
});
