/**
 * Typed client for the Django API.
 *
 * The frontend never computes risk figures: it renders what `risk_engine`
 * produced. Every response type declared here mirrors a serializer on the API
 * side, so a modeling change surfaces as a type error rather than a blank chart.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly path: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    // No Next-level caching: the API already memoizes every stage, so a repeat
    // request is cheap, and a cached response here would quietly outlive a
    // parameter change the reader just made.
    cache: "no-store",
  });

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status, path);
  }

  return (await response.json()) as T;
}

/** Attack vocabulary shared with the engine. */
export type AttackType =
  | "phishing"
  | "ransomware"
  | "credential_theft"
  | "data_breach"
  | "misconfiguration"
  | "ddos"
  | "insider_error"
  | "supply_chain"
  | "other";

export type SeverityClass = "low" | "medium" | "high" | "critical";

export interface HealthResponse {
  status: string;
  engine_version: string;
}

export interface TimeWindow {
  start: string;
  end: string;
  observed_days: number;
  annualization_factor: number;
}

export interface FrequencyParams {
  severity_threshold: SeverityClass;
  session_window_hours: number;
}

export interface AssetRow {
  asset_id: string;
  asset_type: string | null;
  business_criticality: number | null;
  environment: string | null;
  episodes: number;
  annual_rate: number;
  episodes_by_attack_type: Partial<Record<AttackType, number>>;
  /** Episode counts keyed by the ISO date of the week's Monday; quiet weeks are absent. */
  episodes_by_week: Record<string, number>;
}

export interface AssetInventoryResponse {
  assets: AssetRow[];
  episodes_by_criticality: Record<string, number>;
  episodes_by_environment: Record<string, number>;
  params: FrequencyParams;
}

export interface FeedReport {
  source: "siem" | "edr";
  rows_read: number;
  events: number;
  rows_out_of_window: number;
  rows_missing_timestamp: number;
  rows_incomplete_key: number;
  rows_unknown_severity: number;
}

export interface NormalizationReport {
  feeds: FeedReport[];
  window: TimeWindow;
  rows_read: number;
  total_events: number;
  events_in_both_feeds: number;
  duplicates_merged: number;
  inflation_avoided: number;
  unknown_asset_ids: string[];
  events_on_unknown_assets: number;
  explanation: string[];
}

export interface WeeklyBucket {
  week_start: string;
  siem_only: number;
  edr_only: number;
  both: number;
  merged: number;
}

export interface TelemetryResponse {
  normalization: NormalizationReport;
  summary: {
    weekly: WeeklyBucket[];
    severity_mix: Record<string, number>;
    events_by_source: Record<string, number>;
    techniques: Record<string, number>;
  };
}

export interface FrequencyResponse {
  /** Detected attack episodes per year. NOT the rate at which losses occur. */
  lambda_detected: number;
  lambda_detected_by_attack_type: Record<AttackType, number>;
  /** Loss-generating incidents per year — what the simulation prices. */
  lambda_incident: number | null;
  lambda_incident_by_attack_type: Partial<Record<AttackType, number>> | null;
  calibration: {
    p_materialize: number;
    base_rate_per_company_year: number;
    peer_companies: number;
    peer_incidents: number;
    observed_years: number;
  } | null;
  episodes: number;
  episodes_by_attack_type: Record<AttackType, number>;
  observed_days: number;
  window: TimeWindow;
  params: FrequencyParams;
  episodes_by_criticality: Record<string, number>;
  episodes_by_environment: Record<string, number>;
  unmapped_techniques: Record<string, number>;
  events_total: number;
  events_attack_grade: number;
  events_ungraded: number;
  events_without_asset: number;
  events_without_technique: number;
  explanation: string[];
}

export interface ParetoTail {
  threshold_eur: number;
  alpha: number;
  exceedances: number;
  ks_lognormal: number;
  ks_pareto: number;
  pareto_fits_tail_better: boolean;
}

export interface SeverityFit {
  attack_type: AttackType;
  mu: number;
  sigma: number;
  median_eur: number;
  mean_eur: number;
  observations: number;
  effective_n: number;
  used_pooled: boolean;
  diagnostics: {
    observations: number;
    effective_n: number;
    weighted_ks: number;
    qq_theoretical: number[];
    qq_empirical: number[];
    tail: ParetoTail | null;
    plot: {
      bin_edges_log: number[];
      bin_density: number[];
      curve_x_log: number[];
      curve_y: number[];
    };
  };
}

export interface SeverityResponse {
  fits: SeverityFit[];
  pooled: SeverityFit;
  peer_weighting: {
    target_sector: string;
    target_size: string;
    target_maturity: number;
    sector_match_weight: number;
    sector_other_weight: number;
    size_match_weight: number;
    size_other_weight: number;
    maturity_bandwidth: number;
  };
  min_effective_n: number;
  incidents_total: number;
  incidents_fitted: number;
  explanation: string[];
}

export interface ExceedanceCurve {
  kind: "aep" | "oep";
  exceedance_probability: number[];
  return_period_years: number[];
  loss_eur: number[];
}

export interface SimulationRequest {
  n_years?: number;
  seed?: number;
  severity_threshold?: SeverityClass;
  session_window_hours?: number;
  curve_points?: number;
  histogram_bins?: number;
  include_sensitivity?: boolean;
  sensitivity_years?: number;
}

export interface SimulationResponse {
  metrics: {
    aal: number;
    median: number;
    var_95: number;
    var_99: number;
    tvar_95: number;
    tvar_99: number;
    probability_of_no_loss: number;
    maximum: number;
  };
  aep_curve: ExceedanceCurve;
  oep_curve: ExceedanceCurve;
  histogram: { bin_edges_eur: number[]; counts: number[] };
  expected_loss_by_attack_type: Partial<Record<AttackType, number>>;
  expected_incidents_by_attack_type: Partial<Record<AttackType, number>>;
  n_years: number;
  seed: number;
  params: FrequencyParams;
  sensitivity: {
    cells: {
      severity_threshold: SeverityClass;
      session_window_hours: number;
      episodes: number;
      lambda_detected: number;
      lambda_incident: number;
      aal: number;
    }[];
    n_years: number;
    seed: number;
    aal_range: number[];
    spread_factor: number;
    explanation: string[];
  } | null;
  explanation: string[];
}

function query(params: Partial<FrequencyParams> | undefined): string {
  if (!params) return "";
  const search = new URLSearchParams();
  if (params.severity_threshold) search.set("severity_threshold", params.severity_threshold);
  if (params.session_window_hours !== undefined) {
    search.set("session_window_hours", String(params.session_window_hours));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  health: () => request<HealthResponse>("/api/health/"),
  assets: (params?: Partial<FrequencyParams>) =>
    request<AssetInventoryResponse>(`/api/assets/${query(params)}`),
  telemetry: () => request<TelemetryResponse>("/api/telemetry/summary/"),
  frequency: (params?: Partial<FrequencyParams>) =>
    request<FrequencyResponse>(`/api/frequency/${query(params)}`),
  severity: () => request<SeverityResponse>("/api/severity/"),
  simulate: (body: SimulationRequest = {}) =>
    request<SimulationResponse>("/api/simulate/", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

export { API_URL };
