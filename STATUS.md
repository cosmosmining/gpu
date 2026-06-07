# STATUS

> Update every session. Current phase, last results, next actions.

## Current phase
**Phase 0 — Scaffold** (COMPLETE — gate met; awaiting operator "continue" for Phase 1)

## Last results
- Repo bootstrapped on branch `claude/kind-pascal-xamPw` (was empty, no commits).
- Toolchain installed locally: python3.11, iverilog 12.0, verilator 5.020, yosys 0.33,
  verible v0.0-4061, peakrdl 1.5.0, pyyaml/cocotb/pytest/numpy. Deferred to CI:
  SymbiYosys (P4), Fault (P6), LibreLane/ORFS + klayout/magic/netgen (P7).
- Full repository tree created per spec §3 (46 files).
- `make smoke` / `make lint` / `make tools` implemented.
- Local results: **smoke PASS** (5/5 checks), **lint PASS** (verilator + verible clean).

## Gate status — Phase 0
Gate: `make smoke` passes locally **and** in CI.
- [x] Tree scaffolded
- [x] CLAUDE.md / STATUS.md / DECISIONS.md / METRICS.md / PREDICTIONS.md created
- [x] Makefile + CI workflows + .claude commands/hooks created
- [x] `make smoke` green locally  (5/5; lint also clean, both linters)
- [x] `make smoke` green in CI     (test run 27103292094 success; lint run 27103292111 success)

**Phase 0 gate: MET.**

## Next actions
1. **Await operator "continue"** before starting Phase 1.
2. Phase 1: freeze `isa/ISA.yaml`; derive asm + sim from it; write compliance programs
   with expected traces; complete `docs/SPEC.md` (worked divergence example + pipeline
   proposal) and `docs/VPLAN.md`. Gate: operator freezes ISA, compliance suite passes
   on the simulator.

## Phase 1 preview (do NOT start until told)
ISA.yaml frozen; asm + sim derived from it; compliance programs + expected traces;
SPEC.md with worked divergence example + pipeline proposal; VPLAN.md. Gate: operator
freezes ISA, compliance suite passes on the simulator.
