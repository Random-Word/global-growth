#!/usr/bin/env python3
"""Analysis 25: "Can a Marshall Plan be repeated?"

The report argues that durable cross-border redistribution is politically
fragile, and that the binding constraint in poor/fragile states is ABSORPTIVE
CAPACITY and INSTITUTIONS, not capital. This script tests that claim with a
small-N illustrative historical comparison:

  Marshall Plan (1948-1952)  -> SUCCESS rebuilding high-capacity economies.
  Iraq reconstruction (2003+) -> weak/fragile outcome from a low base.
  Afghanistan reconstruction (2001-2021) -> state collapse despite huge spend.

The point is NOT a statistical test (N=3, war/occupation confounds, voluntary
aid vs. military reconstruction differ, hand-assigned ordinal outcomes). It is
an existence demonstration that comparable or larger reconstruction outlays did
NOT ensure success under radically different institutional/security conditions,
because the recipients differed in institutional/human capital -- not primarily
in dollars received. We do NOT claim spending caused worse outcomes.

Outputs:
- charts/112_marshall_vs_reconstruction_spending.png
- charts/113_spending_vs_outcome.png
- data/processed/marshall_reconstruction_comparison.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
CHARTS = BASE / "charts"
CHARTS.mkdir(exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams.update(
    {
        "figure.figsize": (12, 7),
        "font.size": 11,
        "axes.titlesize": 13,
        "figure.dpi": 150,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
    }
)

# ---------------------------------------------------------------------------
# CPI deflators (BLS CPI-U, annual averages; index 1982-84 = 100).
# Used to convert nominal program dollars to 2024 real dollars.
# Source: U.S. Bureau of Labor Statistics, CPI-U All Urban Consumers,
#   annual average series (https://www.bls.gov/cpi/). 2024 annual avg ~313.7.
# 1948 ~24.1; 1950 ~24.1; 1952 ~26.6 (ERP midpoint ~1950 used as the basis).
# Spend-year MIDPOINTS used for reconstruction (price-basis transparency):
#   Iraq recon ran ~2003-2012 -> ~2007 midpoint (CPI ~207.3).
#   Afghan recon ran ~2002-2014 -> ~2011 midpoint (CPI ~224.9).
# NOTE: the broad Brown "Costs of War" totals are ALREADY cumulative,
# multi-year, current-dollar-style budgetary estimates (including future
# veterans' care and interest). They are reported AS PUBLISHED and are NOT
# CPI-deflated here -- doing so would double-count inflation and is wrong.
# ---------------------------------------------------------------------------
CPI_2024 = 313.7  # BLS CPI-U 2024 annual average (approx).
CPI_1950 = 24.1  # BLS CPI-U 1950 annual average (ERP midpoint basis).
CPI_2007 = 207.3  # BLS CPI-U 2007 annual average (Iraq recon midpoint).
CPI_2011 = 224.9  # BLS CPI-U 2011 annual average (Afghan recon midpoint).


def to_2024(nominal_bn: float, cpi_then: float) -> float:
    """Convert nominal USD billions at a given CPI to 2024 USD billions."""
    return nominal_bn * CPI_2024 / cpi_then


# ---------------------------------------------------------------------------
# CURATED PROGRAM FACTS. Every figure carries its source in a comment.
# ---------------------------------------------------------------------------

# MARSHALL PLAN (European Recovery Program), 1948-1952.
#   Nominal outlay ~$13.3B. Source: standard ERP totals (US State Dept /
#   ERP appropriations; widely cited $13.0-13.3B over FY1948-1952).
MARSHALL_NOMINAL_BN = 13.3
#   Real 2024$ range. Low end = simple CPI-U deflation from ~1950 (~$173B).
#   Many "real" estimates land ~$150B depending on base year / deflator choice;
#   we report a range and use the CPI midpoint as the point estimate.
MARSHALL_REAL_LOW_BN = 150.0  # commonly cited CPI-adjusted low end.
MARSHALL_REAL_CPI_BN = to_2024(MARSHALL_NOMINAL_BN, CPI_1950)  # ~$173B.
#   ~1.1% of US GDP/yr over the period; ~5% cumulative of one year's US GDP.
#   Source: US GDP ~$280B (1950); 13.3/280 ~= 4.75% cumulative ~= ~1.1%/yr x4.
MARSHALL_PCT_US_GDP_CUM = 100.0 * MARSHALL_NOMINAL_BN / 280.0  # ~4.75%.
#   As share of recipient GDP: ~2-2.5%/yr (OEEC member GDP, widely cited).
MARSHALL_PCT_RECIPIENT_GDP_YR = 2.5
#   HISTORIOGRAPHY (De Long & Eichengreen 1993, "The Marshall Plan: History's
#   Most Successful Structural Adjustment Program", NBER WP 3899): the marginal
#   effect of Marshall aid was likely INSTITUTIONAL / POLICY-CATALYTIC --
#   restoring well-functioning markets, unblocking intra-European coordination,
#   and tilting political economy toward mixed-economy, pro-growth settlements --
#   rather than a brute capital injection (the transfer was too small relative to
#   recipient GDP to drive recovery on its own). This STRENGTHENS the absorptive-
#   capacity reading: the Marshall Plan worked because of the institutions and
#   policy bargains it catalysed, NOT mainly because of the money.

# IRAQ reconstruction, 2003 onward.
#   US reconstruction appropriations ~$60B. Source: SIGIR (Special Inspector
#   General for Iraq Reconstruction) Final Report, "Learning From Iraq" (2013):
#   ~$60B in US reconstruction funds.
IRAQ_RECON_NOMINAL_BN = 60.0
#   BROAD CUMULATIVE BUDGETARY WAR COST ~$2.1T (as published). Source: Brown
#   University Costs of War project (Watson Institute). This is a multi-year,
#   current-dollar-style cumulative estimate including future veterans' care and
#   interest. Reported AS PUBLISHED; NOT CPI-deflated; NOT directly comparable to
#   reconstruction outlays.
IRAQ_TOTAL_COST_BN = 2100.0

# AFGHANISTAN reconstruction, 2001-2021.
#   US reconstruction ~$145B (much of it Afghan security forces). Source:
#   SIGAR (Special Inspector General for Afghanistan Reconstruction),
#   "What We Need to Learn" (2021) / quarterly reports: ~$145B appropriated for
#   reconstruction (excludes the ~$837B in direct DoD war spending).
AFGHAN_RECON_NOMINAL_BN = 145.0
#   BROAD CUMULATIVE BUDGETARY WAR COST ~$2.3T (as published). Source: Brown
#   University Costs of War project. Cumulative current-dollar-style estimate
#   including future veterans' care and interest. Reported AS PUBLISHED; NOT
#   CPI-deflated; NOT directly comparable to reconstruction outlays.
AFGHAN_TOTAL_COST_BN = 2300.0


# ---------------------------------------------------------------------------
# OUTCOME and BASELINE indices (0-1), with justification in comments.
# IMPORTANT: these are QUALITATIVE AUTHOR-JUDGMENT ordinal markers, NOT measured
# quantities. They are used only as explicitly-labeled illustrative scores to
# convey ordering. We do NOT fit a trend or infer that spending caused outcomes.
# ---------------------------------------------------------------------------

# OUTCOME index (durable success of the intervention, 0=collapse, 1=full success):
#   Marshall ~0.95: Western Europe GDP recovered to/above prewar by ~1951 and
#     entered sustained growth ("Trente Glorieuses"); democracies consolidated.
#   Iraq ~0.35: weak institutions, years of insurgency/instability; GDP and
#     governance gains real but fragile and uneven (SIGIR; World Bank WGI).
#   Afghanistan ~0.05: state collapse Aug 2021; most development gains reversed
#     (SIGAR final lessons-learned).
OUTCOME_INDEX = {"Marshall Plan": 0.95, "Iraq": 0.35, "Afghanistan": 0.05}

# RECIPIENT PRE-INTERVENTION institutional/human-capital baseline (0-1):
#   Western Europe 1948 ~0.90: high literacy (>90%), deep industrial base,
#     professional bureaucracies, prior rule-of-law and democratic/market
#     traditions (interrupted, not absent). Source: Maddison GDP/cap; UNESCO
#     literacy; economic-history consensus.
#   Iraq 2003 ~0.35: middle-income oil economy but personalist dictatorship,
#     hollowed institutions, sanctions damage, sectarian fracture; literacy
#     ~74%. Source: World Bank; UNESCO.
#   Afghanistan 2001 ~0.10: among world's poorest, literacy ~30%, minimal
#     central-state capacity after decades of war. Source: World Bank; UNESCO.
BASELINE_INDEX = {"Marshall Plan": 0.90, "Iraq": 0.35, "Afghanistan": 0.10}

# Indicative baseline indicators for the mechanism panel (pre-intervention).
#   Adult literacy (%) and approximate real GDP/cap (2024-ish USD scale) just
#   before each intervention. Sources: UNESCO literacy; Maddison Project /
#   World Bank GDP per capita (rough, comparison-only).
BASELINE_INDICATORS = pd.DataFrame(
    [
        # label, literacy_pct, gdp_pc_usd (indicative pre-intervention real)
        ("W. Europe 1948", 90.0, 6000.0),  # Maddison: ~$5-7k 1948 W. Europe.
        ("Iraq 2003", 74.0, 4500.0),  # World Bank/UNESCO ~2003.
        ("Afghanistan 2001", 30.0, 1100.0),  # World Bank/UNESCO ~2001.
    ],
    columns=["recipient", "literacy_pct", "gdp_pc_usd"],
)


def build_table() -> pd.DataFrame:
    """Assemble the comparison table with real-dollar conversions.

    Price basis: reconstruction figures are CPI-U deflated from their SPEND-YEAR
    MIDPOINTS to 2024 USD (real consumption-equivalent). The broad Brown
    "Costs of War" totals are reported AS PUBLISHED (cumulative budgetary,
    current-dollar-style) and are deliberately NOT deflated.
    """
    marshall_real = MARSHALL_REAL_CPI_BN
    iraq_recon_real = to_2024(IRAQ_RECON_NOMINAL_BN, CPI_2007)
    afghan_recon_real = to_2024(AFGHAN_RECON_NOMINAL_BN, CPI_2011)
    # Broad war totals: AS PUBLISHED, no deflation (already cumulative budgetary).
    iraq_total_aspub = IRAQ_TOTAL_COST_BN
    afghan_total_aspub = AFGHAN_TOTAL_COST_BN

    rows = [
        {
            "program": "Marshall Plan",
            "period": "1948-1952",
            "figure_type": "reconstruction aid",
            "nominal_usd_bn": MARSHALL_NOMINAL_BN,
            "real_2024_usd_bn": round(marshall_real, 1),
            "real_2024_low_bn": MARSHALL_REAL_LOW_BN,
            "pct_us_gdp": round(MARSHALL_PCT_US_GDP_CUM, 2),
            "nominal_source": "ERP appropriations FY1948-52 (US State Dept)",
            "years_covered": "1948-1952",
            "categories_included": "grants + loans (European Recovery Program)",
            "categories_excluded": "US military spending; later NATO aid",
            "deflator_method": "CPI-U, 1950 midpoint -> 2024",
            "recipient_baseline_index": BASELINE_INDEX["Marshall Plan"],
            "outcome_index_author": OUTCOME_INDEX["Marshall Plan"],
            "source_notes": (
                "ERP ~$13.3B nominal (State Dept totals); CPI-U 1950->2024 ~$173B; "
                "ALSO ~1.1%/yr US GDP (~4.75% cumulative); recipient ~2-2.5%/yr GDP. "
                "De Long & Eichengreen 1993: marginal effect institutional/policy-"
                "catalytic, not brute capital."
            ),
        },
        {
            "program": "Iraq reconstruction",
            "period": "2003-2012",
            "figure_type": "reconstruction aid",
            "nominal_usd_bn": IRAQ_RECON_NOMINAL_BN,
            "real_2024_usd_bn": round(iraq_recon_real, 1),
            "real_2024_low_bn": np.nan,
            "pct_us_gdp": np.nan,
            "nominal_source": "SIGIR Final Report 'Learning From Iraq' (2013)",
            "years_covered": "2003-2012",
            "categories_included": "US reconstruction appropriations",
            "categories_excluded": "DoD war/occupation spending; veterans; interest",
            "deflator_method": "CPI-U, 2007 spend-year midpoint -> 2024",
            "recipient_baseline_index": BASELINE_INDEX["Iraq"],
            "outcome_index_author": OUTCOME_INDEX["Iraq"],
            "source_notes": "SIGIR ~$60B recon; CPI-U 2007 midpoint->2024.",
        },
        {
            "program": "Afghanistan reconstruction",
            "period": "2001-2021",
            "figure_type": "reconstruction + security-force aid",
            "nominal_usd_bn": AFGHAN_RECON_NOMINAL_BN,
            "real_2024_usd_bn": round(afghan_recon_real, 1),
            "real_2024_low_bn": np.nan,
            "pct_us_gdp": np.nan,
            "nominal_source": "SIGAR 'What We Need to Learn' (2021) / quarterly",
            "years_covered": "2002-2014 (spend-weighted)",
            "categories_included": "reconstruction + Afghan security forces fund",
            "categories_excluded": "~$837B direct DoD war spending; veterans; interest",
            "deflator_method": "CPI-U, 2011 spend-year midpoint -> 2024",
            "recipient_baseline_index": BASELINE_INDEX["Afghanistan"],
            "outcome_index_author": OUTCOME_INDEX["Afghanistan"],
            "source_notes": "SIGAR ~$145B recon (incl. security forces); CPI-U 2011 midpoint->2024.",
        },
        {
            "program": "Iraq broad war cost (as published)",
            "period": "2003+",
            "figure_type": "broad cumulative budgetary war cost",
            "nominal_usd_bn": IRAQ_TOTAL_COST_BN,
            "real_2024_usd_bn": np.nan,
            "as_published_usd_bn": round(iraq_total_aspub, 1),
            "real_2024_low_bn": np.nan,
            "pct_us_gdp": np.nan,
            "nominal_source": "Brown U. Costs of War (Watson Institute)",
            "years_covered": "2003+ (cumulative, incl. future obligations)",
            "categories_included": "war/occupation + veterans' care + interest",
            "categories_excluded": "n/a (broad total)",
            "deflator_method": "AS PUBLISHED; NOT CPI-deflated (already cumulative)",
            "recipient_baseline_index": np.nan,
            "outcome_index_author": np.nan,
            "source_notes": (
                "Brown Costs of War: Iraq ~$2.1T cumulative budgetary, as published. "
                "NOT directly comparable to reconstruction outlays."
            ),
        },
        {
            "program": "Afghanistan broad war cost (as published)",
            "period": "2001-2021",
            "figure_type": "broad cumulative budgetary war cost",
            "nominal_usd_bn": AFGHAN_TOTAL_COST_BN,
            "real_2024_usd_bn": np.nan,
            "as_published_usd_bn": round(afghan_total_aspub, 1),
            "real_2024_low_bn": np.nan,
            "pct_us_gdp": np.nan,
            "nominal_source": "Brown U. Costs of War (Watson Institute)",
            "years_covered": "2001-2021+ (cumulative, incl. future obligations)",
            "categories_included": "war/occupation + veterans' care + interest",
            "categories_excluded": "n/a (broad total)",
            "deflator_method": "AS PUBLISHED; NOT CPI-deflated (already cumulative)",
            "recipient_baseline_index": np.nan,
            "outcome_index_author": np.nan,
            "source_notes": (
                "Brown Costs of War: Afghanistan ~$2.3T cumulative budgetary, as "
                "published. NOT directly comparable to reconstruction outlays."
            ),
        },
    ]
    return pd.DataFrame(rows)


def chart_spending(df: pd.DataFrame) -> None:
    """Chart 112: two clearly-separated panels.

    Panel A: apples-to-closer RECONSTRUCTION comparison in real 2024 USD
             (Marshall vs Iraq + Afghan reconstruction).
    Panel B: BROAD CUMULATIVE BUDGETARY war cost (Brown Costs of War), AS
             PUBLISHED, NOT CPI-deflated, NOT directly comparable to recon.
    """
    d = df.set_index("program")
    marshall = float(d.loc["Marshall Plan", "real_2024_usd_bn"])
    m_low = float(d.loc["Marshall Plan", "real_2024_low_bn"])
    iraq_recon = float(d.loc["Iraq reconstruction", "real_2024_usd_bn"])
    afghan_recon = float(d.loc["Afghanistan reconstruction", "real_2024_usd_bn"])
    recon_sum = iraq_recon + afghan_recon
    iraq_total = float(
        d.loc["Iraq broad war cost (as published)", "as_published_usd_bn"]
    )
    afghan_total = float(
        d.loc["Afghanistan broad war cost (as published)", "as_published_usd_bn"]
    )
    total_sum = iraq_total + afghan_total

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 7))

    # Panel A: reconstruction comparison (real 2024 USD).
    a_labels = ["Marshall Plan", "Iraq recon", "Afghanistan recon"]
    a_vals = [marshall, iraq_recon, afghan_recon]
    a_colors = ["#0072B2", "#D55E00", "#E69F00"]
    barsA = axA.bar(a_labels, a_vals, color=a_colors)
    for bar, val in zip(barsA, a_vals):
        axA.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"${val:,.0f}B",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
    # Marshall real range marker (low end).
    axA.plot([0, 0], [m_low, marshall], color="black", lw=2)
    axA.scatter([0], [m_low], color="black", zorder=5)
    axA.annotate(
        f"range low ${m_low:,.0f}B",
        (0, m_low),
        textcoords="offset points",
        xytext=(8, -2),
        fontsize=8,
    )
    axA.set_ylabel("Real 2024 USD (billions, CPI-U, spend-year midpoints)")
    axA.set_title(
        "A. Reconstruction outlays (apples-to-closer, real 2024$)\n"
        f"Iraq + Afghan recon ≈ ${recon_sum:,.0f}B ≈ "
        f"{recon_sum / marshall:.1f}× Marshall (≈${marshall:,.0f}B)"
    )
    axA.set_xticks(range(len(a_labels)))
    axA.set_xticklabels(a_labels, rotation=12, ha="right")

    # Panel B: broad cumulative budgetary war cost, AS PUBLISHED.
    b_labels = ["Iraq broad\nwar cost", "Afghanistan broad\nwar cost"]
    b_vals = [iraq_total, afghan_total]
    barsB = axB.bar(b_labels, b_vals, color=["#999999", "#666666"])
    for bar, val in zip(barsB, b_vals):
        axB.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"${val/1000:,.1f}T",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
    axB.set_ylabel("USD (billions), AS PUBLISHED — NOT CPI-deflated")
    axB.set_title(
        "B. Broad cumulative budgetary war cost\n"
        f"(Brown U. Costs of War, as published; combined ≈ ${total_sum/1000:,.1f}T)\n"
        "NOT directly comparable to reconstruction outlays"
    )

    fig.suptitle("Can a Marshall Plan be repeated? Spending comparison", fontsize=14)
    fig.text(
        0.5,
        -0.02,
        "Panel A: ERP totals (State Dept); SIGIR; SIGAR — CPI-U deflated to 2024 "
        "from spend-year midpoints. Panel B: Brown U. Costs of War cumulative "
        "budgetary totals (incl. future veterans' care + interest), AS PUBLISHED, "
        "NOT deflated. Illustrative N=3.",
        ha="center",
        fontsize=8,
        style="italic",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(CHARTS / "112_marshall_vs_reconstruction_spending.png")
    plt.close(fig)


def chart_outcome(df: pd.DataFrame) -> None:
    """Chart 113: spending vs author-judged outcome (NO trendline) + mechanism."""
    progs = ["Marshall Plan", "Iraq reconstruction", "Afghanistan reconstruction"]
    sub = df.set_index("program").loc[progs].reset_index()
    labels = {
        "Marshall Plan": "Marshall",
        "Iraq reconstruction": "Iraq",
        "Afghanistan reconstruction": "Afghanistan",
    }
    colors = {
        "Marshall Plan": "#0072B2",
        "Iraq reconstruction": "#D55E00",
        "Afghanistan reconstruction": "#E69F00",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # Panel A: real spending (x) vs author-judged ordinal outcome (y).
    # NO trendline / slope: N=3 with hand-assigned ordinal markers cannot
    # support a regression and would falsely imply spending caused outcomes.
    for _, r in sub.iterrows():
        ax1.scatter(
            r["real_2024_usd_bn"],
            r["outcome_index_author"],
            s=260,
            color=colors[r["program"]],
            edgecolor="black",
            zorder=5,
        )
        ax1.annotate(
            f"{labels[r['program']]}\n(${r['real_2024_usd_bn']:,.0f}B, "
            f"author outcome {r['outcome_index_author']:.2f})",
            (r["real_2024_usd_bn"], r["outcome_index_author"]),
            textcoords="offset points",
            xytext=(10, -6),
            fontsize=9,
        )
    ax1.set_xlabel("Real reconstruction spending (2024 USD, billions)")
    ax1.set_ylabel("Author-judged outcome marker (0 collapse – 1 success)")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(
        "A. Comparable/larger outlays did NOT ensure success\n"
        "(qualitative author markers — not a measured relationship)"
    )

    # Panel B: pre-intervention institutional / human-capital baseline.
    bi = BASELINE_INDICATORS.copy()
    xpos = np.arange(len(bi))
    width = 0.38
    ax2b = ax2.twinx()
    b1 = ax2.bar(
        xpos - width / 2,
        bi["literacy_pct"],
        width,
        color="#0072B2",
        label="Adult literacy (%)",
    )
    b2 = ax2b.bar(
        xpos + width / 2,
        bi["gdp_pc_usd"],
        width,
        color="#D55E00",
        label="Pre-intervention GDP/cap (USD)",
    )
    ax2.set_xticks(xpos)
    ax2.set_xticklabels(bi["recipient"], rotation=12, ha="right")
    ax2.set_ylabel("Adult literacy (%)")
    ax2b.set_ylabel("Indicative real GDP per capita (USD)")
    ax2.set_ylim(0, 100)
    for bar, val in zip(b1, bi["literacy_pct"]):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{val:.0f}%",
            ha="center",
            fontsize=9,
        )
    for bar, val in zip(b2, bi["gdp_pc_usd"]):
        ax2b.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"${val:,.0f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax2.set_title("B. Mechanism: pre-intervention institutional/human capital")
    lines = [b1, b2]
    ax2.legend(lines, [l.get_label() for l in lines], loc="upper right", fontsize=9)

    fig.suptitle(
        "Absorptive capacity conditions the returns to aid — capital alone is not sufficient",
        fontsize=14,
    )
    fig.text(
        0.5,
        -0.02,
        "Outcome markers are QUALITATIVE AUTHOR JUDGMENTS (not measured), grounded "
        "in SIGIR, SIGAR, World Bank WGI, Maddison, UNESCO. N=3, illustrative, NOT a "
        "statistical test and NOT a causal claim; war/insurgency/occupation context "
        "differs fundamentally from voluntary aid to a cooperating sovereign.",
        ha="center",
        fontsize=8,
        style="italic",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(CHARTS / "113_spending_vs_outcome.png")
    plt.close(fig)


def main() -> None:
    df = build_table()
    out_csv = PROC / "marshall_reconstruction_comparison.csv"
    df.to_csv(out_csv, index=False)

    chart_spending(df)
    chart_outcome(df)

    marshall = df.loc[df["program"] == "Marshall Plan", "real_2024_usd_bn"].iloc[0]
    iraq_recon = df.loc[
        df["program"] == "Iraq reconstruction", "real_2024_usd_bn"
    ].iloc[0]
    afghan_recon = df.loc[
        df["program"] == "Afghanistan reconstruction", "real_2024_usd_bn"
    ].iloc[0]
    recon_sum = iraq_recon + afghan_recon
    iraq_total = df.loc[
        df["program"] == "Iraq broad war cost (as published)", "as_published_usd_bn"
    ].iloc[0]
    afghan_total = df.loc[
        df["program"] == "Afghanistan broad war cost (as published)",
        "as_published_usd_bn",
    ].iloc[0]
    total_sum = iraq_total + afghan_total

    print("=" * 72)
    print("ANALYSIS 25 — Can a Marshall Plan be repeated?")
    print("=" * 72)
    print("\n[1] REAL-DOLLAR RECONSTRUCTION COMPARISON (2024 USD, CPI-U)")
    print("    'Real consumption-equivalent (CPI)' basis — apples-to-closer.")
    print(
        f"  Marshall Plan:               ${marshall:,.0f}B "
        f"(range ${MARSHALL_REAL_LOW_BN:,.0f}-${marshall:,.0f}B)"
    )
    print(
        f"    ALSO as relative fiscal burden: ~{MARSHALL_PCT_US_GDP_CUM:.1f}% "
        f"cumulative US GDP (~1.1%/yr); ~{MARSHALL_PCT_RECIPIENT_GDP_YR:.1f}%/yr "
        "recipient GDP."
    )
    print(f"  Iraq reconstruction:         ${iraq_recon:,.0f}B  (2007 midpoint basis)")
    print(
        f"  Afghanistan reconstruction:  ${afghan_recon:,.0f}B  (2011 midpoint basis)"
    )
    print(
        f"  Iraq + Afghan RECONSTRUCTION: ${recon_sum:,.0f}B "
        f"= {recon_sum / marshall:.1f}× the Marshall Plan (apples-to-closer)."
    )
    print(
        "  NOTE: 'real consumption-equivalent (CPI)' answers a different question\n"
        "  than 'relative fiscal burden (% of GDP)'. The Marshall Plan was small\n"
        "  in real dollars but a large, sustained share of US and recipient GDP."
    )

    print("\n[1b] BROAD CUMULATIVE BUDGETARY WAR COST — AS PUBLISHED (NOT deflated)")
    print(
        "    Brown U. Costs of War cumulative budgetary totals (incl. future\n"
        "    veterans' care + interest). NOT CPI-inflated. NOT directly comparable\n"
        "    to reconstruction outlays."
    )
    print(f"  Iraq broad war cost:         ${iraq_total/1000:,.1f}T (as published)")
    print(f"  Afghanistan broad war cost:  ${afghan_total/1000:,.1f}T (as published)")
    print(f"  Combined broad war cost:     ${total_sum/1000:,.1f}T (as published)")

    print("\n[2] SOURCE / METHOD TABLE")
    cols = [
        "program",
        "figure_type",
        "nominal_source",
        "years_covered",
        "deflator_method",
    ]
    for _, r in df.iterrows():
        print(f"  {r['program']}")
        print(f"     type:     {r['figure_type']}")
        print(f"     source:   {r['nominal_source']}")
        print(f"     years:    {r['years_covered']}")
        print(f"     incl:     {r['categories_included']}")
        print(f"     excl:     {r['categories_excluded']}")
        print(f"     deflator: {r['deflator_method']}")

    print("\n[3] SPENDING vs AUTHOR-JUDGED OUTCOME (no trend fitted)")
    sub = df.set_index("program").loc[
        ["Marshall Plan", "Iraq reconstruction", "Afghanistan reconstruction"]
    ]
    for prog, r in sub.iterrows():
        print(
            f"  {prog:<28} ${r['real_2024_usd_bn']:>6,.0f}B  "
            f"author-outcome={r['outcome_index_author']:.2f}"
        )
    print(
        "  Comparable or LARGER reconstruction outlays did NOT ensure success\n"
        "  under radically different institutional/security conditions. Outcome\n"
        "  markers are QUALITATIVE AUTHOR JUDGMENTS (not measured); with N=3 no\n"
        "  slope/trend is fitted and NO causal claim ('spending caused worse\n"
        "  outcomes') is made."
    )

    print("\n[4] MARSHALL HISTORIOGRAPHY (De Long & Eichengreen 1993)")
    print(
        "  'The Marshall Plan: History's Most Successful Structural Adjustment\n"
        "  Program' (NBER WP 3899). The marginal effect of Marshall aid was likely\n"
        "  INSTITUTIONAL / POLICY-CATALYTIC — restoring functioning markets,\n"
        "  enabling intra-European coordination, and shaping a pro-growth political\n"
        "  economy — rather than a brute capital injection (the transfer was too\n"
        "  small relative to recipient GDP to drive recovery alone). This\n"
        "  STRENGTHENS the absorptive-capacity story: it was never mainly about\n"
        "  the money."
    )

    print("\n[5] INSTITUTIONAL / HUMAN-CAPITAL BASELINE (pre-intervention)")
    for _, r in BASELINE_INDICATORS.iterrows():
        print(
            f"  {r['recipient']:<18} literacy={r['literacy_pct']:>4.0f}%  "
            f"GDP/cap≈${r['gdp_pc_usd']:,.0f}"
        )
    print(
        "  W. Europe entered with high literacy, an industrial base, and "
        "professional\n  bureaucracies; Iraq/Afghanistan did not. The recipients "
        "differed in\n  ABSORPTIVE CAPACITY, not primarily in dollars received."
    )

    print("\n[6] CONFOUNDS / CAVEATS (why this is illustrative, not a test)")
    for c in [
        "Active insurgency/violence during Iraq & Afghan spending vs peace under Marshall.",
        "Cooperating sovereign governments (Marshall) vs externally-installed regimes / occupation.",
        "Rebuilding pre-existing physical + human capital vs building institutions under fire.",
        "Contractor leakage / corruption in Iraq & Afghanistan reconstruction.",
        "Oil-rent politics distorting governance in Iraq.",
        "Landlocked geography + deep aid dependence in Afghanistan.",
        "Selection bias: one canonical success vs two canonical failures (N=3).",
        "Figure types differ: reconstruction aid vs security-force aid vs broad war cost.",
        "Outcome markers are author judgments, not measured outcomes.",
    ]:
        print(f"  - {c}")

    print("\n[7] TIE TO THE REPORT")
    print(
        "  This supports the report's claim that the binding constraint is\n"
        "  ABSORPTIVE CAPACITY / INSTITUTIONS, not capital alone. The Marshall\n"
        "  Plan cannot be mechanically replicated where security, legitimacy, and\n"
        "  state capacity are absent; capital alone is not sufficient — absorptive\n"
        "  capacity conditions the returns to aid. This REINFORCES the report's\n"
        "  sovereignty/fragility argument: durable cross-border redistribution into\n"
        "  low-capacity states is precarious and contingent on institutions."
    )
    print(
        "\n  CAVEAT: N=3 illustrative historical comparison, NOT a statistical or\n"
        "  causal test. War/occupation context differs fundamentally from voluntary\n"
        "  development aid; outcome/baseline indices are qualitative author judgments."
    )

    print("\nWrote:")
    print(f"  {out_csv.relative_to(BASE)}")
    print("  charts/112_marshall_vs_reconstruction_spending.png")
    print("  charts/113_spending_vs_outcome.png")


if __name__ == "__main__":
    main()
