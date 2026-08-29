"""Loading and normalization of the raw inputs.

Responsibilities:

* read the SIEM, EDR and asset reference files into typed, immutable records;
* normalize severity onto a single 0-1 scale across feeds, using the EDR cut
  points derived in `notebooks/01_eda.ipynb` section 4;
* deduplicate events observed in both telemetry feeds (same asset, same MITRE
  technique, same timestamp), keeping the worst observed severity;
* account for every row, so the difference between "rows in the CSVs" and
  "events the model saw" is always explainable.

Typical use::

    siem = load_siem(data_dir / "feed_siem.csv")
    edr = load_edr(data_dir / "feed_edr.csv")
    assets = load_assets(data_dir / "asset_reference.csv")
    result = merge_feeds(siem, edr, assets=assets)

    for line in result.to_explanation():
        print(line)

pandas is an implementation detail of the loaders; nothing it produces crosses
this package boundary.
"""

from .loaders import LoadedFeed, load_assets, load_edr, load_siem, observed_window
from .merge import IngestionResult, merge_feeds
from .models import (
    SEVERITY_SCORES,
    Asset,
    SecurityEvent,
    SeverityClass,
    Source,
    as_utc,
)
from .report import FeedReport, NormalizationReport, TimeWindow
from .scales import (
    EDR_CUT_POINTS,
    EDR_MAX_RISK,
    EDR_SENTINEL_RISK,
    SIEM_SEVERITY_LABELS,
    severity_from_edr_risk,
    severity_from_siem_label,
)
from .summary import (
    TelemetrySummary,
    WeeklyBucket,
    summarize_telemetry,
)

__all__ = [
    "EDR_CUT_POINTS",
    "EDR_MAX_RISK",
    "EDR_SENTINEL_RISK",
    "SEVERITY_SCORES",
    "SIEM_SEVERITY_LABELS",
    "Asset",
    "FeedReport",
    "IngestionResult",
    "LoadedFeed",
    "NormalizationReport",
    "SecurityEvent",
    "SeverityClass",
    "Source",
    "TelemetrySummary",
    "TimeWindow",
    "WeeklyBucket",
    "as_utc",
    "load_assets",
    "load_edr",
    "load_siem",
    "merge_feeds",
    "observed_window",
    "severity_from_edr_risk",
    "severity_from_siem_label",
    "summarize_telemetry",
]
