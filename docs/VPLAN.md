# WarpOne — Verification Plan

> **STATUS: v1.0 (Phase 1).** Drives all testing (standard #3). Every architectural
> feature maps to named tests **and** named coverage points. Updated per phase.

## Methodology
- **Lockstep** (standard #4): identical programs on RTL and `isa/sim.py`; compare
  retired-instruction trace `(warp, pc, mnemonic, mask)`, final register file,
  scratchpad, traps, and architectural counters. Any divergence is a bug until proven a
  spec ambiguity (then ISA.yaml arbitrates).
- **Directed** suites for corner behavior (the compliance suite below).
- **Constrained-random** fuzzing, legal-by-construction (Phase 3): ≥10k programs, 0 mismatches.
- **Formal** (Phase 4) for the four properties that pay.
- **Coverage** ≥95% functional against the points named below.

## Feature → Test → Coverage matrix

| Feature | Phase | Directed test (exists) | Fuzz / coverage point | Formal property |
|---|---|---|---|---|
| ALU ADD/SUB/AND/OR/XOR | P0 | `test_arith` | each opcode exercised; operand corners | — |
| SHL/SHR | P0 | `test_shift` | shift amounts 0..7 | — |
| LDI / MOV | P0 | `test_arith`, `test_mov` | imm corners 0/255 | — |
| LANEID | P0 | `test_laneid` | each lane id observed | — |
| JMP control flow | P0 | `test_jmp_forward` | fwd/bwd targets in range | — |
| SPLIT/JOIN divergence (depths 0–4) | P0 | `test_split_join_basic`, `test_split_nested` | divergence-depth histogram 0..4 | mask-stack no over/underflow |
| All-lanes-inactive execution | P0 | `test_all_lanes_inactive` | mask==0 region executed | — |
| Stack overflow trap | P0 | `test_stack_overflow_trap` | SP reaches 4 then push | trap reached, no X |
| Stack underflow trap | P0 | `test_stack_underflow_trap` | JOIN with SP==0 | trap reached, no X |
| Decode completeness (every encoding) | P0 | `test_reserved_opcode_traps` | all 32 opcodes decoded/trapped | decode completeness (no X) |
| Halt / retire counting | P0 | `test_halt_retire_counts` | retired/active-sum exact | — |
| Perf counters (div pushes, util) | P0 | `test_split_join_basic`, `test_all_lanes_inactive` | counter values exact vs sim | — |
| Round-robin scheduler (skip halted/barriered) | P1 | _Phase 5_ | both warps issue; skip set | no-deadlock + fairness |
| Banked scratchpad LD/ST | P1 | _Phase 5_ | every bank-conflict pattern (1–4 lanes/bank) | write-port arbitration |
| Bank-conflict counter | P1 | _Phase 5_ | conflict count exact vs sim | — |
| BAR barrier (incl. deadlock) | P1 | _Phase 5_ | all-reach / one-loops-forever | — |
| MUL / SETP / SEL | P2 | _Phase 7 (if area)_ | operand corners | — |
| Scan + ATPG | P6 | functional regress w/ scan | — | — |

## Coverage points (functional) — collected by the Phase 3 fuzzer
1. Each opcode retired ≥ N times. 2. Divergence depth histogram covers 0,1,2,3,4.
3. Overflow + underflow traps both hit. 4. Illegal-opcode trap hit. 5. mask==0 region
executed. 6. (P1) every bank-conflict multiplicity 1..4. 7. (P1) barrier release with
2 warps. 8. utilization observed across a range (100% down to divergent lows).

## Gate metrics (immutable)
Compliance 12/12 on sim (Phase 1) · lockstep bit-exact on ≥20 directed kernels (Phase 2)
· fuzz ≥10k @ 0 mismatch + functional coverage ≥95% (Phase 3) · formal proofs pass
(Phase 4) · demo kernels bit-exact vs sim · WNS ≥ 0 @ 50 MHz (Phase 7).
