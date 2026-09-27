"""Consistent visualization helpers.

Centralizing style means every chart in every notebook looks like it
belongs to the same project — a detail reviewers notice.
"""
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import VISUALS_DIR

# ---------------------------------------------------------------------------
# Global style
# ---------------------------------------------------------------------------
sns.set_style("whitegrid")
plt.rcParams.update({
    "figure.figsize": (12, 6),
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.autolayout": True,
})

# Named palette — every chart uses these for brand consistency
PALETTE = {
    "primary": "#2E86AB",
    "accent": "#E74C3C",
    "success": "#27AE60",
    "warning": "#F39C12",
    "muted": "#7F8C8D",
}


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------
def save(fig, name: str, dpi: int = 150) -> None:
    """Save a figure to visuals/<name>.png and print the path."""
    path = VISUALS_DIR / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    print(f"SAVE  {path}")


# ---------------------------------------------------------------------------
# Reusable chart functions
# ---------------------------------------------------------------------------
def barh_ranked(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    xlabel: str,
    color: str = "primary",
    top_n: int = 12,
    value_fmt: str = "{:,.0f}",
):
    """Horizontal bar chart of top-N rows, sorted descending."""
    sub = df.head(top_n).iloc[::-1]  # reverse so largest is on top
    fig, ax = plt.subplots(figsize=(11, max(5, top_n * 0.5)))
    bars = ax.barh(sub[label_col], sub[value_col], color=PALETTE[color])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    for bar, val in zip(bars, sub[value_col]):
        ax.text(
            val,
            bar.get_y() + bar.get_height() / 2,
            "  " + value_fmt.format(val),
            va="center",
            fontsize=9,
        )
    return fig, ax


def line_trend(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    xlabel: str,
    ylabel: str,
    color: str = "primary",
    annotate: list[tuple] | None = None,
):
    """Line chart with optional vertical annotations."""
    fig, ax = plt.subplots()
    ax.plot(df[x], df[y], marker="o", linewidth=2, color=PALETTE[color])
    ax.fill_between(df[x], df[y], alpha=0.2, color=PALETTE[color])
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if annotate:
        for xv, label in annotate:
            ax.axvline(
                xv, color=PALETTE["accent"],
                linestyle="--", alpha=0.7, label=label,
            )
        ax.legend()
    return fig, ax