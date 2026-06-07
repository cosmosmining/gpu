# WarpOne — a 4-lane, 2-warp SIMT compute core

[![lint](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)
[![test](../../actions/workflows/test.yml/badge.svg)](../../actions/workflows/test.yml)

WarpOne is a minimal but architecturally honest **SIMT** (single-instruction,
multiple-thread) compute core for **Tiny Tapeout TTSKY26c** (sky130A). It exists to
demonstrate, in taped-out silicon, the control mechanisms that define GPUs:

- **Lockstep lanes** — 4 lanes × 8-bit datapath executing in SIMT.
- **Divergence handling** — structured `SPLIT`/`JOIN` over a 4-deep per-warp mask stack.
- **Warp interleaving** — 2 hardware warps, round-robin scheduler skipping halted/barriered warps.
- **Banked shared memory** — 4-bank scratchpad with bank-conflict serialization + counter.
- **Performance counters** — cycles, retired instructions, divergence pushes,
  active-lane utilization %, bank conflicts, stall cycles by cause.

Top module: `tt_um_warpone` (standard Tiny Tapeout interface, single clock, 50 MHz target).

## Status
**Phase 0 (scaffold).** See `STATUS.md` for the live phase, `docs/SPEC.md` for the
microarchitecture, and `isa/ISA.yaml` for the instruction set (the single source of
truth from which the assembler, simulator, and RTL decoder are derived).

## Quick start
```bash
make tools     # detect the open-source toolchain (have/missing)
make smoke     # fast structural + ISA-parse + RTL-compile sanity (Phase 0 gate)
make lint      # RTL lint (verilator --lint-only [+ Verible]); 0 errors required
make help      # all targets
```

## Engineering approach
Spec-first, verification-driven, signoff-disciplined — built like a commercial IP
team of one. The ISA is law and single-sourced; RTL is verified in **lockstep**
against an instruction-accurate Python model; quality gates (lint, ≥10k-program fuzz
@ 0 mismatch, ≥95% coverage, WNS ≥ 0 @ 50 MHz, ≥95% ATPG) are immutable. See
`CLAUDE.md` for the full flow and `DECISIONS.md` for the rationale log.

## Repository layout
| Path | Contents |
|---|---|
| `docs/` | `SPEC.md`, `VPLAN.md`, `INTEGRATION.md`, `ERRATA.md` |
| `isa/` | `ISA.yaml` (source of truth), `asm.py`, `sim.py`, `compliance/` |
| `rtl/` | `core/` (core + APB3 CSRs), `tt_top/` (`tt_um_warpone` + SPI→APB bridge) |
| `regs/` | `warpone.rdl` (SystemRDL CSR map) |
| `dv/` | `cocotb/` (lockstep), `fuzz/`, `formal/`, `regression.list` |
| `dft/ synth/ pnr/` | scan/ATPG, synthesis, hardening + DSE configs |
| `fw/ kernels/` | RP2040 firmware, demo kernels (vecadd, dot-product, parallel max) |
| `scripts/` | `smoke.py`, `lint.py`, `tools.py`, `metrics.py` |

## License
Apache-2.0 — see [LICENSE](LICENSE).
