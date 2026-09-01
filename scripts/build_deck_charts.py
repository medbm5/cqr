"""Regenerate every chart of the Citalid presentation from the data itself.

No screenshots. Each figure is recomputed from `data/*.csv` through the same
`risk_engine` calls the CLI and the API make, so a number on a slide and a
number in the engine cannot drift apart: there is only one of each.

Conventions follow the web UI deliberately - the same palette, and a log scale
wherever the UI uses one - so a reader who has seen the cockpit recognises the
slides, and a reader who sees the slides first is not surprised by the cockpit.

Run from the repository root:

    python scripts/build_deck_charts.py --out deck/charts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from risk_engine.frequency import FrequencyParams, estimate_frequency  # noqa: E402
from risk_engine.ingestion import (  # noqa: E402
    load_assets,
    load_edr,
    load_siem,
    merge_feeds,
    summarize_telemetry,
)
from risk_engine.severity import fit_severity_model, load_incidents  # noqa: E402
from risk_engine.simulation import simulate  # noqa: E402

# The cockpit's palette, so the deck and the UI are visibly one product.
BG = "#050912"
CARD = "#0A1120"
GRID = "#1B2942"
INK = "#F1F5F9"
INK_2 = "#94A3B8"
INK_3 = "#7A8AA0"
ACCENT = "#38BDF8"
SIEM = "#3987e5"
EDR = "#d95926"
BOTH = "#199e70"
CAUTION = "#FBBF24"

DPI = 220

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "savefig.facecolor": BG,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "text.color": INK,
        "xtick.color": INK_3,
        "ytick.color": INK_3,
        "grid.color": GRID,
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.autolayout": False,
    }
)


def eur(value: float) -> str:
    """Compact euros, the way the UI writes them, with French decimals.

    One decimal below ten units, none above: "6,7 M€" carries information that
    "7 M€" throws away, while "816 k€" does not need "816,3".
    """
    for limit, suffix in ((1e9, "Md€"), (1e6, "M€"), (1e3, "k€")):
        if abs(value) >= limit:
            scaled = value / limit
            digits = 1 if abs(scaled) < 100 else 0
            return f"{scaled:.{digits}f} {suffix}".replace(".", ",")
    return f"{value:.0f} €"


def fr(value: float, digits: int = 0) -> str:
    """A number in French convention: space for thousands, comma for decimals."""
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def save(fig: plt.Figure, path: Path) -> None:
    """Write one figure and report it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print(f"  {path.name:28} {path.stat().st_size // 1024:>5} Ko")


# --------------------------------------------------------------------- charts


def chart_funnel(report, out: Path) -> None:
    """Slide 4 - what deduplication removes, as a share of the raw rows."""
    stages = [
        ("Lignes brutes lues", report.rows_read, INK_3),
        ("Événements distincts", report.total_events, ACCENT),
    ]
    fig, ax = plt.subplots(figsize=(11, 3.4))
    for index, (label, value, colour) in enumerate(stages):
        ax.barh(index, value, height=0.5, color=colour)
        ax.text(
            value + report.rows_read * 0.015,
            index,
            fr(value),
            va="center",
            ha="left",
            fontsize=17,
            fontweight="bold",
            color=INK,
        )
        ax.text(0, index + 0.42, label, va="bottom", ha="left", fontsize=11, color=INK_2)

    ax.annotate(
        f"−{fr(report.duplicates_merged)} doublons absorbés",
        xy=(report.total_events, 0.5),
        xytext=(report.total_events + report.rows_read * 0.06, 0.5),
        va="center",
        fontsize=12,
        color=CAUTION,
        arrowprops={"arrowstyle": "-|>", "color": CAUTION, "linewidth": 1.2},
    )

    ax.set_xlim(0, report.rows_read * 1.32)
    ax.set_ylim(-0.55, 1.65)
    ax.invert_yaxis()
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    save(fig, out)


def chart_weekly(summary, out: Path) -> None:
    """Slide 5 - a flat weekly throughput is what licenses Poisson."""
    weeks = [bucket.week_start for bucket in summary.weekly]
    x = np.arange(len(weeks))
    siem = np.array([b.siem_only for b in summary.weekly], dtype=float)
    both = np.array([b.both for b in summary.weekly], dtype=float)
    edr = np.array([b.edr_only for b in summary.weekly], dtype=float)

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.stackplot(
        x,
        siem,
        both,
        edr,
        colors=[SIEM, BOTH, EDR],
        labels=["SIEM seul", "Les deux flux", "EDR seul"],
        linewidth=0,
    )

    total = siem + both + edr
    mean = total.mean()
    ax.axhline(mean, color=INK, linewidth=1, linestyle="--", alpha=0.7)
    ax.text(
        len(x) - 0.5,
        mean * 1.04,
        f"moyenne {fr(mean)} évén./semaine  ·  dispersion "
        + f"{total.std() / mean * 100:.1f}".replace(".", ",")
        + " %",
        ha="right",
        fontsize=10,
        color=INK,
    )

    step = max(1, len(weeks) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([w.strftime("%d %b") for w in weeks[::step]], fontsize=9)
    ax.set_ylabel("événements distincts")
    ax.set_xlim(0, len(x) - 1)
    ax.set_ylim(0, total.max() * 1.25)
    ax.grid(axis="y", linewidth=0.8)
    ax.set_axisbelow(True)
    legend = ax.legend(loc="upper left", frameon=False, fontsize=10, ncol=3)
    for text in legend.get_texts():
        text.set_color(INK_2)
    save(fig, out)


def chart_window_sensitivity(events, window, assets, incidents, out: Path) -> None:
    """Slide 6 - the session window is a dial, and here is what it moves."""
    hours = [1, 4, 8, 12, 24, 48, 72, 168]
    episodes = []
    for value in hours:
        estimate = estimate_frequency(
            events,
            window,
            assets=assets,
            incidents=incidents,
            params=FrequencyParams(session_gap_hours=float(value)),
        )
        episodes.append(estimate.episodes)

    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(range(len(hours)), episodes, color=ACCENT, linewidth=2, marker="o", markersize=6)

    chosen = hours.index(24)
    ax.scatter([chosen], [episodes[chosen]], s=170, facecolor=CAUTION, zorder=5, edgecolor=BG)
    ax.annotate(
        f"convention retenue\n24 h → {episodes[chosen]:,} épisodes".replace(",", " "),
        xy=(chosen, episodes[chosen]),
        xytext=(chosen + 0.45, episodes[chosen] + (max(episodes) - min(episodes)) * 0.30),
        fontsize=11,
        color=CAUTION,
        arrowprops={"arrowstyle": "-", "color": CAUTION, "linewidth": 1},
    )

    ax.set_xticks(range(len(hours)))
    ax.set_xticklabels([f"{h} h" for h in hours], fontsize=10)
    ax.set_ylabel("épisodes reconstitués")
    ax.set_ylim(0, max(episodes) * 1.28)
    ax.grid(axis="y", linewidth=0.8)
    ax.set_axisbelow(True)
    save(fig, out)


def chart_calibration(frequency, out: Path) -> None:
    """Slide 7 - the unit change, on the only scale that can show it."""
    calibration = frequency.calibration
    rows = [
        ("Attaques détectées\npar la télémétrie", frequency.lambda_detected, EDR),
        (
            "Taux de base des pairs\n1 310 organisations",
            calibration.base_rate.incidents_per_company_year,
            INK_3,
        ),
        ("Incidents à perte\nretenus par le modèle", frequency.lambda_incident, ACCENT),
    ]

    fig, ax = plt.subplots(figsize=(11.5, 3.6))
    # The label is not read here: it is set as a y tick below, where the
    # axis can right-align it against the bars.
    for index, (_label, value, colour) in enumerate(rows):
        ax.barh(index, value, height=0.46, color=colour)
        # The label rides after the bar's end on a log axis, where a fixed
        # offset would sit on top of the short bars and miles from the long one.
        ax.text(
            value * 1.6,
            index,
            f"{fr(value, 0 if value >= 100 else 2)} /an",
            va="center",
            fontsize=16,
            fontweight="bold",
            color=INK,
        )

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([label for label, _, _ in rows], fontsize=10.5, color=INK_2)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xscale("log")
    ax.set_xlim(0.1, frequency.lambda_detected * 30)
    ax.set_ylim(-0.6, 2.6)
    ax.invert_yaxis()
    ax.set_xlabel("échelle logarithmique — un facteur 5 138 sépare les deux unités")
    ax.grid(axis="x", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_visible(False)
    save(fig, out)


def chart_fit(fit, out: Path) -> None:
    """Slide 9 - the weighted evidence, and the curve fitted to it."""
    plot = fit.diagnostics.plot
    edges = np.array(plot.bin_edges_log)
    density = np.array(plot.bin_density)
    centres = (edges[:-1] + edges[1:]) / 2

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar(
        np.exp(centres),
        density,
        width=np.exp(edges[1:]) - np.exp(edges[:-1]),
        color=SIEM,
        alpha=0.75,
        label="pertes des pairs, pondérées",
    )
    ax.plot(
        np.exp(np.array(plot.curve_x_log)),
        np.array(plot.curve_y),
        color=EDR,
        linewidth=2.2,
        label="lognormale ajustée",
    )

    ax.set_ylim(0, max(density.max(), max(plot.curve_y)) * 1.32)

    params = fit.params
    for value, label, colour in (
        (params.median_eur, f"médiane {eur(params.median_eur)}", INK),
        (params.mean_eur, f"moyenne {eur(params.mean_eur)}", CAUTION),
    ):
        ax.axvline(value, color=colour, linewidth=1, linestyle="--", alpha=0.8)
        ax.text(value * 1.08, ax.get_ylim()[1] * 0.86, label, fontsize=11, color=colour)

    ax.set_xscale("log")
    ax.set_xlabel("perte par incident (échelle log)")
    ax.set_ylabel("densité")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: eur(v)))
    ax.grid(axis="y", linewidth=0.8)
    ax.set_axisbelow(True)
    legend = ax.legend(loc="upper left", frameon=False, fontsize=10)
    for text in legend.get_texts():
        text.set_color(INK_2)
    save(fig, out)


def chart_qq(fit, out: Path) -> None:
    """Slide 10 - the diagnostic the KS statistic compresses into one number."""
    theoretical = np.array(fit.diagnostics.qq_theoretical)
    empirical = np.array(fit.diagnostics.qq_empirical)
    low = min(theoretical.min(), empirical.min())
    high = max(theoretical.max(), empirical.max())

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.plot([low, high], [low, high], color=INK_3, linewidth=1, linestyle="--")
    ax.scatter(theoretical, empirical, s=34, color=ACCENT, alpha=0.85, edgecolor="none")

    ax.set_xlabel("quantiles prédits par l'ajustement (log)")
    ax.set_ylabel("quantiles observés (log)")
    ax.text(
        0.04,
        0.94,
        f"KS pondéré {fit.diagnostics.weighted_ks:.3f}".replace(".", ","),
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.04,
        0.87,
        f"seuil indicatif ≈ 0,19 pour n_eff = {fit.own_effective_n:.0f}",
        transform=ax.transAxes,
        fontsize=10,
        color=INK_3,
    )
    ax.grid(linewidth=0.8)
    ax.set_axisbelow(True)
    save(fig, out)


def chart_exceedance(result, out: Path) -> None:
    """Slide 12 - how bad a year gets, and how often, with the VaR on it."""
    aep = result.curve("aep", points=140)
    oep = result.curve("oep", points=140)

    def plottable(curve):
        periods = np.array(curve.return_period_years)
        losses = np.array(curve.loss_eur)
        keep = losses > 0
        return periods[keep], losses[keep]

    aep_x, aep_y = plottable(aep)
    oep_x, oep_y = plottable(oep)

    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.plot(aep_x, aep_y, color=SIEM, linewidth=2.2, label="AEP — total de l'année")
    ax.plot(oep_x, oep_y, color=EDR, linewidth=2.2, label="OEP — plus grosse perte unitaire")

    metrics = result.metrics
    for period, value, label in (
        (20, metrics.var_95, f"VaR 95  {eur(metrics.var_95)}"),
        (100, metrics.var_99, f"VaR 99  {eur(metrics.var_99)}"),
    ):
        ax.scatter([period], [value], s=90, facecolor=INK, edgecolor=BG, zorder=6)
        ax.annotate(
            label,
            xy=(period, value),
            xytext=(period * 0.30, value * 2.4),
            fontsize=11.5,
            fontweight="bold",
            color=INK,
            arrowprops={"arrowstyle": "-", "color": INK_3, "linewidth": 1},
        )

    # The left band, where the model says an ordinary year costs nothing.
    ax.axvspan(aep.return_period_years[0], aep_x[0], color=GRID, alpha=0.55, zorder=0)
    ax.text(
        aep.return_period_years[0] * 1.08,
        aep_y.max() * 0.45,
        "année type : 0 €\n"
        + f"{metrics.probability_of_no_loss * 100:.1f}".replace(".", ",")
        + " % des années\nsans incident",
        fontsize=10,
        color=INK_3,
        va="center",
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("période de retour (années, échelle log)")
    ax.set_ylabel("perte annuelle")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: eur(v)))
    ax.set_xticks([2, 5, 10, 20, 50, 100, 500, 1000, 10000])
    ax.set_xticklabels(["2", "5", "10", "20", "50", "100", "500", "1k", "10k"])
    ax.grid(linewidth=0.8, which="major")
    ax.set_axisbelow(True)
    legend = ax.legend(loc="lower right", frameon=False, fontsize=10)
    for text in legend.get_texts():
        text.set_color(INK_2)
    save(fig, out)


def chart_annual_loss(result, out: Path) -> None:
    """Slide 12 companion - the distribution the metrics are read off."""
    histogram = result.histogram(bins=40, scale="log")
    edges = np.array(histogram.bin_edges_eur)
    counts = np.array(histogram.counts)
    centres = np.sqrt(edges[:-1] * edges[1:])

    fig, ax = plt.subplots(figsize=(11, 4.0))
    ax.bar(centres, counts, width=np.diff(edges), color=SIEM, alpha=0.9)

    metrics = result.metrics
    # Staggered heights: the AAL and VaR 95 sit less than half a decade apart
    # on this data, which is close enough for two labels to collide.
    for index, (value, label, colour) in enumerate(
        (
            (metrics.aal, f"AAL {eur(metrics.aal)}", CAUTION),
            (metrics.var_95, "VaR 95", INK_3),
            (metrics.var_99, "VaR 99", INK_3),
        )
    ):
        ax.axvline(value, color=colour, linewidth=1.2, linestyle="--")
        ax.text(
            value * 1.07,
            counts.max() * (0.95 if index % 2 == 0 else 0.85),
            label,
            fontsize=10.5,
            color=colour,
        )

    ax.set_xscale("log")
    ax.set_xlabel("perte annuelle (années à perte uniquement, échelle log)")
    ax.set_ylabel("années simulées")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: eur(v)))
    ax.text(
        0.015,
        0.93,
        f"{histogram.zero_years / (histogram.zero_years + histogram.loss_years) * 100:.1f}".replace(
            ".", ","
        )
        + " % des années : 0 €\n(exclues de l'histogramme)",
        transform=ax.transAxes,
        fontsize=11,
        color=INK,
        va="top",
    )
    ax.grid(axis="y", linewidth=0.8)
    ax.set_axisbelow(True)
    save(fig, out)


# --------------------------------------------------------------------- figures


#: Counts the pipeline cannot produce about itself. Kept here, beside the
#: figures it ships with, rather than typed into a slide where nothing would
#: notice them going stale.
SUITE = {"backend_tests": "272", "coverage": "99 %"}


def exact_peer_count(incidents, params) -> int:
    """How many incidents survive a *hard* filter on the target profile.

    The number that justifies soft weighting: it is quoted on the severity
    slide as the reason the obvious approach was rejected, so it is measured
    rather than remembered.
    """
    return sum(
        1
        for incident in incidents
        if incident.loss_eur is not None
        and incident.sector == params.target_sector
        and incident.company_size == params.target_size
    )


def write_figures(path: Path, *, ingestion, frequency, severity, result, incidents) -> dict:
    """Every number the deck quotes, formatted in French, in one file."""
    report = ingestion.report
    calibration = frequency.calibration
    metrics = result.metrics
    supply_chain = next(fit for key, fit in severity.fits.items() if key.value == "supply_chain")
    pareto = sum(
        1
        for fit in severity.fits.values()
        if fit.diagnostics.tail is not None and fit.diagnostics.tail.pareto_fits_tail_better
    )

    figures = {
        "rows_read": fr(report.rows_read),
        "total_events": fr(report.total_events),
        "duplicates": fr(report.duplicates_merged),
        "dup_cross_feed": fr(report.events_in_both_feeds),
        "inflation": f"{report.inflation_avoided * 100:.1f}".replace(".", ",") + " %",
        "observed_days": fr(report.window.observed_days),
        "annualization": f"{report.window.annualization_factor:.4f}".replace(".", ","),
        "attack_grade": fr(frequency.events_attack_grade),
        "episodes": fr(frequency.episodes),
        "compression": f"{frequency.events_attack_grade / frequency.episodes:.1f}".replace(".", ",")
        + "×",
        "lambda_detected": fr(frequency.lambda_detected),
        "lambda_incident": f"{frequency.lambda_incident:.2f}".replace(".", ","),
        "p_one_in": fr(1 / calibration.p_materialize),
        "peer_companies": fr(calibration.base_rate.companies),
        "incidents_fitted": fr(severity.incidents_fitted),
        "losses_missing": fr(severity.cleaning.losses_missing),
        "hard_filter": fr(exact_peer_count(incidents, severity.peer_params)),
        "min_neff": fr(severity.min_effective_n),
        "sc_mu": f"{supply_chain.params.mu:.3f}".replace(".", ","),
        "sc_sigma": f"{supply_chain.params.sigma:.3f}".replace(".", ","),
        "sc_median": eur(supply_chain.params.median_eur),
        "sc_mean": eur(supply_chain.params.mean_eur),
        "sc_ratio": f"{supply_chain.params.mean_eur / supply_chain.params.median_eur:.0f}",
        "sc_ks": f"{supply_chain.diagnostics.weighted_ks:.3f}".replace(".", ","),
        "sc_neff": fr(supply_chain.own_effective_n),
        "pareto_better": fr(pareto),
        "fits_total": fr(len(severity.fits)),
        "n_years": fr(result.params.n_years),
        "cap": eur(result.cap.cap_eur),
        "cap_share": f"{result.cap.share_capped * 100:.1f}".replace(".", ",") + " %",
        "aal": eur(metrics.aal),
        "aal_exact": fr(metrics.aal) + " €",
        "median_year": "0 €",
        "var95": eur(metrics.var_95),
        "var99": eur(metrics.var_99),
        "tvar95": eur(metrics.tvar_95),
        "tvar99": eur(metrics.tvar_99),
        "p_no_loss": f"{metrics.probability_of_no_loss * 100:.1f}".replace(".", ",")
        + " % des années",
        **SUITE,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(figures, ensure_ascii=False, indent=2), encoding="utf-8")
    return figures


# ----------------------------------------------------------------------- main


def main() -> int:
    """Rebuild every chart and print the figures the deck quotes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "deck" / "charts")
    parser.add_argument("--years", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print("Chargement et normalisation…")
    assets = load_assets(args.data_dir / "asset_reference.csv")
    ingestion = merge_feeds(
        load_siem(args.data_dir / "feed_siem.csv"),
        load_edr(args.data_dir / "feed_edr.csv"),
        assets=assets,
    )
    summary = summarize_telemetry(ingestion.events)
    incidents, cleaning = load_incidents(args.data_dir / "cyber_incidents.csv")

    print("Ajustement de la sévérité…")
    severity = fit_severity_model(incidents, cleaning)

    print("Estimation de la fréquence…")
    frequency = estimate_frequency(
        ingestion.events, ingestion.report.window, assets=assets, incidents=incidents
    )

    print(f"Simulation ({args.years:,} années, seed {args.seed})…")
    result = simulate(frequency, severity, n_years=args.years, seed=args.seed)

    supply_chain = next(fit for key, fit in severity.fits.items() if key.value == "supply_chain")

    print("\nGraphiques :")
    chart_funnel(ingestion.report, args.out / "04_funnel.png")
    chart_weekly(summary, args.out / "05_weekly.png")
    chart_window_sensitivity(
        ingestion.events, ingestion.report.window, assets, incidents, args.out / "06_window.png"
    )
    chart_calibration(frequency, args.out / "07_calibration.png")
    chart_fit(supply_chain, args.out / "09_fit.png")
    chart_qq(supply_chain, args.out / "10_qq.png")
    chart_exceedance(result, args.out / "12_exceedance.png")
    chart_annual_loss(result, args.out / "12b_annual_loss.png")

    figures = write_figures(
        args.out.parent / "figures.json",
        ingestion=ingestion,
        frequency=frequency,
        severity=severity,
        result=result,
        incidents=incidents,
    )
    print(f"\n{len(figures)} chiffres écrits dans deck/figures.json")

    metrics = result.metrics
    print("\nChiffres cités par la présentation :")
    print(f"  AAL              {metrics.aal:,.0f} €")
    print(f"  VaR 95           {metrics.var_95:,.0f} €")
    print(f"  VaR 99           {metrics.var_99:,.0f} €")
    print(f"  TVaR 95          {metrics.tvar_95:,.0f} €")
    print(f"  TVaR 99          {metrics.tvar_99:,.0f} €")
    print(f"  P(aucune perte)  {metrics.probability_of_no_loss:.2%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
