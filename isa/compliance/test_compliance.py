#!/usr/bin/env python3
"""WarpOne ISA compliance suite (Phase 1 gate).

Directed P0 programs with hand-derived expected outcomes (computed from the ISA spec,
NOT read back from the simulator), so passing here validates that isa/sim.py correctly
implements isa/ISA.yaml. Runnable two ways:
    python isa/compliance/test_compliance.py     # standalone, prints PASS/FAIL
    pytest isa/compliance/test_compliance.py      # CI
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ISA = os.path.dirname(_HERE)
sys.path.insert(0, _ISA)

from asm import Assembler          # noqa: E402
from sim import Simulator          # noqa: E402

ASM = Assembler()


def run(text, active_warps=1, max_steps=10000):
    sim = Simulator()
    words = ASM.assemble(text)
    sim.load_program(words, active_warps=active_warps)
    snap = sim.run(max_steps=max_steps)
    return sim, snap


def reg(snap, lane, r, warp=0):
    return snap["regs"][warp][lane][r]


# ---------------------------------------------------------------------------
def test_arith():
    sim, s = run("""
        LDI r0, 5
        LDI r1, 3
        ADD r2, r0, r1
        SUB r3, r0, r1
        AND r4, r0, r1
        OR  r5, r0, r1
        XOR r6, r0, r1
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 2) == 8, "ADD"
        assert reg(s, l, 3) == 2, "SUB"
        assert reg(s, l, 4) == 1, "AND"
        assert reg(s, l, 5) == 7, "OR"
        assert reg(s, l, 6) == 6, "XOR"
    assert s["perf"]["retired"] == 8
    assert s["perf"]["divergence_pushes"] == 0
    assert s["halted"][0] is True


def test_shift():
    sim, s = run("""
        LDI r0, 1
        LDI r1, 3
        SHL r2, r0, r1
        LDI r3, 0x80
        SHR r4, r3, r1
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 2) == 8, "SHL 1<<3"
        assert reg(s, l, 4) == 0x10, "SHR 0x80>>3"


def test_mov():
    sim, s = run("""
        LDI r0, 42
        MOV r1, r0
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 1) == 42


def test_laneid():
    sim, s = run("""
        LANEID r0
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 0) == l, "each lane gets its index"


def test_jmp_forward():
    sim, s = run("""
        LDI r0, 1
        JMP skip
        LDI r0, 99
    skip:
        LDI r1, 7
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 0) == 1, "jumped over the r0=99"
        assert reg(s, l, 1) == 7
    # retired: LDI, JMP, LDI r1, HALT = 4
    assert s["perf"]["retired"] == 4


def test_split_join_basic():
    sim, s = run("""
        LANEID r0
        LDI r1, 100
        SPLIT r0
        LDI r1, 200
        JOIN
        LDI r2, 9
        HALT
    """)
    assert reg(s, 0, 1) == 100, "lane0 masked out, keeps 100"
    for l in (1, 2, 3):
        assert reg(s, l, 1) == 200, "diverged lanes wrote 200"
    for l in range(4):
        assert reg(s, l, 2) == 9, "reconverged: all wrote 9"
    assert s["perf"]["divergence_pushes"] == 1
    # active_lane_sum: 4+4+4 +3+3+ 4+4 = 26 ; retired 7
    assert s["perf"]["retired"] == 7
    assert s["perf"]["active_lane_sum"] == 26
    assert abs(sim.utilization() - 26 / 28 * 100) < 1e-6


def test_split_nested():
    sim, s = run("""
        LANEID r0
        LDI r1, 0
        SPLIT r0
        LDI r2, 1
        LDI r3, 1
        SUB r4, r0, r3
        SPLIT r4
        LDI r2, 2
        JOIN
        LDI r5, 7
        JOIN
        LDI r6, 9
        HALT
    """)
    # lane0: masked at outer -> only r0,r1,r6 change
    assert [reg(s, 0, r) for r in range(7)] == [0, 0, 0, 0, 0, 0, 9]
    # lane1: outer-active, inner-masked (r4==0)
    assert reg(s, 1, 2) == 1 and reg(s, 1, 5) == 7 and reg(s, 1, 6) == 9
    # lane2/3: inner-active -> r2==2
    assert reg(s, 2, 2) == 2 and reg(s, 3, 2) == 2
    assert reg(s, 2, 5) == 7 and reg(s, 3, 6) == 9
    assert s["perf"]["divergence_pushes"] == 2


def test_all_lanes_inactive():
    sim, s = run("""
        LDI r0, 0
        SPLIT r0
        LDI r1, 5
        JOIN
        LDI r2, 8
        HALT
    """)
    for l in range(4):
        assert reg(s, l, 1) == 0, "no lane active in then-block -> no write"
        assert reg(s, l, 2) == 8, "reconverged write applies"
    assert s["perf"]["divergence_pushes"] == 1
    # active_lane_sum: 4(LDI) +4(SPLIT) +0(LDI masked) +0(JOIN) +4(LDI) +4(HALT) = 16
    assert s["perf"]["active_lane_sum"] == 16
    assert s["perf"]["retired"] == 6


def test_stack_overflow_trap():
    sim, s = run("""
        LANEID r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        HALT
    """)
    assert s["trapped"][0] == (True, 2), "5th SPLIT overflows depth-4 stack"
    assert s["perf"]["divergence_pushes"] == 4, "only the 4 successful pushes count"
    assert s["halted"][0] is True


def test_stack_underflow_trap():
    sim, s = run("""
        JOIN
        HALT
    """)
    assert s["trapped"][0] == (True, 3), "JOIN on empty stack underflows"
    assert s["perf"]["divergence_pushes"] == 0


def test_reserved_opcode_traps():
    sim = Simulator()
    sim.load_program([0x15 << 11, 0x01 << 11], active_warps=1)   # reserved op, then HALT
    s = sim.run()
    assert s["trapped"][0] == (True, 1), "reserved opcode -> illegal-instruction trap (no X)"


def test_halt_retire_counts():
    sim, s = run("""
        NOP
        NOP
        HALT
    """)
    assert s["perf"]["retired"] == 3
    assert s["halted"][0] is True
    assert s["perf"]["active_lane_sum"] == 12   # 3 instrs * 4 lanes


# ---------------------------------------------------------------------------
def main():
    tests = sorted(k for k, v in globals().items() if k.startswith("test_") and callable(v))
    npass = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"  [PASS] {name}")
            npass += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR ] {name}: {type(e).__name__}: {e}")
    print(f"compliance: {npass}/{len(tests)} passed")
    return 0 if npass == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
