"""Overlay: reproduction (30 seeds) vs the paper's Fig. 9 table."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
with open(ROOT / "results" / "fit_vs_paper.json") as f:
    fit = json.load(f)
PB = [0, 212, 410, 596, 796, 989, 1193, 1391, 1598, 1788, 1997]
PM = [0, 102, 202, 302, 402, 502, 602, 702, 802, 902, 1003]
cov = list(range(0, 101, 10))
INK2, GRID, SURF = "#52514e", "#e6e5e1", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF,
                     "axes.facecolor": SURF, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(7.2, 4.3))
for key, paper, col, lab in (("base_A", PB, "#eb6834", "Without ML"), ("ml_A_B", PM, "#2a78d6", "With ML")):
    rep = [0] + fit[key]["checkpoints_mean"]
    ax.plot(cov, rep, color=col, lw=2, label=f"{lab}: reproduction (mean of 30 seeds)")
    ax.scatter(cov, paper, s=46, facecolor="none", edgecolor=col, lw=1.6, zorder=3,
               label=f"{lab}: paper Fig. 9")
sm = [0] + fit["smart_A"]["checkpoints_mean"]
ax.plot(cov, sm, color="#1baf7a", lw=1.5, ls=(0, (4, 3)), label="No ML, constraint HBUSREQ==1")
ax.set_xlabel("Functional coverage (%)"); ax.set_ylabel("Transactions (= clock cycles)")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_xlim(0, 102); ax.set_ylim(0, 2100)
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.tight_layout(); fig.savefig(ROOT / "figures" / "fit_vs_paper_fig9.png", dpi=160)
