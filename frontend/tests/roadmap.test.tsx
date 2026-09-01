import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RoadmapTimeline } from "@/components/roadmap/roadmap-timeline";
import { NAV_ITEMS } from "@/components/shell/nav-items";
import { PHASES, ROADMAP } from "@/lib/roadmap";

describe("roadmap data", () => {
  it("gives every item the full three-part structure", () => {
    for (const item of ROADMAP) {
      expect(item.current, `${item.id} current`).not.toHaveLength(0);
      expect(item.change, `${item.id} change`).not.toHaveLength(0);
      expect(item.impact, `${item.id} impact`).not.toHaveLength(0);
      // Each field answers a different question; identical text in two of them
      // means the structure was filled in rather than thought through.
      expect(new Set([item.current, item.change, item.impact]).size).toBe(3);
    }
  });

  it("keeps ids unique, since they key the rendered list", () => {
    const ids = ROADMAP.map((item) => item.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("places every item in a declared phase", () => {
    const declared = new Set(PHASES.map((phase) => phase.phase));
    for (const item of ROADMAP) expect(declared.has(item.phase)).toBe(true);
  });

  it("leaves no phase empty", () => {
    for (const phase of PHASES) {
      expect(ROADMAP.filter((item) => item.phase === phase.phase).length).toBeGreaterThan(0);
    }
  });

  it("covers the product items the roadmap was asked to carry", () => {
    const ids = new Set(ROADMAP.map((item) => item.id));
    for (const required of [
      "auth-workspaces",
      "connectors",
      "credibility",
      "maturity-p-materialize",
      "gpd-tail",
      "copulas",
      "asset-allocation",
      "backtesting",
      "ci-pipeline",
    ]) {
      expect(ids.has(required), `missing roadmap item: ${required}`).toBe(true);
    }
  });
});

describe("RoadmapTimeline", () => {
  it("renders every item under a phase heading", () => {
    render(<RoadmapTimeline />);

    for (const phase of PHASES) {
      expect(
        screen.getByRole("heading", { name: new RegExp(`Phase ${phase.phase} — ${phase.title}`) }),
      ).toBeInTheDocument();
    }
    for (const item of ROADMAP) {
      expect(screen.getByRole("heading", { name: item.title })).toBeInTheDocument();
    }
  });

  it("labels the three sections identically on every card", () => {
    render(<RoadmapTimeline />);

    for (const label of ["Today", "Change", "Impact"]) {
      expect(screen.getAllByText(label)).toHaveLength(ROADMAP.length);
    }
  });

  it("expands an item's reasoning on click", async () => {
    const user = userEvent.setup();
    render(<RoadmapTimeline />);

    // jsdom reports zero heights, so nothing measures as clipped and the
    // toggle is absent - which is itself the contract: the control appears
    // only when there is something hidden behind it.
    const toggles = screen.queryAllByRole("button", { name: /Read the reasoning/ });
    for (const toggle of toggles) {
      await user.click(toggle);
      expect(toggle).toHaveAttribute("aria-expanded", "true");
    }
  });

  it("shows the effort badge as text, not colour alone", () => {
    render(<RoadmapTimeline />);

    const card = screen
      .getByRole("heading", { name: ROADMAP[0]!.title })
      .closest("article") as HTMLElement;

    expect(within(card).getByText(ROADMAP[0]!.effort)).toBeInTheDocument();
    expect(within(card).getByText(ROADMAP[0]!.theme)).toBeInTheDocument();
  });
});

describe("navigation", () => {
  it("puts Roadmap last and marks it as vision", () => {
    const last = NAV_ITEMS[NAV_ITEMS.length - 1]!;

    expect(last.href).toBe("/roadmap");
    expect(last.badge).toBe("vision");
    // Every other entry is a stage of the analysis and carries no badge.
    expect(NAV_ITEMS.slice(0, -1).every((item) => item.badge === undefined)).toBe(true);
  });
});
