import type { ReactNode } from "react";

/** The title block every view opens with: what this page answers, and why. */
export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <header className="mb-8">
      {eyebrow ? (
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-accent">{eyebrow}</p>
      ) : null}
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1>
      {description ? (
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-secondary">{description}</p>
      ) : null}
      {children}
    </header>
  );
}
