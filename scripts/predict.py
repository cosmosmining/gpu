#!/usr/bin/env python3
"""Emit pre-registered architectural perf-counter predictions per demo kernel (Phase 7/8).

Runs each kernel in kernels/*.asm on the golden simulator (isa/sim.py) and reports the
pipeline-INDEPENDENT counters that are knowable without hardening: retired instructions,
divergence pushes, active-lane-sum (+ utilization %), bank conflicts, plus a result check.
The pipeline-DEPENDENT `cycles`/Fmax/area come from the Phase 7 hardening run and are
appended to PREDICTIONS.md then. Single warp (active_warps=1) for the canonical demo.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "isa"))
from asm import Assembler          # noqa: E402
from sim import Simulator          # noqa: E402

KERNELS = ["vecadd", "reduce_sum", "dotprod", "parmax"]


def predict(name):
    asm = Assembler()
    words = asm.assemble_file(os.path.join(ROOT, "kernels", name + ".asm"))
    sim = Simulator()
    sim.load_program(words, active_warps=1)
    snap = sim.run()
    p = snap["perf"]
    return {
        "kernel": name, "instructions": len(words),
        "retired": p["retired"], "divergence_pushes": p["divergence_pushes"],
        "active_lane_sum": p["active_lane_sum"], "utilization_pct": round(sim.utilization(), 2),
        "bank_conflicts": p["bank_conflicts"], "sim_cycles_arch": p["cycles"],
        "regs_lane0": snap["regs"][0][0], "trapped": snap["trapped"][0][0],
    }


def main():
    print("WarpOne — pre-registered architectural perf-counter predictions (golden sim)\n")
    for k in KERNELS:
        d = predict(k)
        print(f"## {d['kernel']}  ({d['instructions']} instructions)")
        print(f"   retired           = {d['retired']}")
        print(f"   divergence_pushes = {d['divergence_pushes']}")
        print(f"   active_lane_sum   = {d['active_lane_sum']}  (utilization {d['utilization_pct']}%)")
        print(f"   bank_conflicts    = {d['bank_conflicts']}")
        print(f"   arch step-count   = {d['sim_cycles_arch']}  (HW cycles incl. pipeline: Phase 7)")
        print(f"   lane0 regfile     = {d['regs_lane0']}")
        print()
    print("Fmax / WNS / area / HW-cycle counts: frozen into PREDICTIONS.md after Phase 7 hardening.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
