# CLAUDE.md — WarpOne flow brain

WarpOne is a 4-lane, 2-warp SIMT compute core for **Tiny Tapeout TTSKY26c**
(sky130A, 4×2 tiles, submission deadline 2026-09-07). Goal: demonstrate real
GPU control mechanics — warp scheduling, divergence via a mask stack, banked
shared memory, performance counters — in taped-out silicon. This repo IS the
project memory. Measurable evidence beats adjectives.

This file is the operational reference: what to read, what to run, the quality
bars, and where things live. Read it first every session.

## Session-start ritual (do this before anything)
1. Read `CLAUDE.md` (this file), `STATUS.md`, `DECISIONS.md`.
2. Read the last 10 lines of `METRICS.md`.
3. Confirm current phase + next action from `STATUS.md`. Do not skip gates.

## Hard constraints (never violate)
- Target: TT digital project, sky130A, 4×2 tiles (~640×200 µm). ~12–16k cells,
  design to ~70% utilization. Top module `tt_um_warpone`, standard TT interface
  (`ui_in/uo_out/uio_in/uio_out/uio_oe/ena/clk/rst_n`), single clock, f_clk = 50 MHz.
- **No SRAM macros.** All storage is flops; flop count is the scarcest resource —
  track per block in `METRICS.md`. Hard caps (need operator approval to exceed):
  I-mem ≤ 64×16b, RF ≤ 2 warps × 4 lanes × 8 regs × 8b, scratchpad ≤ 4 banks × 16 × 8b.
- Synchronous active-low reset; no latches, no comb loops, single clock domain.
- Open-source flow only (see Toolchain).

## The 10 engineering standards (the bar)
1. Spec before RTL. No core RTL until `docs/SPEC.md` + ISA are frozen & approved.
2. **ISA is single-sourced and is law** — `isa/ISA.yaml`. RTL decoder tables, the
   assembler (`isa/asm.py`), and the instruction-accurate simulator (`isa/sim.py`)
   are all derived from it. When RTL and sim disagree, the ISA spec arbitrates.
   **NEVER edit the simulator to make failing RTL pass.** ISA changes after freeze
   require operator approval + version bump + regeneration of all three consumers.
3. Verification plan drives testing — every feature → named tests + coverage in `docs/VPLAN.md`.
4. **Lockstep verification** — identical programs on RTL and sim; compare retired
   state (PC trace, RF, scratchpad, masks). Any divergence is a bug until proven a spec ambiguity.
5. **Lint-clean always** — zero lint errors every commit; waivers need an inline comment + `DECISIONS.md` entry.
6. Formal where it pays — mask stack, scheduler, decode completeness, write-port arbitration. State proof depths.
7. **DFT is a feature** — Fault scan + ATPG; test mode muxed on `uio` under a test-enable CSR bit; target ≥95% stuck-at.
8. Pre-registered predictions — `PREDICTIONS.md` (Fmax, area/block, exact perf-counter values per kernel); frozen at tapeout.
9. **Quality gates are immutable** — never lower a coverage target, relax an SDC, shrink a fuzz campaign, or delete a failing test to pass a gate. If a gate can't be met, stop and report.
10. Everything reproducible — `make <target>` reproduces every result from a clean clone; CI green on `main`.

## Build / test / harden commands
All results reproduce via `make`. Run `make help` for the live list.

| Target | What it does | Phase |
|---|---|---|
| `make tools`   | Detect installed toolchain; report have/missing | 0 |
| `make smoke`   | Fast structural + ISA-parse + RTL-compile sanity (Phase 0 gate) | 0 |
| `make lint`    | RTL lint: `verilator --lint-only` + Verible (if present) | 0+ |
| `make sim`     | cocotb lockstep sim (RTL vs `isa/sim.py`) | 2+ |
| `make fuzz`    | Constrained-random program campaign, lockstep | 3+ |
| `make regress` | Run `dv/regression.list` (directed + compliance) | 2+ |
| `make formal`  | SymbiYosys properties (mask stack, scheduler, decode, write-port) | 4+ |
| `make cov`     | Functional coverage report vs `docs/VPLAN.md` | 3+ |
| `make synth`   | Yosys synthesis, cell/flop report | 5+ |
| `make dft`     | Fault scan insertion + ATPG, stuck-at coverage | 6 |
| `make harden`  | LibreLane/ORFS hardening to GDS | 7 |
| `make sweep`   | Parallel DSE (pipeline × utilization × clock) → Pareto | 7 |
| `make predict` | Emit pre-registered predictions vs sim | 7 |
| `make isa`     | Regenerate asm/sim/decoder consumers from `isa/ISA.yaml` | 1+ |
| `make clean`   | Remove build artifacts | all |

## Quality bars (gates — immutable)
- Lint: **0 errors** at every commit.
- Fuzz: **≥10,000** constrained-random programs, **0** RTL-vs-sim mismatches.
- Coverage: **≥95%** functional (per `docs/VPLAN.md`).
- Timing: **f_clk ≥ 50 MHz**, **WNS ≥ 0** at tt corner post-route.
- DFT: **≥95%** stuck-at on scanned logic (report the real number).
- Demo kernels (vecadd, dot-product reduction, parallel max): **bit-exact** vs sim.

## File map (where things live)
- `CLAUDE.md` flow brain · `STATUS.md` phase/last-results/next · `DECISIONS.md` dated rationale log
- `METRICS.md` append-only metrics · `PREDICTIONS.md` frozen silicon predictions (Phase 7)
- `docs/` — `SPEC.md` (µarch), `VPLAN.md` (feature→test→coverage), `INTEGRATION.md` (CSR/launch/debug), `ERRATA.md`
- `isa/` — `ISA.yaml` (single source of truth), `asm.py`, `sim.py`, `compliance/`
- `rtl/core/` core + APB3 CSR iface · `rtl/tt_top/` `tt_um_warpone` + SPI→APB bridge
- `regs/warpone.rdl` SystemRDL CSRs · `dv/` (`cocotb/ fuzz/ formal/`, `regression.list`)
- `dft/ synth/ pnr/` flow configs · `fw/` RP2040 firmware · `kernels/` demo kernels
- `scripts/` metrics + helpers · `Makefile` · `.github/workflows/` CI · `.claude/` commands + hooks

## Toolchain (open-source only)
sim: Verilator + Icarus + cocotb · lint: Verible + `verilator --lint-only` ·
formal: Yosys + SymbiYosys · DFT: Fault · CSRs: PeakRDL ·
PnR/DSE: LibreLane or OpenROAD-flow-scripts · signoff GDS: official Tiny Tapeout GitHub Action.
Detect with `make tools`. Anything uninstallable locally → run in CI + log in `DECISIONS.md`. Never silently skip.

## Working agreement
- Commits: conventional, one logical change each. Never commit failing lint or broken smoke.
- When blocked: make the smallest reasonable assumption, log it in `DECISIONS.md`, continue —
  **unless** it touches the ISA, a quality gate, flop budget, area >70%, or the pin map; then **stop and ask one focused question**.
- One phase per instruction. At each gate: update `STATUS.md` + `METRICS.md`, commit, present a gate report
  (built / evidence / metrics / risks / proposed next). Don't start the next phase until the operator says "continue."
- Reporting: evidence over adjectives. If a result is bad, lead with it.

## Phase ladder (stop at every gate)
0 Scaffold · 1 ISA+toolchain+spec (freeze ISA) · 2 P0 RTL + lockstep · 3 Fuzz closure ·
4 Formal · 5 P1 features (2nd warp, scratchpad, barrier, perf counters, debug) ·
6 DFT · 7 Hardening + DSE + predictions · 8 Release.
