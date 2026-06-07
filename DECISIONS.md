# DECISIONS

> Dated log of every non-obvious decision + rationale. Append-only.

## 2026-06-07 — Operator delegation

- **D-DELEG. Operator instruction: "continue all the phases automatically."** Authority
  to approve phase gates (including the Phase 1 ISA freeze) is delegated to me for this
  run. I proceed through phases without stopping for per-gate "continue," committing at
  each gate with a gate report in the commit + STATUS.md. Quality gates remain immutable
  (standard #9): no lowered coverage targets, no relaxed SDCs, no shrunk fuzz campaigns,
  no deleted failing tests. I still stop and ask only on a true blocker I cannot resolve
  reasonably. ISA frozen at v1.0.0 under this delegation.

## 2026-06-07 — Phase 2: P0 RTL + lockstep

- **D2.1 Host interface is a parallel CSR shim (for now).** `warpone_core` exposes a
  simple synchronous 16-bit CSR backend; `tt_um_warpone` maps it to TT pins (pin map in
  INTEGRATION.md). Spec §7 calls for SPI→APB3→PeakRDL; that front-end can be added later
  without touching the core or the CSR map. Deviation logged here; CSR map preserved in
  `regs/warpone.rdl`. (This defines the pin map — normally a stop-and-ask item; proceeding
  under operator delegation D-DELEG, map documented + provisional.)

- **D2.2 Verilator UNUSEDPARAM waiver scoped to the generated include only.** P1/P2 opcode
  constants (and NOP) in `warpone_decode.vh` aren't all referenced until their phase;
  `lint_off/on UNUSEDPARAM` wraps only the `\`include` (inline comment present). Removed
  when the ops are implemented.

- **D2.3 Curated Verible ruleset (`verible.rules`).** Keep substantive rules (always_comb/
  always_ff, case completeness, implicit nets, etc.); disable three opinionated *style*
  rules that conflict with standard RTL: parameter-name-style (ALL_CAPS params),
  unpacked-dimensions-range-ordering ([0:N-1]), explicit-parameter-storage-type. This is
  the OpenTitan-style approach (curate, don't blanket-disable).

- **D2.4 Single-cycle-per-instruction core (not pipelined yet).** The spec leaves staging
  to me. A single-issue core that retires one instruction per clock mirrors `sim._exec_one`
  exactly → trivially bit-exact lockstep, fewer flops (no pipeline registers — flops are
  the scarce resource), and it demonstrates every control mechanism (divergence stack,
  scheduler, counters), which is the project's point (throughput is not). The 4-stage
  pipeline in SPEC §3 becomes a Phase 7 timing option if Fmax needs it; the lockstep
  contract (architectural retired state) is pipeline-independent.

- **D2.5 Lockstep observes state through the real CSR/debug path** (DBG_SEL/RDATA, DBG_PC,
  STATUS, PERF), not hierarchical force — so the bench also validates the host interface.

- **D2.6 P0 RTL traps on unimplemented opcodes.** LD/ST/BAR/MUL/SETP/SEL (and reserved)
  trap as illegal in P0 (X-free, satisfies decode completeness). The sim implements them
  fully; P0 lockstep programs use only implemented opcodes, so no divergence. P1/P2 RTL
  removes the trap for those ops at their phase.

## 2026-06-07 — Phase 1: ISA freeze + toolchain + spec

- **D1.1 Encoding.** 16-bit, 5-bit opcode `[15:11]`, three 3-bit reg fields
  `a[10:8]/b[7:5]/c[4:2]`, `imm8[7:0]`, `addr6[5:0]`. 21 instructions (P0×15, P1×3,
  P2×3); opcodes `0x15..0x1F` reserved → illegal-instruction trap (decode completeness,
  no X). All opcodes frozen at v1.0.0; later phases add RTL/sim handlers (implementation,
  not an encoding change → no version bump).

- **D1.2 Divergence model = one stack entry per SPLIT.** SPLIT pushes the current mask
  and narrows to taken lanes; JOIN pops/reconverges. This matches the spec's stated
  semantics exactly (divergence depths 0–4, 4-deep stack, overflow on the 5th push,
  underflow on JOIN-with-empty). `if/else` is two masked regions (SPLIT p…JOIN; SPLIT
  ¬p…JOIN). Masked-off lanes still consume cycles, so the utilization counter exposes
  divergence cost — the pedagogical payoff. Worked cycle-by-cycle in SPEC.md §5.1.

- **D1.3 "Derived from ISA.yaml" = shared decode tables.** The encoding/opcode/format
  tables are the single source consumed by asm, sim, and (Phase 2) the RTL decoder. Per
  instruction *semantics* are implemented in sim/RTL against the normative `sem`
  annotations (you cannot execute English) and cross-checked by lockstep. This satisfies
  standard #2 while staying practical.

- **D1.4 Pipeline = 4-stage F/D/X/W, hazards hidden by fine-grained multithreading.**
  2-warp round-robin spaces same-warp instructions ≥2 cycles apart (covers D→W);
  write-first RF + one X/W→D forward covers single-warp P0; control resolves in X with a
  1-cycle bubble filled by the other warp. Multiplier (P2) is iterative so it's off the
  single-cycle path. Fmax/WNS measured in Phase 7, not asserted.

- **D1.5 Scratchpad (P1).** 4 banks × 16 × 8b, shared across warps (threadblock shared
  mem). `bank=addr[1:0]`, `index=addr[5:2]`. `bank_conflicts += active − distinct_banks`
  per LD/ST. ST same-address collision: lowest lane id wins (deterministic → bit-exact).

- **D1.6 Perf-counter taxonomy.** Architectural counters (retired, divergence_pushes,
  active_lane_sum→utilization, bank_conflicts) are pipeline-independent and checked every
  lockstep run. `active_lane_sum` counts each instruction's *execute-time* mask (SPLIT
  counts pre-narrow). Timing counters (cycles, stall_cycles) are pipeline-dependent →
  predicted by the Phase 7 timing model, frozen in PREDICTIONS.md.

- **D1.7 Compliance uses hand-derived expectations.** Expected register/counter values in
  `test_compliance.py` are computed from the spec by hand (not read back from the sim),
  so passing actually validates the sim against ISA.yaml rather than tautologically.

## 2026-06-07 — Phase 0 scaffold

- **D0.1 Project lives at the repo root of `cosmosmining/gpu`.** The spec §3 shows a
  `warpone/` root directory, but the repo itself is the project and was empty. Nesting
  everything under a redundant `warpone/` subdir adds no value. "warpone" remains the
  IP/module name (`tt_um_warpone`, `warpone_core`). Tree otherwise matches §3 exactly.

- **D0.2 Development branch: `claude/kind-pascal-xamPw`** per operator instruction.
  All Phase 0 work commits here; pushes use `git push -u origin claude/kind-pascal-xamPw`.

- **D0.3 Tool install strategy.** Installed locally now: pyyaml, cocotb, pytest, numpy
  (pip); iverilog 12.0, verilator 5.020, yosys 0.33 (apt); peakrdl 1.5.0 +
  systemrdl-compiler (pip); Verible v0.0-4061 (static binary). Deferred to CI (heavier
  / not needed until later phases), each wired into a workflow rather than silently
  skipped: SymbiYosys (formal, Phase 4), Fault (DFT, Phase 6), LibreLane/ORFS +
  klayout/magic/netgen (harden, Phase 7). Rationale: keep Phase 0 fast; `make smoke`
  must pass with only Python.

- **D0.3a Verible install method.** Verible publishes GitHub releases as *pre-releases*,
  so the `/releases/latest` API returns 404; and the unauthenticated GitHub API is
  rate-limited (60/hr/IP, shared). Robust method (used locally and in `lint.yml`): read
  the newest tag from the no-auth, no-rate-limit `releases.atom` feed and download the
  `linux-static-x86_64` asset directly. CI verible install stays `continue-on-error`
  and `lint.py` defers gracefully if absent, so a download hiccup never blocks lint.

- **D0.4 `make smoke` is pure-Python + optional RTL compile.** The Phase 0 gate must be
  reproducible from a clean clone with minimal tools and cheap in CI. smoke checks:
  Python ≥3.9, `isa/ISA.yaml` parses with required keys, `isa/asm.py`+`isa/sim.py`
  import clean, required tree exists, and (if `iverilog` is present) the TT top stub
  compiles. iverilog absence is reported, not failed — RTL compile is enforced in CI.

- **D0.5 `isa/ISA.yaml` is a DRAFT in Phase 0, not frozen.** It carries metadata +
  structural placeholders so smoke can validate shape, with the instruction set left to
  be defined and **frozen in Phase 1** (per standard #1 and the Phase 1 gate). This
  avoids preempting the operator's ISA-freeze approval.

- **D0.6 `rtl/core/` carries no architectural RTL in Phase 0.** Per standard #1 ("no RTL
  until SPEC + ISA frozen"), core RTL begins Phase 2. `rtl/tt_top/tt_um_warpone.v` is a
  build-flow scaffold only: standard TT ports, outputs tied off, clearly marked. It
  freezes nothing about the µarch or pin map (those are set in INTEGRATION.md, Phase 1+).

- **D0.7 CI gating split.** `lint.yml` + `test.yml` run on push/PR and gate "green main"
  from Phase 0. `fuzz.yml`, `formal.yml`, `gds.yml`, `nightly.yml` are scaffolded but
  triggered by `workflow_dispatch`/`schedule` only, so they don't fail before their
  phase has real content. Each is wired to real work as its phase lands.

- **D0.8 License: Apache-2.0.** Tiny Tapeout requires an OSI-approved license; Apache-2.0
  is the TT default and standard for open silicon IP. Added at repo root.

- **D0.9 PostToolUse hook is advisory (non-blocking).** `.claude/settings.json` runs a
  quick lint/smoke-compile after edits to `rtl/` or `isa/` to surface problems early, but
  exits 0 (does not block). Hard enforcement of lint-clean lives at commit time + CI.
