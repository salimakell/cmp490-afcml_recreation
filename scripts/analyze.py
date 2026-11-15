"""Compare every configuration to the paper's Fig. 9 checkpoints."""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SEEDS = range(1, 31)
PAPER_BASE = [212, 410, 596, 796, 989, 1193, 1391, 1598, 1788, 1997]
PAPER_ML = [102, 202, 302, 402, 502, 602, 702, 802, 902, 1003]
CFG = ["base_A", "base_B", "smart_A", "smart_B", "ml_A_B", "ml_A_A_next", "ml_A_A_same", "ml_B_B"]


def checkpoints(d):
    col = 4 if d["metric"] == "A" else 5
    cps, goal = [], d["goal"]
    counts = [e[col] for e in d["log"]]
    for k in range(1, 11):
        tgt = goal * k // 10
        idx = next((i for i, c in enumerate(counts) if c >= tgt), None)
        cps.append(idx + 1 if idx is not None else np.nan)
    return cps


def _load(p):
    with open(p) as f:
        return json.load(f)


out = {}
for c in CFG:
    runs = [_load(RES / f"{c}_s{s}.json") for s in SEEDS]
    assert all(r["n_errors"] == 0 for r in runs), c
    cp = np.array([checkpoints(r) for r in runs], float)
    mean = np.nanmean(cp, axis=0)
    out[c] = {"checkpoints_mean": [round(float(x), 1) for x in mean],
              "closure_mean": float(mean[-1]), "closure_sd": float(np.nanstd(cp[:, -1])),
              "closed": int(np.sum(~np.isnan(cp[:, -1]))),
              "time_ns_mean": float(np.mean([r["sim_time_ns"] for r in runs])),
              "rmse_vs_paper_baseline": float(np.sqrt(np.nanmean((mean - PAPER_BASE) ** 2))),
              "rmse_vs_paper_ml": float(np.sqrt(np.nanmean((mean - PAPER_ML) ** 2)))}
with open(RES / "fit_vs_paper.json", "w") as f:
    json.dump(out, f, indent=1)
print(f"{'config':14s} {'closure':>9s} {'sd':>6s} {'closed':>6s} {'RMSE vs paper base':>18s} {'RMSE vs paper ML':>16s}")
for c, v in out.items():
    print(f"{c:14s} {v['closure_mean']:9.1f} {v['closure_sd']:6.1f} {v['closed']:6d} "
          f"{v['rmse_vs_paper_baseline']:18.1f} {v['rmse_vs_paper_ml']:16.1f}")
print("paper baseline", PAPER_BASE)
print("base_A        ", out["base_A"]["checkpoints_mean"])
print("paper ML      ", PAPER_ML)
for c in ("ml_A_B", "ml_A_A_next", "smart_A"):
    print(f"{c:14s}", out[c]["checkpoints_mean"])
