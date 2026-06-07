# STATUS

> Update every session. Current phase, last results, next actions.
> Operator delegated continuous execution (DECISIONS D-DELEG): proceeding through gates
> automatically, committing a gate report at each, quality gates kept immutable.

## Current phase
**Phase 4 — Formal** (next). Phases 0–3 complete (gates met).

## Last results
- **Phase 3 COMPLETE.** Legal-by-construction generator (`dv/fuzz/gen.py`); **10,005
  programs (10k random + 5 seeds), 0 RTL-vs-sim mismatches, functional coverage 100%
  (24/24 bins)** in ~3 min (`make fuzz`; report in `dv/fuzz/coverage.json`).
- Phase 2: P0 RTL; lockstep 25/25 bit-exact; 882 flops; lint clean.
- Phase 1: ISA v1.0.0 frozen; compliance 12/12. Phase 0: scaffold; smoke+lint CI.

## Gate status
- **Phase 0** — smoke local+CI: **MET**.
- **Phase 1** — ISA frozen + compliance: **MET** (12/12).
- **Phase 2** — ≥20 kernels bit-exact + lint: **MET** (25/25).
- **Phase 3** — ≥10k fuzz @ 0 mismatch + ≥95% cov: **MET** (10005, 0, 100%).
- **Phase 4** — SymbiYosys proofs (mask stack, scheduler, decode completeness, write-port): _next_.

## Next actions
1. Phase 4: SymbiYosys properties — mask-stack no over/underflow (or trap), decode
   completeness (no X / every encoding executes-or-traps), register write-port arbitration,
   scheduler no-deadlock+fairness (the scheduler proof gains teeth once P1's 2nd warp lands).
2. Phase 5: P1 — 2nd warp + round-robin scheduler, banked scratchpad LD/ST + conflict
   counter, BAR, debug halt/resume/step; re-close fuzz + formal on the expanded design.
3. Phase 6 DFT · Phase 7 harden+DSE+predictions · Phase 8 release.

## Toolchain
Local: python3.11, iverilog 12.0, verilator 5.020, yosys 0.33, verible v0.0-4061,
peakrdl 1.5.0, cocotb/pytest/numpy/pyyaml. Deferred→CI: SymbiYosys (P4), Fault (P6),
LibreLane/ORFS + klayout/magic/netgen (P7).
