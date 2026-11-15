"""pyuvm testbench - reverse-engineered AFCML bus-request test.

The master agent's driver applies one CSV row per clock to master M0 of the
default gen_amba_ahb bus (2 masters, 2 slaves); M1 is idle. Slave agents are
always-ready responders (HTRANS is 0 in every row, so no data transfers occur).

In our reconstruction, coverage is a COUNTER toward a goal of 1000 hits (Fig. 9: coverage is linear
in transactions and the ML run gains exactly 0.1 % per transaction).
Two candidate hit rules are sampled every cycle:
  A  "grant": M0 holds HGRANT this cycle  ("masters acquiring their grants
     for certain times")
  B  "Fig.4": M0 holds HGRANT and this row has HBUSREQ=1 and HWRITE=1
     (matches all 16 labelled rows in Fig. 4; only 2 are positive, so weak evidence)
AFCML_METRIC selects which counter defines coverage %, stopping and the
scheduler's "coverage changed" test; both are logged for every row.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import cocotb
import pyuvm
from cocotb.clock import Clock
from cocotb.triggers import Event, FallingEdge, Timer
from pyuvm import (ConfigDB, uvm_agent, uvm_analysis_port, uvm_component, uvm_driver, uvm_env,
                   uvm_sequence, uvm_sequence_item, uvm_sequencer, uvm_subscriber, uvm_test)

import stimulus as S

CLK_NS = 10
GOAL = int(os.environ.get("AFCML_GOAL", "1000"))


class Bfm:
    """Master interface + slave interfaces (paper Fig. 2)."""

    def __init__(self, dut):
        self.dut, self.row, self.cycle = dut, None, 0
        self.done, self.listeners = Event(), []

    async def start(self):
        d = self.dut
        cocotb.start_soon(Clock(d.HCLK, CLK_NS, unit="ns").start())
        d.REMAP.value = 0
        for m in (0, 1):
            for n in ("HBUSREQ", "HADDR", "HTRANS", "HSIZE", "HBURST", "HPROT", "HLOCK",
                      "HWRITE", "HWDATA"):
                getattr(d, f"M{m}_{n}").value = 0
        for s in (0, 1):
            for n, v in (("HREADY", 1), ("HRESP", 0), ("HRDATA", 0), ("HSPLIT", 0)):
                getattr(d, f"S{s}_{n}").value = v
        d.HRESETn.value = 0
        for _ in range(3):
            await FallingEdge(d.HCLK)
        d.HRESETn.value = 1
        cocotb.start_soon(self._run())

    async def apply(self, row):
        self.row = row
        self.done.clear()
        await self.done.wait()

    async def _run(self):
        d = self.dut
        while True:
            await FallingEdge(d.HCLK)
            r, self.row = self.row, None
            self.cycle += 1
            for c in S.COLS:                    # driver: CSV row -> master interface pins
                getattr(d, c.replace("M_", "M0_")).value = r[c] if r else 0
            await Timer(1, "ns")
            snap = {"hgrant0": int(d.M0_HGRANT.value), "hgrant1": int(d.M1_HGRANT.value),
                    "hready": int(d.M_HREADY.value), "htrans": int(d.S_HTRANS.value),
                    "row": r}
            for cb in self.listeners:
                cb(snap)
            self.done.set()


class Item(uvm_sequence_item):
    def __init__(self, name="row", row=None):
        super().__init__(name)
        self.row = row


class Driver(uvm_driver):
    def build_phase(self):
        self.bfm = ConfigDB().get(self, "", "BFM")

    async def run_phase(self):
        while True:
            it = await self.seq_item_port.get_next_item()
            await self.bfm.apply(it.row)
            self.seq_item_port.item_done()


class MasterAgent(uvm_agent):
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        self.driver = Driver("driver", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)


class SlaveAgent(uvm_agent):
    pass   # always-ready slaves are tied off in the BFM


class Monitor(uvm_component):
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)
        ConfigDB().get(self, "", "BFM").listeners.append(lambda s: self.ap.write(s))


class Scoreboard(uvm_subscriber):
    """Protocol checks for the bus-request test."""

    def build_phase(self):
        self.errors, self.prev_req = [], 0

    def write(self, s):
        if s["hgrant0"] and s["hgrant1"]:
            self.errors.append("both masters granted")
        if s["htrans"] != 0:
            self.errors.append("unexpected bus transfer")
        if not s["hready"]:
            self.errors.append("HREADY low")
        # arbiter contract with M1 idle: M0 is granted iff it requested last cycle
        if s["hgrant0"] != self.prev_req:
            self.errors.append(f"grant {s['hgrant0']} != previous request {self.prev_req}")
        self.prev_req = s["row"]["M_HBUSREQ"] if s["row"] else 0


class Coverage(uvm_subscriber):
    def build_phase(self):
        self.count = {"A": 0, "B": 0}
        self.last = {"A": 0, "B": 0}

    def write(self, s):
        r = s["row"] or {}
        a = s["hgrant0"]
        b = int(a and r.get("M_HBUSREQ", 0) and r.get("M_HWRITE", 0))
        self.last = {"A": a, "B": b}
        self.count["A"] += a
        self.count["B"] += b


class Env(uvm_env):
    def build_phase(self):
        self.master = MasterAgent("master_agent", self)
        self.slave = SlaveAgent("slave_agent", self)
        self.monitor = Monitor("monitor", self)
        self.sb = Scoreboard("scoreboard", self)
        self.cov = Coverage("coverage", self)
        ConfigDB().set(None, "*", "COVC", self.cov)

    def connect_phase(self):
        self.monitor.ap.connect(self.sb.analysis_export)
        self.monitor.ap.connect(self.cov.analysis_export)


class Seq(uvm_sequence):
    async def body(self):
        cov = ConfigDB().get(None, "", "COVC")
        log = ConfigDB().get(None, "", "LOG")
        metric = os.environ.get("AFCML_METRIC", "A")
        stop = os.environ.get("AFCML_STOP", "1") == "1"
        files = os.environ["AFCML_FILES"].split(",")
        cgmt = os.environ.get("AFCML_MODE", "list") == "cgmt"
        k = int(os.environ.get("AFCML_SWITCH", "2"))

        async def send(r, src):
            it = Item("row", r)
            await self.start_item(it)
            await self.finish_item(it)
            log.append([r["id"], src, cov.last["A"], cov.last["B"], cov.count["A"], cov.count["B"]])
            return cov.last[metric]

        def done():
            return stop and cov.count[metric] >= GOAL

        if not cgmt:
            for f in files:
                for r in S.load(f):
                    await send(r, os.path.basename(f))
                    if done():
                        return
            return
        cl = [S.load(f) for f in files[:-1]]
        ptr, cur, miss = [0] * len(cl), 0, 0
        while any(ptr[i] < len(cl[i]) for i in range(len(cl))):
            if ptr[cur] >= len(cl[cur]):
                cur, miss = (cur + 1) % len(cl), 0
                continue
            r = cl[cur][ptr[cur]]
            ptr[cur] += 1
            g = await send(r, f"c{cur}")
            if done():
                return
            miss = 0 if g else miss + 1
            if miss >= k:
                cur, miss = (cur + 1) % len(cl), 0
        for r in S.load(files[-1]):
            await send(r, "tail")
            if done():
                return


@pyuvm.test()
class AfcmlTest(uvm_test):
    def build_phase(self):
        self.bfm = Bfm(cocotb.top)
        self.log = []
        ConfigDB().set(None, "*", "BFM", self.bfm)
        ConfigDB().set(None, "*", "LOG", self.log)
        self.env = Env("env", self)

    async def run_phase(self):
        self.raise_objection()
        await self.bfm.start()
        await Seq("seq").start(self.env.master.seqr)
        c = self.env.cov.count
        out = {"metric": os.environ.get("AFCML_METRIC", "A"), "goal": GOAL,
               "transactions": len(self.log), "sim_time_ns": self.bfm.cycle * CLK_NS,
               "count_A": c["A"], "count_B": c["B"],
               "n_errors": len(self.env.sb.errors), "errors": self.env.sb.errors[:10],
               "log": self.log}
        with open(os.environ["AFCML_OUT"], "w") as f:
            json.dump(out, f)
        self.drop_objection()
