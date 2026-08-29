/**
 * Loading placeholders.
 *
 * Sized to the content they stand in for, so the layout does not jump when the
 * real figure arrives — a stat tile that grows by 20px on load is a worse
 * experience than one that waited.
 */

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={[
        "rounded bg-navy-800",
        "bg-[linear-gradient(90deg,theme(colors.navy.800)_0%,theme(colors.navy.700)_50%,theme(colors.navy.800)_100%)]",
        "bg-[length:200%_100%] animate-shimmer",
        className,
      ].join(" ")}
    />
  );
}

/** A stat tile's shape, while its number is in flight. */
export function StatTileSkeleton() {
  return (
    <div className="rounded-xl border border-navy-800 bg-navy-900 p-5 shadow-card">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-9 w-32" />
      <Skeleton className="mt-3 h-3 w-40" />
    </div>
  );
}

/** A panel's shape, while its contents load. */
export function CardSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <div className="rounded-xl border border-navy-800 bg-navy-900 p-5 shadow-card">
      <Skeleton className="h-4 w-40" />
      <div className="mt-5 space-y-3">
        {Array.from({ length: lines }, (_, index) => (
          <Skeleton key={index} className="h-3" />
        ))}
      </div>
    </div>
  );
}
