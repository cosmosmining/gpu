"""Constrained-random RTL-vs-sim lockstep fuzz campaign (Phase 3 / Phase 5 gate).

Two-warp campaign: legal-by-construction programs (dv/fuzz/gen.py) run on the RTL and the
golden simulator; asserts 0 mismatches and >=95% functional coverage (per docs/VPLAN.md),
writing dv/fuzz/coverage.json. Knobs (env): FUZZ_N (default 10000), FUZZ_SEED (default 1).
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

from gen import Gen                                          # noqa: E402
from test_lockstep import (reset_dut, load, run_core,        # noqa: E402
                           read_state, sim_state, compare)

P1_OPS = ["NOP", "HALT", "LDI", "MOV", "ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR",
          "LANEID", "JMP", "SPLIT", "JOIN", "LD", "ST", "BAR"]


def has_st(words):
    return any(((w >> 11) & 0x1F) == 0x10 for w in words)


class Coverage:
    def __init__(self):
        self.ops, self.depths, self.traps = set(), set(), set()
        self.mask_zero = self.bank = self.barrier = False

    def update(self, snap):
        for (_w, _pc, mn, _mk) in snap["trace"]:
            if mn in P1_OPS:
                self.ops.add(mn)
            elif mn.startswith("TRAP"):
                self.traps.add(int(mn[4:]))
        for d in range(0, min(snap["max_depth"], 4) + 1):
            self.depths.add(d)
        self.mask_zero |= snap["mask_zero"]
        self.bank |= snap["perf"]["bank_conflicts"] > 0
        self.barrier |= snap["perf"]["barrier_releases"] > 0

    def report(self):
        bins = {f"op_{o}": (o in self.ops) for o in P1_OPS}
        for d in range(5):
            bins[f"depth_{d}"] = d in self.depths
        bins["trap_illegal"] = 1 in self.traps
        bins["trap_overflow"] = 2 in self.traps
        bins["trap_underflow"] = 3 in self.traps
        bins["mask_zero"] = self.mask_zero
        bins["bank_conflict"] = self.bank
        bins["barrier_release"] = self.barrier
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
        st = has_st(words)
        await reset_dut(dut)
        await load(dut, words)
        if not await run_core(dut):
            mismatches.append(f"{name}: timeout")
            continue
        rtl = await read_state(dut, read_scratch=st)
        sim = sim_state(words)
        cov.update(sim["snap"])
        try:
            compare(name, rtl, sim, check_scratch=st)
        except AssertionError as e:
            if len(mismatches) < 10:
                mismatches.append(str(e))
        if (idx + 1) % 1000 == 0:
            dut._log.info(f"  fuzz progress: {idx+1}/{len(programs)}")

    bins, hit, total, pct = cov.report()
    out = {"programs": len(programs), "n_random": n, "seed": seed, "warps": 2,
           "mismatches": len(mismatches), "coverage_pct": pct,
           "coverage_hit": hit, "coverage_total": total, "bins": bins}
    with open(os.path.join(ROOT, "dv", "fuzz", "coverage.json"), "w") as f:
        json.dump(out, f, indent=2)

    dut._log.info(f"FUZZ: {len(programs)} programs (2 warps), {len(mismatches)} mismatches, "
                  f"coverage {hit}/{total} = {pct:.1f}%")
    if mismatches:
        dut._log.error("first mismatches:\n" + "\n".join(mismatches))
    missing = [k for k, v in bins.items() if not v]
    assert not mismatches, f"{len(mismatches)} mismatch(es); first: {mismatches[0]}"
    assert pct >= 95.0, f"coverage {pct:.1f}% < 95% (missing: {missing})"
