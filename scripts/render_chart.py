#!/usr/bin/env python3
"""Render the weekly Top-15 gainers horizontal bar chart (dark theme, A-share colors).

Standalone matplotlib implementation of the skill's Step 3. Any other charting
stack (ECharts, frontend components, built-in tools) may be used instead as long
as the style rules are respected: dark theme, all-red bars (gainers only),
value labels at bar ends.

Requires: pip install matplotlib

Usage:
  python scripts/render_chart.py --input data/kline_data.json \
      --sector-info data/sectors.json --out chart_week_top15.png
"""

import argparse
import subprocess
import sys
from pathlib import Path


def top15(sys_python: str, kline: Path, sectors: Path):
    """Call calc_changes.py with the same interpreter and return (names, values)."""
    out = subprocess.run(
        [sys_python, str(Path(__file__).parent / "calc_changes.py"),
         "--input", str(kline), "--sector-info", str(sectors),
         "--sort", "chg_5d", "--format", "tsv", "--fields", "name,chg_5d",
         "--limit", "16"],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    rows = [line.split("\t") for line in out[1:16]]  # skip header
    return rows[::-1], None


def main():
    ap = argparse.ArgumentParser(description="Render weekly Top-15 bar chart")
    ap.add_argument("--input", default="data/kline_data.json")
    ap.add_argument("--sector-info", default="data/sectors.json")
    ap.add_argument("--out", default="chart_week_top15.png")
    args = ap.parse_args()

    rows, _ = top15(sys.executable, Path(args.input), Path(args.sector_info))
    names = [r[0] for r in rows]
    vals = [float(r[1].rstrip("%")) for r in rows]

    try:
        import matplotlib
    except ImportError:
        sys.exit("matplotlib is required: pip install matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    plt.rcParams["axes.unicode_minus"] = False

    # The weekly Top-15 list contains gainers only, so every bar is red
    # (A-share convention: red = up). No green is used anywhere.
    colors = ["#ef4444"] * len(vals)

    fig, ax = plt.subplots(figsize=(10, 0.68 * len(rows) + 1.2), dpi=110)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    bars = ax.barh(names, vals, color=colors, height=0.62)
    ax.tick_params(colors="#E6EDF3", labelsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color=(1, 1, 1, 0.07), linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_width() + max(abs(v) for v in vals) * 0.01,
                bar.get_y() + bar.get_height() / 2, f"{v:+.2f}%",
                va="center", ha="left", color="#E6EDF3", fontsize=10)
    lo, hi = 0, max(vals) * 1.15
    ax.set_xlim(lo, hi)
    ax.set_title("申万二级行业 周涨幅 Top 15（近5个交易日）",
                 color="#E6EDF3", fontsize=14, pad=14)
    fig.text(0.99, 0.01, "■ 涨幅（红） · 数据源：申万宏源研究(akshare)",
             ha="right", color="#8b949e", fontsize=9)
    plt.tight_layout()
    plt.savefig(args.out, facecolor=fig.get_facecolor(), bbox_inches="tight")
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
