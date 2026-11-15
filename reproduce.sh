#!/usr/bin/env bash
# Full reproduction from scratch. About 3-5 minutes on 2 cores.
set -euo pipefail
cd "$(dirname "$0")"
command -v iverilog >/dev/null || { echo "Icarus Verilog not found (e.g. apt install iverilog / brew install icarus-verilog)"; exit 1; }
mkdir -p data results figures
python3 scripts/prepare_training.py      # 1. training simulation (20,000 rows)
python3 scripts/check_fig4.py            # 2. replay the paper's Fig. 4 rows
python3 scripts/experiments.py           # 3. 30 seeds x 8 configurations
python3 scripts/analyze.py               # 4. compare with the paper's Fig. 9 -> results/fit_vs_paper.json
python3 scripts/plot.py                  # 5. figures/fit_vs_paper_fig9.png
