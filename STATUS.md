# STATUS

> Update every session. Current phase, last results, next actions.
> Operator delegated continuous execution (DECISIONS D-DELEG): proceeding through gates
> automatically, committing a gate report at each, quality gates kept immutable.

## Current phase
**Phase 2 — P0 RTL + lockstep** (in progress). Phases 0–1 complete (gates met).

## Last results
- **Phase 1 COMPLETE.** ISA frozen at `isa/ISA.yaml` **v1.0.0** (21 instructions, 5-bit
  opcode, reserved 0x15–0x1F → trap). Assembler (`isa/asm.py`) + golden simulator
  (`isa/sim.py`) derive decode tables from it. **Compliance 12/12** on the sim
  (`make compliance`). `docs/SPEC.md` complete incl. the cycle-by-cycle worked
  divergence example (gate item) + 4-stage pipeline proposal w/ timing justification.
  `docs/VPLAN.md` maps every P0 feature → named test → coverage point.
- Phase 0: scaffold; smoke + lint green local + CI.

## Gate status
- **Phase 0** — `make smoke` local+CI: **MET**.
- **Phase 1** — ISA frozen + compliance passes on sim: **MET** (12/12; ISA v1.0.0 frozen
  under operator delegation D-DELEG).
- **Phase 2** — 20 directed kernels retire bit-exact RTL vs sim; lint clean: _in progress_.

## Next actions
1. Phase 2: build P0 RTL module-by-module (decoder generated from ISA.yaml; datapath/
   ALU; per-warp state + divergence mask stack; register file; I-mem; SPI→APB3→CSR).
2. cocotb lockstep bench (RTL vs `isa/sim.py`), ≥20 directed kernels bit-exact.
3. Keep lint clean; update METRICS (flops/block). Commit gate; continue to Phase 3.

## Toolchain
Local: python3.11, iverilog 12.0, verilator 5.020, yosys 0.33, verible v0.0-4061,
peakrdl 1.5.0, cocotb/pytest/numpy/pyyaml. Deferred→CI: SymbiYosys (P4), Fault (P6),
LibreLane/ORFS + klayout/magic/netgen (P7).
