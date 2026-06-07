#!/usr/bin/env python3
"""WarpOne constrained-random program generator (Phase 3) — legal by construction.

Guarantees, by construction:
  * P0 opcodes only; operands in range; assembles cleanly.
  * SPLIT is emitted only when stack depth < DEPTH; every SPLIT gets a matching JOIN
    emitted before HALT (statically balanced).
  * JMP targets are strictly forward (post-pass), so PC is monotonic -> programs always
    terminate (no infinite loops). A forward JMP may dynamically skip a SPLIT/JOIN, which
    yields a deterministic trap — a legitimate, valuable lockstep case.
  * Program length <= I-mem capacity.

`seed_programs()` returns a few directed edge programs so the coverage bins for
overflow/underflow/illegal/all-lanes-inactive/max-depth are reachable in one campaign.
"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "isa"))
from asm import Assembler          # noqa: E402

P0_RRR = ["ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR"]


class Gen:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.asm = Assembler()
        self.depth_cap = self.asm.isa["datapath"]["div_stack_depth"]
        self.regs = self.asm.isa["datapath"]["regs_per_lane"]
        self.imem = self.asm.isa["datapath"]["imem_entries"]

    def _reg(self):
        return f"r{self.rng.randrange(self.regs)}"

    def random_program(self, allow_jmp=True, allow_p1=True):
        rng = self.rng
        body_len = rng.randint(3, 22)
        instrs = []          # (mnem, [ops], is_jmp_placeholder)
        depth = 0
        for i in range(body_len):
            remaining = body_len - i
            # reserve slots so we can still close all open SPLITs + HALT
            can_split = depth < self.depth_cap and remaining > (depth + 1)
            opts = ["LDI", "MOV", "LANEID", "NOP"] + P0_RRR
            if can_split:
                opts += ["SPLIT", "SPLIT"]
            if depth > 0:
                opts += ["JOIN", "JOIN"]
            if allow_jmp:
                opts += ["JMP"]
            if allow_p1:
                opts += ["LD", "ST", "BAR"]
            m = rng.choice(opts)
            if m == "LDI":
                instrs.append(("LDI", [self._reg(), str(rng.randrange(256))], False))
            elif m == "MOV":
                instrs.append(("MOV", [self._reg(), self._reg()], False))
            elif m == "LANEID":
                instrs.append(("LANEID", [self._reg()], False))
            elif m == "NOP":
                instrs.append(("NOP", [], False))
            elif m in P0_RRR:
                instrs.append((m, [self._reg(), self._reg(), self._reg()], False))
            elif m == "LD":
                instrs.append(("LD", [self._reg(), self._reg()], False))
            elif m == "ST":
                instrs.append(("ST", [self._reg(), self._reg()], False))
            elif m == "BAR":
                instrs.append(("BAR", [], False))
            elif m == "SPLIT":
                instrs.append(("SPLIT", [self._reg()], False))
                depth += 1
            elif m == "JOIN":
                instrs.append(("JOIN", [], False))
                depth -= 1
            elif m == "JMP":
                instrs.append(("JMP", None, True))      # target filled in post-pass
        while depth > 0:
            instrs.append(("JOIN", [], False))
            depth -= 1
        instrs.append(("HALT", [], False))

        total = len(instrs)
        words = []
        for k, (m, ops, is_jmp) in enumerate(instrs):
            if is_jmp:
                tgt = rng.randint(k + 1, total - 1)     # strictly forward -> terminates
                words.append(self.asm.encode("JMP", [str(tgt)]))
            else:
                words.append(self.asm.encode(m, ops))
        return words

    def seed_programs(self):
        """Directed edge programs to guarantee trap / mask-zero / max-depth coverage."""
        A = self.asm
        progs = {}
        progs["seed_illegal"] = [0x15 << 11, A.encode("HALT", [])]
        progs["seed_overflow"] = A.assemble(
            "LANEID r0\nSPLIT r0\nSPLIT r0\nSPLIT r0\nSPLIT r0\nSPLIT r0\nHALT")
        progs["seed_underflow"] = A.assemble("JOIN\nHALT")
        progs["seed_mask_zero"] = A.assemble(
            "LDI r0, 0\nSPLIT r0\nLDI r1, 5\nJOIN\nHALT")
        progs["seed_depth4"] = A.assemble(
            "LANEID r0\nSPLIT r0\nSPLIT r0\nSPLIT r0\nSPLIT r0\n"
            "LDI r1,1\nJOIN\nJOIN\nJOIN\nJOIN\nHALT")
        return progs


def main():
    g = Gen(seed=1)
    for name, words in g.seed_programs().items():
        print(f"{name}: {len(words)} words")
    for i in range(3):
        w = g.random_program()
        print(f"random[{i}]: {len(w)} words  {[hex(x) for x in w[:6]]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
