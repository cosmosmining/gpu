#!/usr/bin/env python3
"""WarpOne instruction-accurate simulator — dispatch derived from isa/ISA.yaml.

This is the GOLDEN reference for lockstep verification (standard #4). RTL is compared
against the retired-instruction state this model produces: PC trace, register file,
scratchpad, and divergence masks. Per standard #2, the simulator is NEVER edited to
make failing RTL pass — when they disagree, ISA.yaml arbitrates.

Phase 0: scaffold. Loads/validates ISA.yaml and defines the architectural-state
containers. Instruction semantics (dispatched from ISA.yaml) land in Phase 1.
"""
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("sim.py requires pyyaml (pip install pyyaml)\n")
    raise

ISA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISA.yaml")


def load_isa(path=ISA_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


class WarpState:
    """Per-warp architectural state: PC, active-lane mask, divergence stack, RF."""

    def __init__(self, lanes, regs_per_lane, div_stack_depth):
        self.pc = 0
        self.mask = (1 << lanes) - 1          # all lanes active
        self.div_stack = []                   # entries pushed by SPLIT, popped by JOIN
        self.div_stack_depth = div_stack_depth
        self.regfile = [[0] * regs_per_lane for _ in range(lanes)]
        self.halted = False
        self.barriered = False


class PerfCounters:
    """Observable performance counters (validated against RTL in later phases)."""

    def __init__(self):
        self.cycles = 0
        self.retired = 0
        self.divergence_pushes = 0
        self.active_lane_sum = 0              # -> utilization %
        self.bank_conflicts = 0
        self.stall_cycles = {}               # by cause


class Simulator:
    """Instruction-accurate WarpOne model.

    Phase 0 builds architectural state from ISA.yaml; `step()`/`run()` semantics are
    derived from the frozen ISA in Phase 1.
    """

    def __init__(self, isa=None):
        self.isa = isa or load_isa()
        dp = self.isa["datapath"]
        self.lanes = dp["lanes"]
        self.width_mask = (1 << dp["width_bits"]) - 1
        self.warps = [
            WarpState(dp["lanes"], dp["regs_per_lane"], dp["div_stack_depth"])
            for _ in range(dp["warps"])
        ]
        self.imem = [0] * dp["imem_entries"]
        self.perf = PerfCounters()

    def load_program(self, words):
        for i, w in enumerate(words):
            self.imem[i] = w & 0xFFFF

    def step(self):
        raise NotImplementedError(
            "step() semantics are derived from the frozen ISA in Phase 1")

    def run(self, max_cycles=10000):
        raise NotImplementedError(
            "run() is derived from the frozen ISA in Phase 1")


def main():
    sim = Simulator()
    meta = sim.isa["isa"]
    print(f"WarpOne simulator — ISA '{meta['name']}' v{meta['version']} "
          f"(frozen={meta['frozen']}); {sim.lanes} lanes, {len(sim.warps)} warps, "
          f"{len(sim.imem)} I-mem entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
