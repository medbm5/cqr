#!/usr/bin/env python
"""Throwaway: print the frequency funnel, stage by stage.

Answers one question - where does each stage lose rows, and is the drop the size
it should be? Run it before and after any change to the clustering, and compare.

    python scripts/debug_frequency.py
    python scripts/debug_frequency.py --threshold critical --window 48
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from risk_engine.frequency import (  # noqa: E402
    FrequencyParams,
    estimate_frequency,
    sessionize,
)
from risk_engine.ingestion import (  # noqa: E402
    SeverityClass,
    load_assets,
    load_edr,
    load_siem,
    merge_feeds,
)
from risk_engine.severity import load_incidents  # noqa: E402


def main() -> int:
    """Print the funnel."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--threshold", default="high", choices=[c.value for c in SeverityClass])
    parser.add_argument("--window", type=float, default=24.0)
    args = parser.parse_args()

    siem = load_siem(args.data_dir / "feed_siem.csv")
    edr = load_edr(args.data_dir / "feed_edr.csv")
    assets = load_assets(args.data_dir / "asset_reference.csv")
    result = merge_feeds(siem, edr, assets=assets)

    params = FrequencyParams(
        severity_threshold=SeverityClass(args.threshold), session_gap_hours=args.window
    )
    events = result.events
    window = result.report.window

    graded = [e for e in events if e.severity_class is not None]
    attack_grade = [
        e
        for e in graded
        if e.severity_class is not None and e.severity_class.rank >= params.severity_threshold.rank
    ]
    clusterable = [e for e in attack_grade if e.asset_id is not None]

    incidents, _ = load_incidents(args.data_dir / "cyber_incidents.csv")
    episodes = sessionize(events, params=params)
    estimate = estimate_frequency(events, window, assets=assets, params=params, incidents=incidents)

    days = window.observed_days
    print(f"\nFREQUENCY FUNNEL   threshold >= {args.threshold}, {args.window:g}h window\n")
    print(f"{'stage':<42}{'count':>12}{'ratio':>12}")
    print("-" * 66)

    def row(label: str, count: float, previous: float | None) -> None:
        ratio = f"{previous / count:.2f}x" if previous and count else ""
        print(f"{label:<42}{count:>12,.0f}{ratio:>12}")

    raw = sum(f.rows_read for f in result.report.feeds)
    row("raw rows, SIEM", siem.report.rows_read, None)
    row("raw rows, EDR", edr.report.rows_read, None)
    row("raw rows, total", raw, None)
    row("distinct events after dedup", len(events), raw)
    row("  ... with a severity grade", len(graded), len(events))
    row(f"  ... attack-grade (>= {args.threshold})", len(attack_grade), len(graded))
    row("  ... and attributable to an asset", len(clusterable), len(attack_grade))
    row("episodes after clustering", len(episodes), len(clusterable))

    print("-" * 66)
    print(f"{'observed days':<42}{days:>12,}")
    print(f"{'episodes per day':<42}{len(episodes) / days:>12.2f}")
    print(f"{'episodes per asset per day':<42}{len(episodes) / days / len(assets):>12.3f}")
    compression = len(clusterable) / max(len(episodes), 1)
    print(f"{'COMPRESSION (attack-grade per episode)':<42}{compression:>12.2f}x")
    print(f"{'lambda_detected (episodes/yr)':<42}{estimate.lambda_detected:>12,.1f}")
    calibration = estimate.calibration
    if calibration is not None:
        base = calibration.base_rate
        print()
        print(f"{'peer base rate (incidents/co-yr)':<42}{base.incidents_per_company_year:>12.4f}")
        print(f"{'  from':<42}{base.incidents:>12,} incidents")
        print(f"{'  at':<42}{base.companies:>12,} organisations")
        print(f"{'  over':<42}{base.observed_years:>12.2f} years")
        print(f"{'p_materialize (fitted)':<42}{calibration.p_materialize:>12.3e}")
        print(f"{'lambda_incident (losses/yr)':<42}{calibration.lambda_incident:>12.4f}")

    print("\nepisodes per asset, top 5:")
    per_asset = Counter(e.asset_id for e in episodes)
    for asset_id, count in per_asset.most_common(5):
        print(f"  {asset_id}  {count:>5,} episodes  ({count / days:.2f}/day)")

    print("\nepisode duration:")
    durations = sorted(e.duration_hours for e in episodes)
    if durations:
        mid = durations[len(durations) // 2]
        print(f"  median {mid:.2f}h   max {durations[-1]:.1f}h")
        print(f"  single-event episodes: {sum(1 for e in episodes if e.event_count == 1):,}")
        print(
            f"  mean events per episode: {sum(e.event_count for e in episodes) / len(episodes):.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
