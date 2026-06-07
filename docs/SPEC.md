# WarpOne — Microarchitecture Specification

> **STATUS: SKELETON (Phase 0).** Completed and frozen in **Phase 1** alongside the ISA.
> No core RTL is written until this document and `isa/ISA.yaml` are frozen and
> operator-approved (engineering standard #1). Section headers below are the Phase 1
> work plan.

## 1. Overview
4-lane, 2-warp SIMT compute core. Purpose: demonstrate, in observable silicon, the
control mechanisms that define GPUs — lockstep lanes, predicated execution under
divergence, warp interleaving, banked-memory conflicts, and the counters that expose
them. Throughput is explicitly **not** the goal.

## 2. Datapath
4 lanes × 8-bit. 8 registers per lane per warp. 16-bit fixed-width instructions.
(Authoritative parameters live in `isa/ISA.yaml § datapath`.)

## 3. Pipeline _(Phase 1 — propose with timing justification)_
Proposal: fetch / decode / execute / writeback. Exact staging, hazard handling, and
the 50 MHz timing argument are to be presented here and approved at the Phase 1 gate.

## 4. Warp scheduler _(Phase 1)_
Round-robin across 2 warps, skipping halted/barriered warps. Define issue policy,
fairness guarantee (formalized in Phase 4), and interaction with stalls.

## 5. Divergence semantics — SPLIT / JOIN _(Phase 1, GATE ITEM)_
Structured divergence over a 4-deep per-warp mask stack. **Must define:** exact
stack-entry contents (mask, reconvergence PC, …), the mask algebra for SPLIT (push)
and JOIN (pop), and overflow/underflow trap behavior. **A fully worked example
program showing the active mask and PC trace cycle-by-cycle is part of the Phase 1
gate.**

## 6. Memory
- I-mem: 32×16b (P0; up to 64 if area allows), CSR-loadable.
- Register file: 2 warps × 4 lanes × 8 regs × 8b.
- Scratchpad (P1): 4 banks × 16 × 8b, LD/ST with bank-conflict serialization + counter.
All storage is flops (no SRAM macros). Flop budget tracked in `METRICS.md`.

## 7. Host interface
SPI slave → APB3 → PeakRDL-generated CSRs: I-mem write port, launch/halt control,
status, lane-register peek. CSR map authored in `regs/warpone.rdl`; usage in
`docs/INTEGRATION.md`.

## 8. Performance counters _(P1)_
cycles, retired instructions, divergence pushes, active-lane-sum (→ utilization %),
bank conflicts, stall cycles by cause.

## 9. Debug port _(P1)_
Via CSR: halt, resume, single-step, PC/register peek.

## 10. DFT _(Phase 6)_
Scan insertion + ATPG (Fault). Test mode muxed onto `uio` under a test-enable CSR
bit. Target ≥95% stuck-at on scanned logic.

## 11. Area fallback ladder
Apply top-down if >70% utilization: drop P2 → I-mem 64→32 → scratchpad 4→2 banks →
drop second warp but keep scheduler interfaces. **Never** drop the divergence stack,
LANEID, perf counters, debug peek, or scan once implemented.
