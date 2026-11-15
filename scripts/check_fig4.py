"""Replay the 16 rows of the paper's Fig. 4 on the RTL and compare its "Coverage"
column with the two candidate hit rules (A: grant held, B: granted & HBUSREQ & HWRITE).

Note: only 2 of the 16 rows are labelled 1, so a full match is weak evidence.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tb")); sys.path.insert(0, str(ROOT))
import stimulus as S  # noqa: E402
import run_sim  # noqa: E402

# (M_HBUSREQ, M_HADDR, M_HWRITE, M_HWDATA, Coverage) transcribed from Fig. 4;
# every other column is 0 in the figure.
FIG4 = [(0, 0, 0, 0, 0), (0, 89, 0, 2439, 0), (0, 187, 0, 1619, 0), (0, 275, 0, 3203, 0),
        (0, 137, 0, 4390, 0), (1, 269, 1, 2295, 0), (1, 392, 0, 3537, 0), (1, 361, 0, 1926, 0),
        (1, 20, 0, 4801, 0), (1, 235, 1, 2916, 1), (1, 103, 0, 3060, 0), (1, 90, 0, 3946, 0),
        (0, 378, 1, 3407, 0), (0, 224, 1, 4599, 0), (1, 57, 1, 2857, 0), (1, 173, 1, 3211, 1)]


def main():
    (ROOT / "data").mkdir(exist_ok=True)
    rows = [dict(id=i, test="bus_request", M_HBUSREQ=b, M_HADDR=a, M_HTRANS=0, M_HSIZE=0,
                 M_HBURST=0, M_HPROT=0, M_HLOCK=0, M_HWRITE=w, M_HWDATA=d)
            for i, (b, a, w, d, _) in enumerate(FIG4)]
    S.save(rows, ROOT / "data" / "fig4.json")
    out = ROOT / "data" / "fig4_out.json"
    run_sim.run([ROOT / "data" / "fig4.json"], out, stop=False)
    with open(out) as f:
        log = json.load(f)["log"]
    paper = [r[-1] for r in FIG4]
    a = [e[2] for e in log]
    b = [e[3] for e in log]
    print("paper :", paper)
    print("rule A:", a, f"{sum(x == y for x, y in zip(a, paper))}/16")
    print("rule B:", b, f"{sum(x == y for x, y in zip(b, paper))}/16")


if __name__ == "__main__":
    main()
