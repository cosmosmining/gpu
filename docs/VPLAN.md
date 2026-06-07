# WarpOne — Verification Plan

> **STATUS: SKELETON (Phase 0).** Authored in **Phase 1**; drives all testing
> (engineering standard #3). Every architectural feature maps to named tests **and**
> named coverage points here. Filled per feature as phases land.

## Methodology
- **Lockstep** (standard #4): identical programs on RTL and `isa/sim.py`; compare
  retired-instruction state (PC trace, RF, scratchpad, masks). Any divergence is a
  bug until proven a spec ambiguity.
- **Directed** suites for corner behavior; **constrained-random** fuzzing
  (legal-by-construction) for breadth (≥10k programs, 0 mismatches).
- **Formal** for the properties where it pays (Phase 4).
- **Coverage** ≥95% functional, measured against the points named below.

## Feature → Test → Coverage matrix _(to be populated in Phase 1+)_

| Feature | Phase | Directed test(s) | Fuzz/coverage point(s) | Formal property |
|---|---|---|---|---|
| ALU ops (ADD/SUB/AND/OR/XOR/SHL/SHR) | P0 | _tbd_ | _tbd_ | — |
| LDI / MOV / LANEID | P0 | _tbd_ | _tbd_ | — |
| JMP control flow | P0 | _tbd_ | _tbd_ | — |
| SPLIT/JOIN divergence (depths 0–4) | P0 | _tbd_ | depth histogram | mask-stack no over/underflow |
| All-lanes-inactive execution | P0 | _tbd_ | _tbd_ | — |
| Stack overflow/underflow trap | P0 | _tbd_ | _tbd_ | trap reached, no X |
| Decode completeness (every encoding) | P0 | _tbd_ | opcode coverage | decode completeness (no X) |
| Round-robin scheduler (skip halted/barriered) | P1 | _tbd_ | _tbd_ | no-deadlock + fairness |
| Banked scratchpad LD/ST + conflicts | P1 | every conflict pattern | conflict-count match | write-port arbitration |
| BAR barrier (incl. deadlock scenarios) | P1 | _tbd_ | _tbd_ | — |
| Perf counters vs sim | P1 | all demo kernels | exact-value match | — |
| Debug port (halt/resume/step/peek) | P1 | _tbd_ | _tbd_ | — |
| Scan + ATPG | P6 | functional regress w/ scan | — | — |

## Gate metrics
Fuzz ≥10k @ 0 mismatch · functional coverage ≥95% · demo kernels bit-exact vs sim.
