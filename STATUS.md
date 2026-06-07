# STATUS

> Update every session. Current phase, last results, next actions.
> Operator delegated continuous execution (DECISIONS D-DELEG): proceeding through gates
> automatically, committing a gate report at each, quality gates kept immutable.

## Current phase
**Phase 6 — DFT** (next). Phases 0–5 complete (gates met).

## Last results
- **Phase 5 COMPLETE (P1).** 2-warp core: round-robin scheduler (skips halted/barriered),
  banked scratchpad (4×16×8) LD/ST with bank-conflict counting + low-lane-wins ST, BAR
  barrier. **Lockstep 31/31** bit-exact (2 warps; incl. scratchpad/bank-conflict/barrier
  kernels). **Fuzz 10,005 programs (2 warps), 0 mismatches, 100% coverage (29/29)**.
  **Formal PROVEN** via yosys `sat -tempinduct`: per-warp mask-stack `sp≤DEPTH` + scheduler
  no-deadlock. **1891 flops** (I-mem 512, RF 512=cap, scratch 512=cap). Built Verilator
  5.049 (cocotb needs ≥5.036). Tools: lint clean.
- Phase 4: P0 formal A–E proven. Phase 3: 10k fuzz. Phase 2: 25/25. Phase 1: ISA v1.0.0.

## Gate status
- **Phase 0** smoke: **MET** · **P1** ISA+compliance: **MET** (12/12) ·
  **P2** lockstep: **MET** (25/25) · **P3** fuzz: **MET** · **P4** formal: **MET** ·
  **P5** P1 features + re-closure: **MET** (lockstep 31/31, fuzz 10k/0/100%, formal proven).
- **Phase 6** — Fault scan insertion + ATPG (≥95% stuck-at); functional regress re-passes with scan: _next_.

## Next actions
1. Phase 6 (DFT): scan insertion + ATPG via Fault (or document install→CI); test mode muxed
   on `uio` under the test-enable CSR bit (already present); target ≥95% stuck-at; report real %.
2. Phase 7: LibreLane/ORFS hardening + DSE sweep → Pareto; OpenSTA Fmax/WNS; freeze PREDICTIONS.md.
   Watch area (RF+scratch at flop caps; ~14.4k generic cells pre-map).
3. Phase 8: datasheet, RP2040 firmware, kernel walkthrough, tag v1.0.0.

## Toolchain
Local: python3.11, iverilog 12.0, verilator 5.020, yosys 0.33, verible v0.0-4061,
peakrdl 1.5.0, cocotb/pytest/numpy/pyyaml. Deferred→CI: SymbiYosys (P4), Fault (P6),
LibreLane/ORFS + klayout/magic/netgen (P7).
