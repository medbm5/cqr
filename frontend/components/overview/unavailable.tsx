import { Card } from "@/components/ui/card";

/**
 * Shown when the API cannot be reached.
 *
 * A dashboard that renders zeros when its source is down is worse than one that
 * says so: a zero AAL is a number a reader can act on, and it would be a lie.
 */
export function ApiUnavailable({ detail }: { detail: string }) {
  return (
    <Card className="p-6">
      <h2 className="text-sm font-semibold text-ink">The risk engine is not reachable</h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-secondary">
        No figures are shown rather than placeholder zeros — a zero loss is a number
        someone could act on.
      </p>
      <p className="mt-4 text-xs text-ink-muted">
        Start the API with <code className="text-accent">make api</code>, then reload. Set{" "}
        <code className="text-accent">NEXT_PUBLIC_API_URL</code> if it is not on
        localhost:8000.
      </p>
      <p className="mt-3 font-mono text-xs text-ink-muted">{detail}</p>
    </Card>
  );
}
