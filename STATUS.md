# STATUS

> Update every session. Current phase, last results, next actions.
> Operator delegated continuous execution (DECISIONS D-DELEG): proceeding through gates
> automatically, committing a gate report at each, quality gates kept immutable.

## Current phase
**Phase 3 — Fuzz closure** (next). Phases 0–2 complete (gates met).

## Last results
- **Phase 2 COMPLETE.** `warpone_core` (P0, single-cycle-per-instruction) + `tt_um_warpone`
  wrapper. Decoder generated from ISA.yaml. **Lockstep 25/25 kernels bit-exact** RTL vs
  `isa/sim.py` (`make sim`) — all divergence depths 0–4, all-lanes-inactive, both traps,
  ALU wraps, perf counters. Lint clean (verilator + verible). **882 flops** (I-mem 512 +
  RF 256 + counters 82 + stack/ctrl ~32); within budget.
- Phase 1: ISA v1.0.0 frozen; compliance 12/12 on sim.
- Phase 0: scaffold; smoke + lint green local + CI.

## Gate status
- **Phase 0** — `make smoke` local+CI: **MET**.
- **Phase 1** — ISA frozen + compliance on sim: **MET** (12/12).
- **Phase 2** — ≥20 kernels bit-exact RTL vs sim + lint clean: **MET** (25/25).
- **Phase 3** — ≥10k constrained-random programs, 0 mismatches, ≥95% func coverage: _next_.

## Next actions
1. Phase 3: legal-by-construction random program generator (balanced SPLIT/JOIN, bounded,
   in-range), reusing the lockstep comparator; run ≥10k programs; functional coverage.
2. Phase 4: SymbiYosys formal (mask stack, scheduler, decode completeness, write-port).
3. Phase 5: P1 (2nd warp + scheduler, scratchpad LD/ST + conflicts, BAR, debug); re-close 3–4.

## Toolchain
Local: python3.11, iverilog 12.0, verilator 5.020, yosys 0.33, verible v0.0-4061,
peakrdl 1.5.0, cocotb/pytest/numpy/pyyaml. Deferred→CI: SymbiYosys (P4), Fault (P6),
LibreLane/ORFS + klayout/magic/netgen (P7).
