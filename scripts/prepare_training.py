"""Training run: 20,000 random rows, logged per row, also written in the Fig. 4 CSV format."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tb")); sys.path.insert(0, str(ROOT))
import stimulus as S  # noqa: E402
import run_sim  # noqa: E402

if __name__ == "__main__":
    d = ROOT / "data"
    d.mkdir(exist_ok=True)
    pool = S.generate_pool(20000, 100)
    S.save(pool, d / "train_pool.json")
    run_sim.run([d / "train_pool.json"], d / "train_out.json", stop=False)
    with open(d / "train_out.json") as f:
        log = json.load(f)["log"]
    S.save_csv(pool, d / "train_paper_format.csv", ("Coverage", [e[3] for e in log]))
    print("training run: rows", len(log), "rule-A hits", sum(e[2] for e in log),
          "rule-B hits", sum(e[3] for e in log))
