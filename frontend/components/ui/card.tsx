import type { ReactNode } from "react";

import { HintTip } from "@/components/HintTip";
import type { GlossaryKey } from "@/lib/glossary";

/**
 * The one surface every panel sits on.
 *
 * `interactive` adds the hover lift. It is opt-in rather than automatic: a card
 * that rises under the cursor is promising it does something, and a static
 * panel that lifts is a lie the user only discovers by clicking.
 */
export function Card({
  children,
  className = "",
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <div
      className={[
        "rounded-xl border border-navy-800 bg-navy-900 shadow-card",
        interactive
          ? "transition duration-200 ease-out hover:-translate-y-0.5 hover:border-navy-700 hover:shadow-lift"
          : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </div>
  );
}

/**
 * Title row of a card: a name, and optionally a note explaining the figure.
 *
 * `hint` is the note that rides in the corner; `term` is the ⓘ beside the title.
 * Both can be present — one says what this card shows, the other says what the
 * concept means.
 */
export function CardHeader({
  title,
  hint,
  term,
}: {
  title: string;
  hint?: string;
  term?: GlossaryKey;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-navy-800 px-5 py-4">
      <h2 className="text-sm font-semibold tracking-tight text-ink">
        {title}
        {term ? <HintTip term={term} /> : null}
      </h2>
      {hint ? <p className="text-xs text-ink-muted">{hint}</p> : null}
    </div>
  );
}
