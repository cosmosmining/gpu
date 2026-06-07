# DECISIONS

> Dated log of every non-obvious decision + rationale. Append-only.

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
