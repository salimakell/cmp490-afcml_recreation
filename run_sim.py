"""Build the DUT once and run one simulation."""
import sys
from pathlib import Path

from cocotb_tools.runner import get_runner

ROOT = Path(__file__).resolve().parent
RTL = ROOT / "rtl" / "amba_ahb_m2s2.v"
BUILD = ROOT / "sim_build"
if str(ROOT / "tb") not in sys.path:
    sys.path.insert(0, str(ROOT / "tb"))


def build():
    r = get_runner("icarus")
    r.build(sources=[RTL], hdl_toplevel="amba_ahb_m2s2", build_dir=BUILD,
            timescale=("1ns", "1ps"), always=False)
    return r


def run(files, out, metric="A", mode="list", stop=True, switch=2, goal=1000):
    r = build()
    env = {"AFCML_FILES": ",".join(str(Path(f).resolve()) for f in files),
           "AFCML_OUT": str(Path(out).resolve()), "AFCML_METRIC": metric, "AFCML_MODE": mode,
           "AFCML_STOP": "1" if stop else "0", "AFCML_SWITCH": str(switch),
           "AFCML_GOAL": str(goal), "COCOTB_LOG_LEVEL": "WARNING"}
    tag = Path(out).stem
    r.test(test_module="tb_ahb", hdl_toplevel="amba_ahb_m2s2", build_dir=BUILD,
           test_dir=BUILD / f"run_{tag}", extra_env=env, results_xml=str(BUILD / f"r_{tag}.xml"))
