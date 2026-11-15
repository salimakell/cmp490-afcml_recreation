"""Stimulus: exactly the columns of the paper's Fig. 4 / Fig. 5.

One stimulus = one CSV row = the master interface values for one clock cycle:
  M_HBUSREQ M_HADDR M_HTRANS M_HSIZE M_HBURST M_HPROT M_HLOCK M_HWRITE M_HWDATA
In every row of Figs. 4-5, HTRANS/HSIZE/HBURST/HPROT/HLOCK are 0, HBUSREQ and
HWRITE are 0/1, HADDR is 0..~400 and HWDATA is 0..~5000.
"""
import csv
import json
import random

COLS = ["M_HBUSREQ", "M_HADDR", "M_HTRANS", "M_HSIZE", "M_HBURST", "M_HPROT",
        "M_HLOCK", "M_HWRITE", "M_HWDATA"]
HADDR_MAX, HWDATA_MAX = 400, 5000          # ranges seen in Figs. 4-5


def random_row(rng, sid, p_busreq=0.5, p_write=0.5):
    return {"id": sid, "test": "bus_request",
            "M_HBUSREQ": int(rng.random() < p_busreq), "M_HADDR": rng.randrange(HADDR_MAX),
            "M_HTRANS": 0, "M_HSIZE": 0, "M_HBURST": 0, "M_HPROT": 0, "M_HLOCK": 0,
            "M_HWRITE": int(rng.random() < p_write), "M_HWDATA": rng.randrange(HWDATA_MAX)}


def generate_pool(n, seed, start_id=0, **kw):
    rng = random.Random(seed)
    return [random_row(rng, start_id + i, **kw) for i in range(n)]


def save(rows, path):
    with open(path, "w") as f:
        json.dump(rows, f)


def load(path):
    with open(path) as f:
        return json.load(f)


def save_csv(rows, path, extra=None):
    """Write the paper-style CSV (Fig. 3: the driver reads stimuli from a CSV)."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS + ([extra[0]] if extra else []))
        for i, r in enumerate(rows):
            w.writerow([r[c] for c in COLS] + ([extra[1][i]] if extra else []))


def features(r):
    return [r[c] for c in COLS]
