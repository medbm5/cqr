"""Serializers: the only place engine objects are reshaped for the wire.

The engine speaks in frozen dataclasses keyed by enums. JSON does not, so the
translation happens here rather than in a view - which keeps the views to
parse, call, serialize, and keeps every field of the contract in one file that
drf-spectacular can read.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from risk_engine.ingestion import SeverityClass
from risk_engine.simulation import DEFAULT_SENSITIVITY_YEARS

from .pipeline import DEFAULT_YEARS, MAX_YEARS, MIN_YEARS

#: Maximum points on an exceedance curve returned by the API.
MAX_CURVE_POINTS = 500
DEFAULT_CURVE_POINTS = 200


def _by_value(mapping: dict[Any, Any]) -> dict[str, Any]:
    """Re-key a mapping from enum members to their string values."""
    return {getattr(key, "value", key): value for key, value in mapping.items()}


# --------------------------------------------------------------------- shared


class ExplanationMixin(serializers.Serializer):
    """Adds the numbered audit trail every stage carries."""

    explanation = serializers.SerializerMethodField(
        help_text="Numbered, human-readable trace of how these figures were produced."
    )

    def get_explanation(self, obj: Any) -> list[str]:
        """Read the trace off whichever object carries it."""
        return list(obj.to_explanation())


class TimeWindowSerializer(serializers.Serializer):
    """The observation period the telemetry covers."""

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    observed_days = serializers.IntegerField()
    annualization_factor = serializers.FloatField()


class FrequencyParamsSerializer(serializers.Serializer):
    """The two frequency conventions, echoed back on every response."""

    severity_threshold = serializers.SerializerMethodField()
    session_window_hours = serializers.FloatField(source="session_gap_hours")

    def get_severity_threshold(self, obj: Any) -> str:
        """The threshold as its string value."""
        return str(obj.severity_threshold.value)


# --------------------------------------------------------------------- assets


class AssetSerializer(serializers.Serializer):
    """One asset, with the attack activity attributed to it."""

    asset_id = serializers.CharField()
    asset_type = serializers.CharField(allow_null=True)
    business_criticality = serializers.IntegerField(allow_null=True)
    environment = serializers.CharField(allow_null=True)
    episodes = serializers.IntegerField()
    annual_rate = serializers.FloatField()
    episodes_by_attack_type = serializers.SerializerMethodField()

    def get_episodes_by_attack_type(self, obj: Any) -> dict[str, int]:
        """Episode counts per attack type, non-zero only."""
        return _by_value(dict(obj.episodes_by_attack_type))


class AssetInventorySerializer(serializers.Serializer):
    """The estate, and where the attacks landed on it."""

    assets = AssetSerializer(many=True, source="by_asset")
    episodes_by_criticality = serializers.DictField(child=serializers.IntegerField())
    episodes_by_environment = serializers.DictField(child=serializers.IntegerField())
    params = FrequencyParamsSerializer()


# ------------------------------------------------------------------ telemetry


class WeeklyBucketSerializer(serializers.Serializer):
    """Distinct events in one week, split by which feed saw them."""

    week_start = serializers.DateField()
    siem_only = serializers.IntegerField()
    edr_only = serializers.IntegerField()
    both = serializers.IntegerField()
    merged = serializers.IntegerField()


class FeedReportSerializer(serializers.Serializer):
    """What one feed contributed, and what was set aside."""

    source = serializers.SerializerMethodField()
    rows_read = serializers.IntegerField()
    events = serializers.IntegerField()
    rows_out_of_window = serializers.IntegerField()
    rows_missing_timestamp = serializers.IntegerField()
    rows_incomplete_key = serializers.IntegerField()
    rows_unknown_severity = serializers.IntegerField()

    def get_source(self, obj: Any) -> str:
        """The feed name."""
        return str(obj.source.value)


class NormalizationReportSerializer(ExplanationMixin):
    """The accounting from raw rows to distinct events."""

    feeds = FeedReportSerializer(many=True)
    window = TimeWindowSerializer()
    rows_read = serializers.IntegerField()
    total_events = serializers.IntegerField()
    events_in_both_feeds = serializers.IntegerField()
    duplicates_merged = serializers.IntegerField()
    inflation_avoided = serializers.FloatField()
    unknown_asset_ids = serializers.ListField(child=serializers.CharField())
    events_on_unknown_assets = serializers.IntegerField()


class TelemetrySummarySerializer(serializers.Serializer):
    """Shape of the telemetry over the window."""

    weekly = WeeklyBucketSerializer(many=True)
    severity_mix = serializers.DictField(child=serializers.IntegerField())
    events_by_source = serializers.DictField(child=serializers.IntegerField())
    techniques = serializers.DictField(child=serializers.IntegerField())


class TelemetryResponseSerializer(serializers.Serializer):
    """Everything the telemetry page needs."""

    normalization = NormalizationReportSerializer()
    summary = TelemetrySummarySerializer()


# ------------------------------------------------------------------ frequency


class FrequencyResponseSerializer(ExplanationMixin):
    """Annualized attack rates, segmented by type."""

    lambda_total = serializers.FloatField()
    lambda_by_attack_type = serializers.SerializerMethodField()
    episodes = serializers.IntegerField()
    episodes_by_attack_type = serializers.SerializerMethodField()
    observed_days = serializers.IntegerField()
    window = TimeWindowSerializer()
    params = FrequencyParamsSerializer()
    episodes_by_criticality = serializers.DictField(child=serializers.IntegerField())
    episodes_by_environment = serializers.DictField(child=serializers.IntegerField())
    unmapped_techniques = serializers.DictField(child=serializers.IntegerField())
    events_total = serializers.IntegerField()
    events_attack_grade = serializers.IntegerField()
    events_ungraded = serializers.IntegerField()
    events_without_asset = serializers.IntegerField()
    events_without_technique = serializers.IntegerField()

    def get_lambda_by_attack_type(self, obj: Any) -> dict[str, float]:
        """Annual rate per attack type, every type present."""
        return _by_value(dict(obj.lambda_by_attack_type))

    def get_episodes_by_attack_type(self, obj: Any) -> dict[str, int]:
        """Episode count per attack type."""
        return _by_value(dict(obj.episodes_by_attack_type))


# ------------------------------------------------------------------- severity


class ParetoTailSerializer(serializers.Serializer):
    """The Pareto rival fitted to the upper tail."""

    threshold_eur = serializers.FloatField()
    alpha = serializers.FloatField()
    exceedances = serializers.IntegerField()
    ks_lognormal = serializers.FloatField()
    ks_pareto = serializers.FloatField()
    pareto_fits_tail_better = serializers.BooleanField()


class DistributionPlotSerializer(serializers.Serializer):
    """Weighted histogram and fitted density, on the log scale."""

    bin_edges_log = serializers.ListField(child=serializers.FloatField())
    bin_density = serializers.ListField(child=serializers.FloatField())
    curve_x_log = serializers.ListField(child=serializers.FloatField())
    curve_y = serializers.ListField(child=serializers.FloatField())


class FitDiagnosticsSerializer(serializers.Serializer):
    """Evidence for and against one fit."""

    observations = serializers.IntegerField()
    effective_n = serializers.FloatField()
    weighted_ks = serializers.FloatField()
    qq_theoretical = serializers.ListField(child=serializers.FloatField())
    qq_empirical = serializers.ListField(child=serializers.FloatField())
    tail = ParetoTailSerializer(allow_null=True)
    plot = DistributionPlotSerializer()


class SeverityFitSerializer(serializers.Serializer):
    """One attack type's loss distribution."""

    attack_type = serializers.SerializerMethodField()
    mu = serializers.FloatField(source="params.mu")
    sigma = serializers.FloatField(source="params.sigma")
    median_eur = serializers.FloatField(source="params.median_eur")
    mean_eur = serializers.FloatField(source="params.mean_eur")
    observations = serializers.IntegerField(source="own_observations")
    effective_n = serializers.FloatField(source="own_effective_n")
    used_pooled = serializers.BooleanField()
    diagnostics = FitDiagnosticsSerializer()

    def get_attack_type(self, obj: Any) -> str:
        """The attack type as its string value."""
        return str(obj.attack_type.value)


class PeerWeightingSerializer(serializers.Serializer):
    """The target profile the peer weights were built from."""

    target_sector = serializers.CharField()
    target_size = serializers.CharField()
    target_maturity = serializers.FloatField()
    sector_match_weight = serializers.FloatField()
    sector_other_weight = serializers.FloatField()
    size_match_weight = serializers.FloatField()
    size_other_weight = serializers.FloatField()
    maturity_bandwidth = serializers.FloatField()


class SeverityResponseSerializer(ExplanationMixin):
    """The severity model and the evidence behind it."""

    fits = serializers.SerializerMethodField()
    pooled = SeverityFitSerializer()
    peer_weighting = PeerWeightingSerializer(source="peer_params")
    min_effective_n = serializers.FloatField()
    incidents_total = serializers.IntegerField()
    incidents_fitted = serializers.IntegerField()

    def get_fits(self, obj: Any) -> list[dict[str, Any]]:
        """One fit per attack type, ordered by name."""
        ordered = sorted(obj.fits.items(), key=lambda item: item[0].value)
        return [SeverityFitSerializer(fit).data for _, fit in ordered]


# ----------------------------------------------------------------- simulation


class SimulationRequestSerializer(serializers.Serializer):
    """What a caller may ask the simulation for."""

    n_years = serializers.IntegerField(
        required=False,
        default=DEFAULT_YEARS,
        min_value=MIN_YEARS,
        max_value=MAX_YEARS,
        help_text=(
            f"Years to simulate, {MIN_YEARS:,} to {MAX_YEARS:,}. More years resolve a "
            f"finer tail and take proportionally longer."
        ),
    )
    seed = serializers.IntegerField(
        required=False, default=42, min_value=0, help_text="Seed; the run is reproducible from it."
    )
    severity_threshold = serializers.ChoiceField(
        required=False,
        default=SeverityClass.HIGH.value,
        choices=[member.value for member in SeverityClass],
        help_text="Minimum severity for an event to count as an attack.",
    )
    session_window_hours = serializers.FloatField(
        required=False,
        default=24.0,
        min_value=0.25,
        max_value=720.0,
        help_text="Quiet period that ends an episode.",
    )
    curve_points = serializers.IntegerField(
        required=False,
        default=DEFAULT_CURVE_POINTS,
        min_value=2,
        max_value=MAX_CURVE_POINTS,
        help_text=f"Points per exceedance curve, at most {MAX_CURVE_POINTS}.",
    )
    include_sensitivity = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to include the 3x3 parameter sweep, which costs nine more runs.",
    )
    sensitivity_years = serializers.IntegerField(
        required=False,
        default=DEFAULT_SENSITIVITY_YEARS,
        min_value=MIN_YEARS,
        max_value=MAX_YEARS,
        help_text="Years per sensitivity cell.",
    )


class LossMetricsSerializer(serializers.Serializer):
    """Headline figures of the annual loss distribution."""

    aal = serializers.FloatField()
    median = serializers.FloatField()
    var_95 = serializers.FloatField()
    var_99 = serializers.FloatField()
    tvar_95 = serializers.FloatField()
    tvar_99 = serializers.FloatField()
    probability_of_no_loss = serializers.FloatField()
    maximum = serializers.FloatField()


class ExceedanceCurveSerializer(serializers.Serializer):
    """A loss-versus-probability curve as parallel plottable arrays."""

    kind = serializers.CharField(help_text="'aep' (annual total) or 'oep' (largest single loss).")
    exceedance_probability = serializers.ListField(child=serializers.FloatField())
    return_period_years = serializers.ListField(child=serializers.FloatField())
    loss_eur = serializers.ListField(child=serializers.FloatField())


class SensitivityCellSerializer(serializers.Serializer):
    """One point of the parameter sweep."""

    severity_threshold = serializers.SerializerMethodField()
    session_window_hours = serializers.FloatField()
    episodes = serializers.IntegerField()
    lambda_total = serializers.FloatField()
    aal = serializers.FloatField()

    def get_severity_threshold(self, obj: Any) -> str:
        """The threshold as its string value."""
        return str(obj.severity_threshold.value)


class SensitivityGridSerializer(ExplanationMixin):
    """AAL across the two frequency conventions."""

    cells = SensitivityCellSerializer(many=True)
    n_years = serializers.IntegerField()
    seed = serializers.IntegerField()
    aal_range = serializers.SerializerMethodField()
    spread_factor = serializers.FloatField()

    def get_aal_range(self, obj: Any) -> list[float]:
        """Lowest and highest AAL in the grid."""
        return list(obj.aal_range)


class SimulationResponseSerializer(serializers.Serializer):
    """The simulated loss distribution and everything behind it."""

    metrics = LossMetricsSerializer()
    aep_curve = ExceedanceCurveSerializer()
    oep_curve = ExceedanceCurveSerializer()
    expected_loss_by_attack_type = serializers.DictField(child=serializers.FloatField())
    expected_incidents_by_attack_type = serializers.DictField(child=serializers.FloatField())
    n_years = serializers.IntegerField()
    seed = serializers.IntegerField()
    params = FrequencyParamsSerializer()
    sensitivity = SensitivityGridSerializer(allow_null=True)
    explanation = serializers.ListField(child=serializers.CharField())
