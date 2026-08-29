import { Card, CardHeader } from "@/components/ui/card";

/** Split a trace line into its leading step number and the rest. */
function parseStep(line: string): { step: string | null; body: string } {
  const match = /^(\d+)\.\s+(.*)$/.exec(line);
  if (!match) return { step: null, body: line.trimStart() };
  return { step: match[1] ?? null, body: match[2] ?? "" };
}

/**
 * The engine's own audit trail, rendered as it was written.
 *
 * This is `to_explanation()` verbatim — the same numbered chain the CLI prints
 * and the JSON carries. Showing it here rather than paraphrasing it means the
 * page cannot drift from the engine: if the model changes its reasoning, this
 * changes with it.
 *
 * Numbers are set in a monospace face so the quantities in adjacent steps line
 * up and a reader can check the arithmetic down the column.
 */
export function ExplanationTrace({
  lines,
  title = "How this was computed",
  hint,
}: {
  lines: string[];
  title?: string;
  hint?: string;
}) {
  return (
    <Card>
      <CardHeader title={title} hint={hint ?? "Straight from the engine's audit trail"} />
      <ol className="divide-y divide-navy-800">
        {lines.map((line, index) => {
          const { step, body } = parseStep(line);
          const detail = step === null;

          return (
            <li
              key={index}
              className={[
                "flex gap-3 px-5 py-2.5",
                detail ? "border-t-0 bg-navy-950/40 pl-12" : "",
              ].join(" ")}
            >
              {step !== null ? (
                <span className="tabular mt-px w-5 shrink-0 text-right font-mono text-xs text-accent">
                  {step}
                </span>
              ) : null}
              <p
                className={[
                  "min-w-0 font-mono text-xs leading-relaxed",
                  detail ? "whitespace-pre-wrap text-ink-muted" : "text-ink-secondary",
                ].join(" ")}
              >
                {body}
              </p>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
