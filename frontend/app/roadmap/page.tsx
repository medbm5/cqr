import { RoadmapLegend, RoadmapTimeline } from "@/components/roadmap/roadmap-timeline";
import { PageHeader } from "@/components/ui/page-header";
import { ROADMAP } from "@/lib/roadmap";

export const metadata = { title: "Roadmap · Citalid Risk Engine" };

/**
 * The product vision beyond the case study.
 *
 * The only page that touches no API: it renders `lib/roadmap.ts` and nothing
 * else, so it is static and works whether or not the engine is running.
 */
export default function RoadmapPage() {
  return (
    <>
      <PageHeader
        eyebrow="Vision"
        title="Roadmap"
        description="What this would become with more than four hours. Every item below was deprioritized by choice, not by ignorance — each says what exists today, what would change, and what the number or the product gains. The modeling entries are the ones argued in next_steps.md, including the reason each was left alone."
      />
      <RoadmapLegend />
      <RoadmapTimeline />

      <p className="mt-10 pl-8 text-xs leading-relaxed text-ink-muted">
        {ROADMAP.length} items. The order within each phase is by how much it would move the
        answer, not by how interesting it would be to build — which is why the cheapest item on
        the page sits at the top and the most interesting one sits at the bottom.
      </p>
    </>
  );
}
