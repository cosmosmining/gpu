#!/usr/bin/env python3
"""WarpOne instruction-accurate simulator — the GOLDEN reference for lockstep (std #4).

Decode tables come from isa/ISA.yaml; per-instruction semantics implement the `sem`
annotations there. The simulator is NEVER edited to make failing RTL pass (std #2) —
when they disagree, ISA.yaml arbitrates.

Produces, for a program: a retired-instruction trace [(warp, pc, mnem, mask), ...],
final register file, final scratchpad, and architectural performance counters. RTL is
compared against exactly these in lockstep.
"""
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("sim.py requires pyyaml (pip install pyyaml)\n")
    raise

ISA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISA.yaml")

TRAP_ILLEGAL, TRAP_OVERFLOW, TRAP_UNDERFLOW = 1, 2, 3


def load_isa(path=ISA_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


def popcount(x):
    return bin(x).count("1")


class WarpState:
    def __init__(self, lanes, regs):
        self.pc = 0
        self.mask = (1 << lanes) - 1     # all lanes active
        self.regs = [[0] * regs for _ in range(lanes)]
        self.dstack = []                 # list of saved masks (depth-bounded)
        self.halted = False
        self.barriered = False
        self.trapped = False
        self.trap_code = 0
        self.retired = 0


class Perf:
    def __init__(self):
        self.retired = 0
        self.divergence_pushes = 0
        self.active_lane_sum = 0
        self.bank_conflicts = 0
        self.cycles = 0              # architectural step count (timing model: Phase 7)
        self.barrier_releases = 0

    def as_dict(self):
        return dict(retired=self.retired, divergence_pushes=self.divergence_pushes,
                    active_lane_sum=self.active_lane_sum, bank_conflicts=self.bank_conflicts,
                    cycles=self.cycles, barrier_releases=self.barrier_releases)


class Simulator:
    def __init__(self, isa=None):
        self.isa = isa or load_isa()
        dp = self.isa["datapath"]
        self.lanes = dp["lanes"]
        self.regs = dp["regs_per_lane"]
        self.nwarps = dp["warps"]
        self.depth = dp["div_stack_depth"]
        self.imem_size = dp["imem_entries"]
        self.wmask = (1 << dp["width_bits"]) - 1
        sp = dp["scratchpad"]
        self.scratch_size = sp["banks"] * sp["entries_per_bank"]
        self.banks = sp["banks"]
        # opcode -> mnemonic
        self.op2mnem = {v["opcode"]: k.upper() for k, v in self.isa["instructions"].items()}
        self.reset()

    def reset(self):
        self.warps = [WarpState(self.lanes, self.regs) for _ in range(self.nwarps)]
        self.scratch = [0] * self.scratch_size
        self.imem = [0] * self.imem_size
        self.perf = Perf()
        self.trace = []
        self.deadlock = False
        self.max_depth = 0          # peak divergence-stack depth reached (coverage)
        self.mask_zero = False      # an instruction executed with all lanes inactive (coverage)

    # -- program load --------------------------------------------------------
    def load_program(self, words, warp_pcs=None, active_warps=None):
        self.reset()
        for i, w in enumerate(words):
            if i >= self.imem_size:
                raise ValueError("program exceeds I-mem")
            self.imem[i] = w & 0xFFFF
        if warp_pcs:
            for w, pc in enumerate(warp_pcs):
                self.warps[w].pc = pc
        if active_warps is not None:
            for w in range(active_warps, self.nwarps):
                self.warps[w].halted = True       # excluded from scheduler + perf

    # -- field decode --------------------------------------------------------
    @staticmethod
    def _fields(word):
        return dict(
            op=(word >> 11) & 0x1F,
            a=(word >> 8) & 0x7,
            b=(word >> 5) & 0x7,
            c=(word >> 2) & 0x7,
            imm8=word & 0xFF,
            addr6=word & 0x3F,
        )

    # -- scheduler -----------------------------------------------------------
    def _non_halted(self):
        return [w for w in self.warps if not w.halted]

    def _maybe_release_barrier(self):
        nh = self._non_halted()
        if nh and all(w.barriered for w in nh):
            for w in nh:
                w.barriered = False
                w.pc += 1
                w.retired += 1
                self.perf.retired += 1
                self.perf.active_lane_sum += popcount(w.mask)
            self.perf.barrier_releases += 1
            return True
        return False

    def _next_runnable(self, start):
        for k in range(self.nwarps):
            idx = (start + k) % self.nwarps
            w = self.warps[idx]
            if not w.halted and not w.barriered:
                return idx
        return None

    def run(self, max_steps=100000):
        rr = 0
        steps = 0
        while steps < max_steps:
            self._maybe_release_barrier()
            idx = self._next_runnable(rr)
            if idx is None:
                if not self._non_halted():
                    break                       # all halted -> done
                if not self._maybe_release_barrier():
                    self.deadlock = True         # waiting at barrier, nobody can release
                    break
                continue
            self._exec_one(idx)
            rr = (idx + 1) % self.nwarps
            steps += 1
        self.perf.cycles = steps
        return self.snapshot()

    # -- execute one instruction for warp idx --------------------------------
    def _exec_one(self, idx):
        w = self.warps[idx]
        word = self.imem[w.pc] if 0 <= w.pc < self.imem_size else 0
        f = self._fields(word)
        mnem = self.op2mnem.get(f["op"])
        M = w.mask                               # execute-time mask (captured before any narrowing)
        execpc = w.pc
        active = [l for l in range(self.lanes) if (M >> l) & 1]

        def retire(advance=True, halt=False, newpc=None):
            w.retired += 1
            self.perf.retired += 1
            self.perf.active_lane_sum += popcount(M)
            if popcount(M) == 0:
                self.mask_zero = True
            self.trace.append((idx, execpc, mnem or "ILL%02x" % f["op"], M))
            if halt:
                w.halted = True
            elif newpc is not None:
                w.pc = newpc
            elif advance:
                w.pc += 1

        def trap(code):
            w.trapped = True
            w.trap_code = code
            w.halted = True
            self.trace.append((idx, execpc, "TRAP%d" % code, M))

        if mnem is None:                          # reserved opcode -> illegal (no X)
            trap(TRAP_ILLEGAL)
        elif mnem == "NOP":
            retire()
        elif mnem == "HALT":
            retire(advance=False, halt=True)
        elif mnem == "LDI":
            for l in active:
                w.regs[l][f["a"]] = f["imm8"] & self.wmask
            retire()
        elif mnem == "MOV":
            for l in active:
                w.regs[l][f["a"]] = w.regs[l][f["b"]]
            retire()
        elif mnem in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR", "MUL", "SETP", "SEL"):
            for l in active:
                x, y = w.regs[l][f["b"]], w.regs[l][f["c"]]
                if mnem == "ADD":
                    r = (x + y) & self.wmask
                elif mnem == "SUB":
                    r = (x - y) & self.wmask
                elif mnem == "AND":
                    r = x & y
                elif mnem == "OR":
                    r = x | y
                elif mnem == "XOR":
                    r = x ^ y
                elif mnem == "SHL":
                    r = (x << (y & 7)) & self.wmask
                elif mnem == "SHR":
                    r = (x & self.wmask) >> (y & 7)
                elif mnem == "MUL":
                    r = (x * y) & self.wmask
                elif mnem == "SETP":
                    r = 1 if x < y else 0
                else:  # SEL
                    r = y if x != 0 else w.regs[l][f["a"]]
                w.regs[l][f["a"]] = r
            retire()
        elif mnem == "LANEID":
            for l in active:
                w.regs[l][f["a"]] = l & self.wmask
            retire()
        elif mnem == "JMP":
            retire(newpc=f["addr6"])
        elif mnem == "SPLIT":
            t = 0
            for l in active:
                if w.regs[l][f["a"]] != 0:
                    t |= (1 << l)
            if len(w.dstack) >= self.depth:
                trap(TRAP_OVERFLOW)
            else:
                w.dstack.append(M)
                self.max_depth = max(self.max_depth, len(w.dstack))
                self.perf.divergence_pushes += 1
                retire()                          # counts pre-narrow M, advances PC
                w.mask = M & t                    # narrow AFTER retire
        elif mnem == "JOIN":
            if not w.dstack:
                trap(TRAP_UNDERFLOW)
            else:
                retire()                          # counts narrowed M, advances PC
                w.mask = w.dstack.pop()           # reconverge
        elif mnem == "LD":
            self._mem_access(w, f, active, store=False)
            retire()
        elif mnem == "ST":
            self._mem_access(w, f, active, store=True)
            retire()
        elif mnem == "BAR":
            self.trace.append((idx, execpc, "BAR", M))   # observability; retires at release
            w.barriered = True
        else:  # pragma: no cover
            trap(TRAP_ILLEGAL)

    def _mem_access(self, w, f, active, store):
        banks_touched = set()
        # ST: low-lane-wins on identical address -> apply in lane order
        for l in active:
            if store:
                addr = w.regs[l][f["b"]] & (self.scratch_size - 1)
            else:
                addr = w.regs[l][f["b"]] & (self.scratch_size - 1)
            banks_touched.add(addr & (self.banks - 1))
        # bank conflicts = active lanes - distinct banks touched (serialized accesses)
        if active:
            self.perf.bank_conflicts += max(0, len(active) - len(banks_touched))
        if store:
            written = {}
            for l in active:               # ascending lane order => low lane wins
                addr = w.regs[l][f["b"]] & (self.scratch_size - 1)
                if addr not in written:
                    written[addr] = w.regs[l][f["a"]]
            for addr, val in written.items():
                self.scratch[addr] = val & self.wmask
        else:
            for l in active:
                addr = w.regs[l][f["b"]] & (self.scratch_size - 1)
                w.regs[l][f["a"]] = self.scratch[addr] & self.wmask

    # -- state snapshot for lockstep ----------------------------------------
    def snapshot(self):
        return {
            "trace": list(self.trace),
            "regs": [[list(lane) for lane in w.regs] for w in self.warps],
            "scratch": list(self.scratch),
            "pc": [w.pc for w in self.warps],
            "mask": [w.mask for w in self.warps],
            "sp": [len(w.dstack) for w in self.warps],
            "halted": [w.halted for w in self.warps],
            "trapped": [(w.trapped, w.trap_code) for w in self.warps],
            "perf": self.perf.as_dict(),
            "deadlock": self.deadlock,
            "max_depth": self.max_depth,
            "mask_zero": self.mask_zero,
        }

    def utilization(self):
        r = self.perf.retired
        return 100.0 * self.perf.active_lane_sum / (r * self.lanes) if r else 0.0


def main():
    sim = Simulator()
    meta = sim.isa["isa"]
    print(f"WarpOne simulator — ISA '{meta['name']}' v{meta['version']} "
          f"(frozen={meta['frozen']}); {sim.lanes} lanes, {sim.nwarps} warps, "
          f"{sim.imem_size} I-mem, scratch {sim.scratch_size}B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
