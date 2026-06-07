"""Constrained-random RTL-vs-sim lockstep fuzz campaign (Phase 3 gate).

Generates legal-by-construction programs (dv/fuzz/gen.py), runs each on the RTL and the
golden simulator, and asserts 0 mismatches over the whole campaign. Tallies functional
coverage (per docs/VPLAN.md) from the simulator and asserts >= 95%. Writes
dv/fuzz/coverage.json.

Knobs (env): FUZZ_N (default 10000), FUZZ_SEED (default 1).
"""
import json
import os
import sys

import cocotb
from cocotb.clock import Clock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "isa"))
sys.path.insert(0, os.path.join(ROOT, "dv", "fuzz"))
sys.path.insert(0, HERE)

from sim import Simulator                                  # noqa: E402
from gen import Gen                                        # noqa: E402
from test_lockstep import (reset_dut, load, run_core,      # noqa: E402
                           read_state, compare)

P0_OPS = ["NOP", "HALT", "LDI", "MOV", "ADD", "SUB", "AND", "OR", "XOR",
          "SHL", "SHR", "LANEID", "JMP", "SPLIT", "JOIN"]


def sim_full(words):
    s = Simulator()
    s.load_program(words, active_warps=1)
    snap = s.run()
    p = snap["perf"]
    tr, tc = snap["trapped"][0]
    cmp = {
        "regs": snap["regs"][0], "pc": snap["pc"][0], "mask": snap["mask"][0],
        "sp": snap["sp"][0], "trapped": 1 if tr else 0, "trapcode": tc,
        "ret": p["retired"], "div": p["divergence_pushes"], "act": p["active_lane_sum"],
        "bank": p["bank_conflicts"], "cyc": p["cycles"],
    }
    return cmp, snap


class Coverage:
    def __init__(self):
        self.ops = set()
        self.depths = set()
        self.traps = set()
        self.mask_zero = False

    def update(self, snap):
        for (_w, _pc, mn, _mk) in snap["trace"]:
            if mn in P0_OPS:
                self.ops.add(mn)
            elif mn.startswith("TRAP"):
                self.traps.add(int(mn[4:]))
        for d in range(0, min(snap["max_depth"], 4) + 1):
            self.depths.add(d)
        if snap["mask_zero"]:
            self.mask_zero = True

    def report(self):
        bins = {}
        for op in P0_OPS:
            bins[f"op_{op}"] = op in self.ops
        for d in range(5):
            bins[f"depth_{d}"] = d in self.depths
        bins["trap_illegal"] = 1 in self.traps
        bins["trap_overflow"] = 2 in self.traps
        bins["trap_underflow"] = 3 in self.traps
        bins["mask_zero"] = self.mask_zero
        hit = sum(1 for v in bins.values() if v)
        return bins, hit, len(bins), 100.0 * hit / len(bins)


@cocotb.test()
async def fuzz_lockstep(dut):
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    n = int(os.environ.get("FUZZ_N", "10000"))
    seed = int(os.environ.get("FUZZ_SEED", "1"))
    g = Gen(seed=seed)

    programs = list(g.seed_programs().items())
    programs += [(f"rand{i}", g.random_program()) for i in range(n)]

    cov = Coverage()
    mismatches = []
    for idx, (name, words) in enumerate(programs):
        await reset_dut(dut)
        await load(dut, words)
        finished = await run_core(dut)
        if not finished:
            mismatches.append(f"{name}: timeout")
            continue
        rtl = await read_state(dut)
        cmp, snap = sim_full(words)
        cov.update(snap)
        try:
            compare(name, rtl, cmp)
        except AssertionError as e:
            if len(mismatches) < 10:
                mismatches.append(str(e))
        if (idx + 1) % 1000 == 0:
            dut._log.info(f"  fuzz progress: {idx+1}/{len(programs)}")

    bins, hit, total, pct = cov.report()
    out = {
        "programs": len(programs), "n_random": n, "seed": seed,
        "mismatches": len(mismatches), "coverage_pct": pct,
        "coverage_hit": hit, "coverage_total": total, "bins": bins,
    }
    with open(os.path.join(ROOT, "dv", "fuzz", "coverage.json"), "w") as f:
        json.dump(out, f, indent=2)

    dut._log.info(f"FUZZ: {len(programs)} programs, {len(mismatches)} mismatches, "
                  f"coverage {hit}/{total} = {pct:.1f}%")
    if mismatches:
        dut._log.error("first mismatches:\n" + "\n".join(mismatches))
    missing = [k for k, v in bins.items() if not v]
    assert not mismatches, f"{len(mismatches)} lockstep mismatch(es); first: {mismatches[0]}"
    assert pct >= 95.0, f"coverage {pct:.1f}% < 95% (missing: {missing})"
