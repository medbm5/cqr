import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { HintTip } from "@/components/HintTip";
import { GLOSSARY } from "@/lib/glossary";

const AAL = GLOSSARY.aal;

/**
 * Waits for the tooltip to leave.
 *
 * `AnimatePresence` keeps the node mounted through its 150ms exit, so asserting
 * on the same tick would fail on an animation that is doing exactly its job.
 */
async function expectClosed() {
  await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
}

describe("HintTip", () => {
  it("shows nothing until asked", () => {
    render(<HintTip term="aal" />);

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });

  it("opens on hover and closes when the pointer leaves", async () => {
    const user = userEvent.setup();
    render(<HintTip term="aal" />);

    await user.hover(screen.getByRole("button"));
    expect(await screen.findByRole("tooltip")).toHaveTextContent(AAL.hint);

    await user.unhover(screen.getByRole("button"));
    await expectClosed();
  });

  it("opens on click and stays open when the pointer leaves", async () => {
    const user = userEvent.setup();
    render(<HintTip term="var95" />);
    const trigger = screen.getByRole("button");

    await user.click(trigger);
    expect(await screen.findByRole("tooltip")).toHaveTextContent(GLOSSARY.var95.hint);

    // A pinned tooltip survives the pointer moving away — the whole point of
    // click-to-open is reading the text without holding the mouse still.
    await user.unhover(trigger);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  });

  it("closes again on a second click", async () => {
    const user = userEvent.setup();
    render(<HintTip term="aal" />);
    const trigger = screen.getByRole("button");

    await user.click(trigger);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await user.click(trigger);
    await user.unhover(trigger);
    await expectClosed();
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<HintTip term="tvar99" />);
    const trigger = screen.getByRole("button");

    await user.click(trigger);
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await expectClosed();
    expect(trigger).toHaveFocus();
  });

  it("closes when something outside it is clicked", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <HintTip term="poisson" />
        <button type="button">elsewhere</button>
      </div>,
    );

    await user.click(screen.getByRole("button", { name: /What is/ }));
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "elsewhere" }));
    await expectClosed();
  });

  it("opens on keyboard focus, so the hint is not hover-only", async () => {
    const user = userEvent.setup();
    render(<HintTip term="seed" />);

    await user.tab();
    expect(screen.getByRole("button")).toHaveFocus();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(GLOSSARY.seed.hint);
  });

  it("points aria-describedby at the tooltip only while it is showing", async () => {
    const user = userEvent.setup();
    render(<HintTip term="ks" />);
    const trigger = screen.getByRole("button");

    expect(trigger).not.toHaveAttribute("aria-describedby");

    await user.click(trigger);
    const tooltip = screen.getByRole("tooltip");
    expect(trigger).toHaveAttribute("aria-describedby", tooltip.id);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  it("names the concept in the trigger's accessible name", () => {
    render(<HintTip term="kish_neff" />);

    expect(
      screen.getByRole("button", { name: `What is ${GLOSSARY.kish_neff.term}?` }),
    ).toBeInTheDocument();
  });
});
