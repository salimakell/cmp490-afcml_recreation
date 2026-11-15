"""Fit hypotheses to the paper's Fig. 9 on 30 seeds.

configs (metric = what coverage % counts, label = what the DT learns):
  base_A / base_B          constrained random, rows in generated order
  smart_A / smart_B        no ML: constraint HBUSREQ=1 (and HWRITE=1 for B)
  ml_<metric>_<label>      AFCML pipeline + CGMT scheduler
"""
import json
import pickle
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tb")); sys.path.insert(0, str(ROOT))
import stimulus as S  # noqa: E402
import ml  # noqa: E402
import run_sim as run3  # noqa: E402

SEEDS = range(1, 31)
POOL_N = 12000
RES, POOLS = ROOT / "results", ROOT / "data" / "pools"
ML_COMBOS = [("A", "B"), ("A", "A_next"), ("A", "A_same"), ("B", "B")]


def job(a):
    files, out, metric, mode = a
    if not Path(out).exists():
        run3.run(files, out, metric=metric, mode=mode)
    return out


def main():
    RES.mkdir(exist_ok=True); POOLS.mkdir(parents=True, exist_ok=True)
    pool_tr = S.load(ROOT / "data" / "train_pool.json")
    with open(ROOT / "data" / "train_out.json") as f:
        log_tr = json.load(f)["log"]
    models, reps = {}, {}
    for lab in ("B", "A_next", "A_same"):
        models[lab], reps[lab] = ml.train(pool_tr, log_tr, lab)
    with open(RES / "dt_reports.json", "w") as f:
        json.dump(reps, f, indent=1)
    run3.build()
    jobs = []
    for sd in SEEDS:
        pool = S.generate_pool(POOL_N, 10_000 + sd)
        pf = POOLS / f"pool_s{sd}.json"; S.save(pool, pf)
        smA = POOLS / f"smartA_s{sd}.json"
        S.save(S.generate_pool(POOL_N, 20_000 + sd, p_busreq=1.0), smA)
        smB = POOLS / f"smartB_s{sd}.json"
        S.save(S.generate_pool(POOL_N, 20_000 + sd, p_busreq=1.0, p_write=1.0), smB)
        for m in ("A", "B"):
            jobs.append(([pf], RES / f"base_{m}_s{sd}.json", m, "list"))
        jobs.append(([smA], RES / f"smart_A_s{sd}.json", "A", "list"))
        jobs.append(([smB], RES / f"smart_B_s{sd}.json", "B", "list"))
        for m, lab in ML_COMBOS:
            files = ml.apply(models[lab], pool, POOLS / f"ml_{lab}_s{sd}")
            jobs.append((files, RES / f"ml_{m}_{lab}_s{sd}.json", m, "cgmt"))
    with Pool(2) as p:
        list(p.imap_unordered(job, jobs))


if __name__ == "__main__":
    main()
