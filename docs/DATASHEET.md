# WarpOne — Datasheet (v1.0)

WarpOne is a 4-lane, 2-warp SIMT compute core for Tiny Tapeout (sky130A, 4×2 tiles).
It demonstrates, in silicon, the control mechanisms that define GPUs: lockstep lanes,
predicated execution under structured divergence, warp interleaving, banked shared
memory with conflict accounting, and performance counters that expose all of it.

## Features
- 4 lanes × 8-bit SIMT datapath; 8 registers/lane/warp.
- 2 hardware warps; round-robin scheduler that skips halted/barriered warps.
- Structured `SPLIT`/`JOIN` divergence over a 4-deep per-warp active-mask stack
  (overflow/underflow trap; verified by formal induction).
- Banked scratchpad: 4 banks × 16 × 8 b (64 B), shared by both warps, with
  bank-conflict serialization counting and low-lane-wins store semantics.
- `BAR` barrier synchronizing live warps.
- Performance counters: retired instructions, divergence pushes, active-lane-sum
  (→ utilization %), bank conflicts, cycles.
- Host CSR interface (I-mem load, launch, status, register/scratch/PC peek, perf dump);
  test-enable bit for scan (DFT).
- All storage is flip-flops (no SRAM macros): 1891 flops total (I-mem 512, RF 512,
  scratchpad 512, state+counters ~355).

## Interface
- Top module `tt_um_warpone`, standard Tiny Tapeout pins, single clock (target 50 MHz),
  synchronous active-low reset. Pin and CSR maps: see `docs/INTEGRATION.md`.

## ISA (frozen v1.0.0 — `isa/ISA.yaml`)
16-bit fixed-width, 5-bit opcode. P0: NOP, HALT, LDI, MOV, ADD, SUB, AND, OR, XOR, SHL,
SHR, LANEID, JMP, SPLIT, JOIN. P1: LD, ST, BAR. P2: MUL, SETP, SEL (all implemented).
Opcodes 0x15–0x1F reserved → illegal-instruction trap (decode completeness proven, no X).

## Programming model
1. Reset / `CTRL.reset`. 2. Stream the program to the I-mem window. 3. `CTRL.launch`.
4. Poll `STATUS.done`. 5. Read back register file, scratchpad, and perf counters via the
debug/perf CSRs. Both warps execute the same I-mem; cross-warp communication is via the
shared scratchpad, ordered by the round-robin scheduler and synchronized with `BAR`.

## Divergence (the GPU differentiator)
`SPLIT rp` pushes the current active mask and narrows to lanes with `R[rp] != 0`; `JOIN`
pops/reconverges. Masked-off lanes still consume cycles, so the active-lane-sum counter
directly measures divergence cost. A full cycle-by-cycle worked example is in
`docs/SPEC.md` §5.1.

## Demo kernels (`kernels/`)
- **vecadd** — per-lane `c = a + b` from LANEID-derived inputs (pure SIMT, 100% util).
- **dot-product / parallel-max** — cross-lane reduction via the shared scratchpad + BAR.
Each is bit-exact vs the golden simulator; pre-registered perf-counter values: see
`PREDICTIONS.md` (frozen at tapeout).

## Verification status (evidence)
- ISA compliance: 12/12 on the golden simulator.
- RTL-vs-sim lockstep: 31/31 directed kernels bit-exact (2 warps).
- Constrained-random fuzz: 10,005 programs × 2 warps, 0 mismatches, 100% functional
  coverage (29/29 bins).
- Formal (yosys SAT temporal induction): per-warp mask-stack `sp ≤ DEPTH`; scheduler
  no-deadlock. P0 mask-stack/decode-completeness/trap properties proven unbounded.
- Timing/area (Fmax, WNS, utilization) and ATPG stuck-at coverage: see `METRICS.md` /
  `PREDICTIONS.md` once the hardening and DFT flows have run.

## Limitations / errata
See `docs/ERRATA.md`. Full ISA (P0/P1/P2) implemented and verified. RF and scratchpad sit
exactly at their flop budgets; MUL is single-cycle (4 lane multipliers) — at hardening,
evaluate area/Fmax and, if tight, apply the fallback ladder (drop P2 first / iterative MUL).
