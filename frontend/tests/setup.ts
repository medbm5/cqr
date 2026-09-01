import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

/**
 * Observers jsdom does not implement.
 *
 * `IntersectionObserver` is what framer-motion's `whileInView` mounts on, and
 * `ResizeObserver` is how the roadmap card learns whether its impact text is
 * actually clipped. Without them the components throw on mount and every
 * assertion below fails for a reason that has nothing to do with the component.
 *
 * The intersection stub reports the element as visible immediately, so
 * scroll-triggered content is present for assertions rather than waiting for a
 * scroll that will never happen in a headless DOM. The resize stub reports
 * nothing: jsdom gives every element a height of zero, so no measurement it
 * could deliver would be meaningful.
 */
class ImmediateIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: ReadonlyArray<number> = [];

  constructor(private readonly callback: IntersectionObserverCallback) {}

  observe(target: Element): void {
    this.callback(
      [{ isIntersecting: true, target } as IntersectionObserverEntry],
      this as IntersectionObserver,
    );
  }

  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

class NoopResizeObserver implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

globalThis.IntersectionObserver ??= ImmediateIntersectionObserver;
globalThis.ResizeObserver ??= NoopResizeObserver;
