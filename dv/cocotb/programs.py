"""Directed P0 kernels for RTL-vs-simulator lockstep (Phase 2).

Each entry is (name, assembly). All are P0-only, terminate (HALT or trap), and have
balanced SPLIT/JOIN except the intentional trap programs. Imported by the cocotb
lockstep bench and the standalone sim cross-check.
"""

PROGRAMS = [
    ("nop_halt", """
        NOP
        NOP
        HALT
    """),
    ("arith", """
        LDI r0, 5
        LDI r1, 3
        ADD r2, r0, r1
        SUB r3, r0, r1
        AND r4, r0, r1
        OR  r5, r0, r1
        XOR r6, r0, r1
        HALT
    """),
    ("shift", """
        LDI r0, 1
        LDI r1, 3
        SHL r2, r0, r1
        LDI r3, 0x80
        SHR r4, r3, r1
        HALT
    """),
    ("logic", """
        LDI r0, 0xF0
        LDI r1, 0x0F
        AND r2, r0, r1
        OR  r3, r0, r1
        XOR r4, r0, r1
        HALT
    """),
    ("mov_chain", """
        LDI r0, 0x2A
        MOV r1, r0
        MOV r2, r1
        MOV r3, r2
        HALT
    """),
    ("laneid", """
        LANEID r0
        HALT
    """),
    ("laneid_arith", """
        LANEID r0
        LDI r1, 2
        ADD r2, r0, r1
        SHL r3, r0, r1
        HALT
    """),
    ("jmp_fwd", """
        LDI r0, 1
        JMP skip
        LDI r0, 99
    skip:
        LDI r1, 7
        HALT
    """),
    ("add_wrap", """
        LDI r0, 0xFF
        LDI r1, 1
        ADD r2, r0, r1
        HALT
    """),
    ("sub_wrap", """
        LDI r0, 0
        LDI r1, 1
        SUB r2, r0, r1
        HALT
    """),
    ("split_basic", """
        LANEID r0
        LDI r1, 100
        SPLIT r0
        LDI r1, 200
        JOIN
        LDI r2, 9
        HALT
    """),
    ("split_allactive", """
        LDI r0, 1
        SPLIT r0
        LDI r1, 5
        JOIN
        HALT
    """),
    ("split_nested2", """
        LANEID r0
        SPLIT r0
        LDI r2, 1
        LDI r3, 1
        SUB r4, r0, r3
        SPLIT r4
        LDI r2, 2
        JOIN
        JOIN
        HALT
    """),
    ("split_nested3", """
        LANEID r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        LDI r1, 7
        JOIN
        JOIN
        JOIN
        HALT
    """),
    ("split_nested4_max", """
        LANEID r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        LDI r1, 7
        JOIN
        JOIN
        JOIN
        JOIN
        HALT
    """),
    ("all_inactive", """
        LDI r0, 0
        SPLIT r0
        LDI r1, 5
        JOIN
        LDI r2, 8
        HALT
    """),
    ("if_else", """
        LANEID r0
        SPLIT r0
        LDI r1, 0xAA
        JOIN
        LDI r2, 1
        SUB r3, r2, r0
        SPLIT r3
        LDI r1, 0xBB
        JOIN
        HALT
    """),
    ("divergent_arith", """
        LANEID r0
        LDI r1, 10
        SPLIT r0
        ADD r1, r1, r0
        ADD r1, r1, r0
        JOIN
        LDI r2, 3
        HALT
    """),
    ("deep_then_shallow", """
        LANEID r0
        SPLIT r0
        SPLIT r0
        LDI r4, 4
        JOIN
        LDI r5, 5
        JOIN
        LDI r6, 6
        HALT
    """),
    ("vecadd", """
        LANEID r0
        LDI r1, 2
        SHL r2, r0, r1
        ADD r3, r0, r2
        HALT
    """),
    ("accumulate", """
        LDI r0, 0
        LDI r1, 1
        ADD r0, r0, r1
        ADD r0, r0, r1
        ADD r0, r0, r1
        HALT
    """),
    ("shift_sweep", """
        LDI r0, 0xFF
        LDI r1, 1
        SHR r2, r0, r1
        LDI r1, 4
        SHR r3, r0, r1
        LDI r1, 7
        SHL r4, r0, r1
        HALT
    """),
    ("trap_overflow", """
        LANEID r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        SPLIT r0
        HALT
    """),
    ("trap_underflow", """
        JOIN
        HALT
    """),
    # ---- P1: scratchpad LD/ST, bank conflicts, barrier (2-warp shared memory) ----
    ("st_ld", """
        LANEID r0
        LDI r1, 0x50
        ADD r1, r1, r0
        ST  r1, r0
        LD  r2, r0
        HALT
    """),
    ("bank_conflict_all", """
        LDI r0, 0
        LDI r1, 0xAB
        ST  r1, r0
        LD  r2, r0
        HALT
    """),
    ("bank_conflict_pairs", """
        LANEID r0
        LDI r1, 1
        SHR r2, r0, r1
        LDI r3, 0x11
        ST  r3, r2
        LD  r4, r2
        HALT
    """),
    ("barrier_simple", """
        NOP
        BAR
        NOP
        HALT
    """),
    ("barrier_memory", """
        LDI r0, 1
        ST  r0, r0
        BAR
        LD  r1, r0
        HALT
    """),
    ("divergent_store", """
        LANEID r0
        SPLIT r0
        LDI r1, 0x77
        ST  r1, r0
        JOIN
        LD  r2, r0
        HALT
    """),
    # ---- demo kernels (also in kernels/*.asm; predictions in PREDICTIONS.md) ----
    ("kernel_vecadd", """
        LANEID r0
        LDI r1, 1
        SHL r2, r0, r1
        ADD r3, r0, r2
        HALT
    """),
    ("kernel_reduce_sum", """
        LANEID r0
        ST  r0, r0
        BAR
        LDI r1, 0
        LD  r2, r1
        LDI r1, 1
        LD  r3, r1
        ADD r2, r2, r3
        LDI r1, 2
        LD  r3, r1
        ADD r2, r2, r3
        LDI r1, 3
        LD  r3, r1
        ADD r2, r2, r3
        HALT
    """),
]
