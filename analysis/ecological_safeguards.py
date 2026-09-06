"""Small shared safeguards; no replacement total-N or energy model is implied."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

NITROGEN_SCOPE = (
    "Synthetic fertilizer input only; not total industrial + intentional biological "
    "fixation. Not a planetary-boundary compliance test. Richardson et al. (2023) "
    "report a 62 Tg N/yr boundary and about 190 Tg N/yr current total fixation."
)
LEGACY_N_REASON = (
    "WITHDRAWN: legacy exploratory arithmetic mixes fixation, combustion NOx, "
    "synthetic fertilizer substitution and runoff treatment. Biological fixation "
    "in cereals is not automatically net reactive N avoided; runoff treatment "
    "cannot be subtracted from gross fixation. No valid total-N balance, "
    "boundary-compliance result or success probability is available."
)
JOINT_REASON = (
    "WITHDRAWN: the nitrogen marginal was derived from an invalid compliance "
    "comparison. Joint bounds, copula values and information rankings using it "
    "are not valid ecological results, even as probability sensitivity. "
    "A compatible total-N model and independently justified marginals are needed."
)
LCOS_REASON = (
    "WITHDRAWN: the legacy comparison lacks auditable, common-assumption LCOS "
    "sources. Manufacturer capital-cost targets in $/kWh of capacity are not "
    "LCOS in $/MWh discharged. The iron-air target and pilot LCOS values have "
    "been removed, not converted. Rebuild requires lifetime, utilization, "
    "efficiency, charging cost, financing and operating-cost assumptions."
)
FINAL_ENERGY_REASON = (
    "WITHDRAWN: the legacy shares mixed final energy, process feedstocks and "
    "cement process CO2. Calcination emissions are not final-energy consumption. "
    "Removing one category and renormalizing does not validate the remaining "
    "shares. No replacement percentages or 'hard 80%' estimate are asserted. "
    "Rebuild needs a consistent energy balance and a separate emissions inventory."
)

# One entry per process; N and P are components of biogeochemical flows.
# This is the published 2023 assessment, not a calculation from local proxy data.
PB_2023 = (
    ("Climate change", "Transgressed"),
    ("Biosphere integrity", "Transgressed"),
    ("Land-system change", "Transgressed"),
    ("Freshwater change (blue and green)", "Transgressed"),
    ("Biogeochemical flows (N and P)", "Transgressed"),
    ("Novel entities", "Transgressed"),
    ("Ocean acidification", "Not transgressed globally"),
    ("Atmospheric aerosol loading", "Not transgressed globally"),
    ("Stratospheric ozone depletion", "Not transgressed globally"),
)


def withdrawn_table(reason: str) -> pd.DataFrame:
    """Deliberately omit invalid numeric columns; consumers must not reuse them."""
    return pd.DataFrame([{"status": "withdrawn", "interpretation_limit": reason}])


def withdrawal_chart(path: Path, title: str, reason: str) -> None:
    import textwrap

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_axis_off()
    ax.set_title(title, fontsize=16, fontweight="bold", color="#a32a2a", pad=25)
    ax.text(
        0.05,
        0.75,
        textwrap.fill(reason, 95),
        transform=ax.transAxes,
        va="top",
        fontsize=13,
        linespacing=1.7,
        parse_math=False,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def planetary_scorecard(chart_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_axis_off()
    table = ax.table(
        cellText=PB_2023,
        colLabels=["Earth-system process", "Published 2023 status"],
        loc="center",
        cellLoc="left",
        colWidths=[0.56, 0.44],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    ax.set_title(
        "Chart 31: Nine planetary-boundary processes\n"
        "Richardson et al. (2023): six transgressed — dated literature summary",
        fontsize=14,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.03,
        "Source: doi:10.1126/sciadv.adh2458. Not a current-year reassessment.\n"
        "LPI is a complementary biodiversity indicator, NOT a PB control variable.\n"
        "A global non-transgression does not imply absence of regional harm.",
        ha="center",
        fontsize=10,
    )
    fig.savefig(chart_dir / "31_planetary_scorecard.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(
        "Published 2023 summary: 6 of 9 processes transgressed; N/P counted together."
    )


def energy_withdrawals(chart_dir: Path) -> None:
    withdrawal_chart(
        chart_dir / "86_lcos_by_duration.png",
        "Chart 86: LCOS comparison withdrawn",
        LCOS_REASON,
    )
    withdrawal_chart(
        chart_dir / "90_final_energy_tractability.png",
        "Chart 90: Final-energy shares withdrawn",
        FINAL_ENERGY_REASON,
    )
