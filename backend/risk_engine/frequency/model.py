"""Annualized attack frequency, and the trace explaining how it was reached."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import timedelta

from risk_engine.ingestion import Asset, NormalizationReport, SecurityEvent, TimeWindow
from risk_engine.severity.cleaning import Incident
from risk_engine.severity.peers import PeerWeightParams

from .attack_types import UNOBSERVABLE_ATTACK_TYPES, AttackType, attack_type_for
from .calibration import Calibration, calibrate, peer_weighted_base_rate
from .episodes import (
    DAYS_PER_YEAR,
    Episode,
    FrequencyParams,
    is_attack_grade,
    sessionize,
)


@dataclass(frozen=True, slots=True)
class AssetFrequency:
    """Episodes attributed to one asset, for the per-asset view in the UI.

    Attributes:
        asset_id: The asset.
        asset_type: From the asset reference, or `None` if the asset is unknown
            to it.
        business_criticality: From the asset reference, or `None`.
        environment: From the asset reference, or `None`.
        episodes: Episodes observed on the asset over the window.
        annual_rate: Those episodes annualized.
        episodes_by_attack_type: Episode counts per attack type, non-zero only.
        episodes_by_week: Episode counts keyed by the ISO date of the week's
            Monday, ascending. Weeks with no episode are absent rather than
            zero-filled: the caller knows the window and can tell a quiet week
            from one outside it.
    """

    asset_id: str
    asset_type: str | None
    business_criticality: int | None
    environment: str | None
    episodes: int
    annual_rate: float
    episodes_by_attack_type: Mapping[AttackType, int]
    episodes_by_week: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class FrequencyEstimate:
    """Annualized attack frequency, segmented by attack type.

    `lambda_*` values are Poisson rates in attacks per year, ready to be drawn
    from in the simulation stage.

    Attributes:
        lambda_detected: Annualized *detected attack episodes*, across all
            types. This is what the telemetry saw, not what it cost - almost
            every detected attack is stopped, noise, or one step of a chain that
            never completes.
        lambda_detected_by_attack_type: The same, per attack type.
        calibration: The bridge to loss-generating incidents, or `None` when no
            incident base was supplied to anchor against.
        lambda_incident: Annualized *loss-generating incidents* - the rate the
            simulation draws from, because it is the unit the severity model
            prices. `None` until calibrated.
        lambda_incident_by_attack_type: The incident rate split by the attack-type
            mix the telemetry observed. The telemetry cannot say how often losses
            occur, but it is the best evidence for *which kind* they are.
        episodes: Episodes observed over the window.
        episodes_by_attack_type: Episode counts behind each rate.
        observed_days: Length of the observation window, in calendar days.
        window: The window itself.
        params: The threshold and gap the estimate was produced with.
        by_asset: Per-asset breakdown, sorted by descending episode count.
        events_total: Canonical events the estimate started from.
        events_attack_grade: Events that passed the severity threshold.
        events_ungraded: Events excluded for carrying no severity at all.
        events_without_asset: Attack-grade events excluded for having no asset.
        events_without_technique: Attack-grade events whose feed reported no
            technique at all. They are counted as `OTHER`, and are the reason
            `OTHER` can hold more episodes than `unmapped_techniques` explains.
        unmapped_techniques: Named techniques that fell through to `OTHER`, with
            their attack-grade event counts.
        normalization: The ingestion report, when supplied, so the trace can
            start from raw CSV rows rather than from already-merged events.
    """

    lambda_detected: float
    lambda_detected_by_attack_type: Mapping[AttackType, float]
    episodes: int
    episodes_by_attack_type: Mapping[AttackType, int]
    observed_days: int
    window: TimeWindow
    params: FrequencyParams
    by_asset: tuple[AssetFrequency, ...]
    events_total: int
    events_attack_grade: int
    events_ungraded: int
    events_without_asset: int
    events_without_technique: int = 0
    unmapped_techniques: Mapping[str, int] = field(default_factory=dict)
    normalization: NormalizationReport | None = None
    calibration: Calibration | None = None

    @property
    def lambda_incident(self) -> float | None:
        """Loss-generating incidents per year, or `None` if uncalibrated."""
        return None if self.calibration is None else self.calibration.lambda_incident

    @property
    def lambda_incident_by_attack_type(self) -> Mapping[AttackType, float] | None:
        """The incident rate split by the observed attack-type mix.

        The mix is the telemetry's contribution: it cannot say how often a loss
        happens, but it is the best available evidence for what kind it would be.
        """
        if self.calibration is None or self.episodes == 0:
            return None
        rate = self.calibration.lambda_incident
        return {
            attack_type: rate * count / self.episodes
            for attack_type, count in self.episodes_by_attack_type.items()
        }

    @property
    def episodes_by_criticality(self) -> Mapping[int, int]:
        """Episode counts grouped by business criticality, for the UI."""
        counts: Counter[int] = Counter()
        for asset in self.by_asset:
            if asset.business_criticality is not None:
                counts[asset.business_criticality] += asset.episodes
        return dict(sorted(counts.items()))

    @property
    def episodes_by_environment(self) -> Mapping[str, int]:
        """Episode counts grouped by environment, for the UI."""
        counts: Counter[str] = Counter()
        for asset in self.by_asset:
            if asset.environment is not None:
                counts[asset.environment] += asset.episodes
        return dict(sorted(counts.items()))

    def to_explanation(self) -> list[str]:
        """Render the estimate as a numbered trace from raw rows to lambda.

        Returns:
            One numbered line per step - raw rows, unique events, attack-grade
            events, episodes, annualization - with indented detail beneath, so
            the arithmetic can be checked by hand at every stage.
        """
        lines: list[str] = []

        if self.normalization is not None:
            rows = self.normalization.rows_read
            lines.append(f"Read {rows:,} raw row(s) across both telemetry feeds.")
            lines.append(
                f"  Deduplicated to {self.normalization.total_events:,} unique event(s); "
                f"concatenating instead would have overstated the count by "
                f"{self.normalization.inflation_avoided:.1%}."
            )

        lines.append(f"Started from {self.events_total:,} unique event(s).")
        if self.events_ungraded:
            lines.append(
                f"  Excluded {self.events_ungraded:,} event(s) carrying no severity grade: "
                f"an ungraded event is not evidence of a benign one."
            )
        lines.append(
            f"Kept {self.events_attack_grade:,} attack-grade event(s), "
            f"severity at or above {self.params.severity_threshold.value} "
            f"({self.events_attack_grade / self.events_total:.1%} of unique events)."
            if self.events_total
            else "Kept 0 attack-grade event(s)."
        )
        if self.events_without_asset:
            lines.append(
                f"  Excluded {self.events_without_asset:,} of them for having no asset: "
                f"an attack that cannot be attributed to a machine cannot be clustered "
                f"per machine."
            )

        lines.append(
            f"Clustered them into {self.episodes:,} episode(s): same asset and attack "
            f"type, separated by at most {self.params.session_gap_hours:g}h of quiet."
        )
        if self.events_attack_grade:
            clustered = self.events_attack_grade - self.events_without_asset
            if self.episodes:
                lines.append(
                    f"  {clustered:,} event(s) collapsed to {self.episodes:,} attack(s), "
                    f"{clustered / self.episodes:.1f} event(s) per attack on average."
                )

        lines.append(
            f"Annualized over the observed window: {self.episodes:,} / "
            f"{self.observed_days} day(s) x {DAYS_PER_YEAR:g} = "
            f"{self.lambda_detected:,.1f} DETECTED attack(s) per year."
        )
        for attack_type, rate in sorted(
            self.lambda_detected_by_attack_type.items(), key=lambda item: -item[1]
        ):
            count = self.episodes_by_attack_type.get(attack_type, 0)
            note = ""
            if rate == 0.0 and attack_type in UNOBSERVABLE_ATTACK_TYPES:
                note = "  <- not observable from SIEM/EDR telemetry, not absent risk"
            lines.append(
                f"  {attack_type.value:18s} {count:>6,} episode(s)  lambda = {rate:>9,.1f}/yr{note}"
            )

        if self.calibration is not None:
            base = self.calibration.base_rate
            lines.append(
                f"Detected attacks are not losses. Calibrated against the external "
                f"base: {base.incidents:,} incident(s) at {base.companies:,} "
                f"organisation(s) over {base.observed_years:.2f} years, peer-weighted "
                f"to this company's profile, gives "
                f"{base.incidents_per_company_year:.4f} loss incident(s) per "
                f"organisation-year."
            )
            lines.append(
                f"  {self.lambda_detected:,.1f} detected episodes/yr x "
                f"p_materialize = {self.calibration.p_materialize:.2e} -> "
                f"{self.calibration.lambda_incident:.4f} loss incident(s)/yr."
            )
            lines.append(
                "  p_materialize is fitted, not assumed: it is whatever makes this "
                "estate's detection rate agree with what comparable organisations "
                "actually lose. A very small value says the sensors are noisy, not "
                "that the company is safe."
            )
            incident_mix = self.lambda_incident_by_attack_type or {}
            for attack_type, rate in sorted(incident_mix.items(), key=lambda item: -item[1]):
                if rate <= 0.0:
                    continue
                lines.append(
                    f"    {attack_type.value:18s} {rate:8.5f} incident(s)/yr  "
                    f"({self.episodes_by_attack_type.get(attack_type, 0):,} of "
                    f"{self.episodes:,} episodes)"
                )
        else:
            lines.append(
                "No incident base supplied, so the estimate stops at detected attacks. "
                "Pricing these directly would treat every detection as a breach."
            )

        if self.events_without_technique:
            lines.append(
                f"{self.events_without_technique:,} attack-grade event(s) carried no "
                f"technique at all and were counted as 'other'; together with the "
                f"unmapped techniques below, that is what 'other' contains."
            )

        if self.unmapped_techniques:
            listed = ", ".join(
                f"{technique} ({count:,})"
                for technique, count in sorted(
                    self.unmapped_techniques.items(), key=lambda item: -item[1]
                )
            )
            lines.append(
                f"{sum(self.unmapped_techniques.values()):,} attack-grade event(s) used "
                f"technique(s) with no attack-type mapping and were counted as "
                f"'other': {listed}."
            )

        numbered: list[str] = []
        step = 0
        for line in lines:
            if line.startswith("  "):
                numbered.append(line)
            else:
                step += 1
                numbered.append(f"{step}. {line}")
        return numbered


def estimate_frequency(
    events: Sequence[SecurityEvent],
    window: TimeWindow,
    *,
    assets: Sequence[Asset] = (),
    params: FrequencyParams | None = None,
    normalization: NormalizationReport | None = None,
    incidents: Sequence[Incident] = (),
    peer_params: PeerWeightParams | None = None,
) -> FrequencyEstimate:
    """Estimate annualized attack frequency from normalized telemetry.

    The chain is: unique events -> attack-grade events -> episodes -> annual
    rate, segmented by attack type. Each step is counted so the result can be
    reconstructed from its inputs.

    The annualization factor comes from the window the data actually spans, never
    from a constant: a longer telemetry export must change the answer by itself.

    Args:
        events: Canonical events from `risk_engine.ingestion`.
        window: The observation period, normally derived from those events.
        assets: The asset reference, used to attach criticality and environment
            to the per-asset breakdown. Optional.
        params: Severity threshold and session gap. Defaults to
            `FrequencyParams()` - attack-grade at `high`, 24-hour gap.
        normalization: The ingestion report, so the trace can begin at raw CSV
            rows. Optional.
        incidents: The external incident base. Supplying it calibrates detected
            attacks into loss-generating incidents, which is the rate the
            simulation needs; without it the estimate stops at what was detected.
        peer_params: The target profile the base rate is weighted against. The
            same one the severity model uses, so both halves describe the same
            company.

    Returns:
        The estimate, its per-attack-type segmentation and its audit trail.

    Raises:
        ValueError: If the window covers no days, which would make the rate
            infinite.
    """
    if window.observed_days <= 0:
        raise ValueError(f"observed window must cover at least one day, got {window.observed_days}")

    resolved = params if params is not None else FrequencyParams()

    attack_grade = [
        event for event in events if is_attack_grade(event, resolved.severity_threshold)
    ]
    unmapped: Counter[str] = Counter()
    for event in attack_grade:
        if attack_type_for(event.technique) is AttackType.OTHER and event.technique:
            unmapped[event.technique] += 1

    episodes = sessionize(events, params=resolved)
    scale = DAYS_PER_YEAR / window.observed_days

    counts: Counter[AttackType] = Counter(episode.attack_type for episode in episodes)
    episodes_by_type = {attack_type: counts.get(attack_type, 0) for attack_type in AttackType}
    lambda_by_type = {attack_type: count * scale for attack_type, count in episodes_by_type.items()}

    lambda_detected = len(episodes) * scale
    calibration: Calibration | None = None
    if incidents and lambda_detected > 0.0:
        calibration = calibrate(
            lambda_detected,
            peer_weighted_base_rate(
                incidents, peer_params if peer_params is not None else PeerWeightParams()
            ),
        )

    return FrequencyEstimate(
        lambda_detected=lambda_detected,
        lambda_detected_by_attack_type=lambda_by_type,
        episodes=len(episodes),
        episodes_by_attack_type=episodes_by_type,
        observed_days=window.observed_days,
        window=window,
        params=resolved,
        by_asset=_per_asset(episodes, assets, scale),
        events_total=len(events),
        events_attack_grade=len(attack_grade),
        events_ungraded=sum(1 for event in events if event.severity_class is None),
        events_without_asset=sum(1 for event in attack_grade if event.asset_id is None),
        events_without_technique=sum(
            1 for event in attack_grade if event.technique is None and event.asset_id
        ),
        unmapped_techniques=dict(unmapped),
        normalization=normalization,
        calibration=calibration,
    )


def _per_asset(
    episodes: Sequence[Episode], assets: Sequence[Asset], scale: float
) -> tuple[AssetFrequency, ...]:
    """Build the per-asset breakdown, joined to the asset reference where possible."""
    reference = {asset.asset_id: asset for asset in assets}
    grouped: dict[str, Counter[AttackType]] = {}
    weekly: dict[str, Counter[str]] = {}
    for episode in episodes:
        grouped.setdefault(episode.asset_id, Counter())[episode.attack_type] += 1
        started = episode.started_at.date()
        week = started - timedelta(days=started.weekday())
        weekly.setdefault(episode.asset_id, Counter())[week.isoformat()] += 1

    breakdown = [
        AssetFrequency(
            asset_id=asset_id,
            asset_type=reference[asset_id].asset_type if asset_id in reference else None,
            business_criticality=(
                reference[asset_id].business_criticality if asset_id in reference else None
            ),
            environment=reference[asset_id].environment if asset_id in reference else None,
            episodes=sum(by_type.values()),
            annual_rate=sum(by_type.values()) * scale,
            episodes_by_attack_type=dict(by_type.most_common()),
            episodes_by_week=dict(sorted(weekly[asset_id].items())),
        )
        for asset_id, by_type in grouped.items()
    ]
    return tuple(sorted(breakdown, key=lambda asset: (-asset.episodes, asset.asset_id)))
