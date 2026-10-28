"""Benford's law first-digit analysis: chi-square test and Nigrini's MAD conformity."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

from . import SQL_DIR

DIGITS = np.arange(1, 10)
EXPECTED = np.log10(1 + 1 / DIGITS)

# Nigrini's first-digit MAD thresholds (upper bounds).
MAD_BANDS = [
    (0.006, "close conformity"),
    (0.012, "acceptable conformity"),
    (0.015, "marginally acceptable conformity"),
    (float("inf"), "nonconformity"),
]


def first_digit_counts(amounts) -> np.ndarray:
    """Count leading digits 1-9 of positive amounts (zeros and negatives are ignored)."""
    a = np.asarray([x for x in amounts if x > 0], dtype=float)
    digits = np.floor(a / 10 ** np.floor(np.log10(a))).astype(int)
    digits = np.where(digits == 10, 1, digits)  # guard against log10 rounding at powers of ten
    return np.bincount(digits, minlength=10)[1:10]


def benford_stats(counts) -> dict:
    counts = np.asarray(counts, dtype=float)
    n = counts.sum()
    if n == 0:
        raise ValueError("no positive amounts")
    observed = counts / n
    expected_counts = EXPECTED * n
    chi_sq = float(((counts - expected_counts) ** 2 / expected_counts).sum())
    mad = float(np.abs(observed - EXPECTED).mean())
    return {
        "n": int(n),
        "chi_square": chi_sq,
        "p_value": float(chi2.sf(chi_sq, df=8)),
        "mad": mad,
        "conformity": next(label for bound, label in MAD_BANDS if mad <= bound),
    }


def vendor_digit_counts(con) -> pd.DataFrame:
    """Per-vendor digit counts via sql/11_benford_first_digit.sql (columns vendor_id, digit, n)."""
    return con.execute((SQL_DIR / "11_benford_first_digit.sql").read_text()).df()


def flag_vendors(con, min_n: int = 40, alpha: float = 0.001) -> pd.DataFrame:
    """Vendors with at least `min_n` invoices whose first digits reject Benford at `alpha`."""
    rows = []
    for vendor_id, g in vendor_digit_counts(con).groupby("vendor_id"):
        counts = np.zeros(9)
        counts[g["digit"].to_numpy() - 1] = g["n"].to_numpy()
        if counts.sum() < min_n:
            continue
        s = benford_stats(counts)
        if s["p_value"] < alpha:
            rows.append({"entity_id": vendor_id, **s})
    return pd.DataFrame(rows, columns=["entity_id", "n", "chi_square", "p_value", "mad", "conformity"])


def plot_benford(panels: list[tuple[str, np.ndarray]], out: str | Path) -> Path:
    """Bar chart of observed first-digit shares against the Benford curve, one panel each."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(panels), figsize=(5.6 * len(panels), 3.9), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (title, counts) in zip(axes, panels, strict=True):
        s = benford_stats(counts)
        share = np.asarray(counts) / s["n"]
        ax.bar(DIGITS, share, width=0.62, color="#2a6fb0", label="Observed")
        ax.plot(
            DIGITS, EXPECTED, color="#c2410c", marker="o", markersize=5, linewidth=2, label="Benford expected"
        )
        ax.set_xticks(DIGITS)
        ax.set_xlabel("Leading digit")
        ax.set_title(title, fontsize=11, loc="left")
        ax.text(
            0.98,
            0.95,
            f"n = {s['n']:,}\nMAD = {s['mad']:.4f}\n{s['conformity']}\n"
            f"chi-square = {s['chi_square']:.1f}, p = {s['p_value']:.3g}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
        )
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color="#e5e7eb", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Share of invoices")
    axes[0].legend(frameon=False, loc="center right", fontsize=9)
    fig.tight_layout()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out
