# STATUS

> Update every session. Current phase, last results, next actions.

## Current phase
**Phase 0 — Scaffold** (in progress)

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
- [ ] `make smoke` green in CI     ← after first push

## Next actions
1. Run `make smoke` locally; fix any failures.
2. Commit (conventional) + push `-u origin claude/kind-pascal-xamPw`.
3. Confirm CI `lint.yml` + `test.yml` green on the branch.
4. Present Phase 0 gate report; **wait for operator "continue"** before Phase 1.

## Phase 1 preview (do NOT start until told)
ISA.yaml frozen; asm + sim derived from it; compliance programs + expected traces;
SPEC.md with worked divergence example + pipeline proposal; VPLAN.md. Gate: operator
freezes ISA, compliance suite passes on the simulator.
