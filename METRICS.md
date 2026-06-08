# METRICS

> Append-only. One row per measured checkpoint. Columns:
> date | commit | phase | fuzz pass-rate | func cov % | flops (total / by block) | WNS (ns @ MHz, corner) | ATPG stuck-at % | notes
>
> Rules: never overwrite a row; never lower a target to "pass". Add a new row per checkpoint.
> Use `scripts/metrics.py` to parse logs → `summary.json` → append a row here.

| date | commit | phase | fuzz | cov % | flops | WNS | ATPG | notes |
|------|--------|-------|------|-------|-------|-----|------|-------|
| 2026-06-07 | (pre-commit) | 0 | — | — | 0 (no core RTL yet) | — | — | scaffold; toolchain detected; `make smoke` implemented |
| 2026-06-07 | 3083862 | 0 | — | — | 0 (no core RTL yet) | — | — | Phase 0 gate MET: smoke PASS 5/5 local+CI; lint clean (verilator+verible) local+CI |
| 2026-06-07 | (phase1) | 1 | — | — | 0 (no core RTL yet) | — | — | Phase 1 gate MET: ISA v1.0.0 frozen; compliance 12/12 on sim; SPEC+VPLAN complete |
| 2026-06-07 | (phase2) | 2 | 25/25 lockstep | — | 882 | — | — | Phase 2 gate MET: 25 directed kernels bit-exact RTL vs sim; lint clean (verilator+verible) |
| 2026-06-07 | (phase3) | 3 | 10005/10005 | 100.0 (24/24) | 882 | — | — | Phase 3 gate MET: 10k random + 5 seeds, 0 mismatches, functional coverage 100% |
| 2026-06-07 | (phase4) | 4 | 10005/10005 | 100.0 | 882 | — | — | Phase 4 gate MET: SymbiYosys proofs A–E PASS unbounded (k-induction, z3); mask-stack/decode/traps |
| 2026-06-07 | (phase5) | 5 | 10005/10005 | 100.0 (29/29) | 1891 | — | — | Phase 5 gate MET (P1): 2 warps+sched+scratchpad+BAR; lockstep 31/31; fuzz 10k 2-warp 0 mismatch; formal proven (yosys sat) |
| 2026-06-07 | (phase6-8) | 6-8 | 10005/10005 | 100.0 | 1891 | pending | pending | infra: TT info.yaml+gds.yml (TT action), DFT flow (Fault, pending), datasheet+kernels; arch predictions frozen (lockstep 33/33). WNS/ATPG pending EDA tools (CI) |
| 2026-06-07 | (p2) | 7 | 10005/10005 | 100.0 (32/32) | 1891 | pending | pending | P2 implemented (MUL/SETP/SEL): full ISA live; lockstep 36/36; fuzz 10k 0 mismatch; dotprod=26, parmax=3 verified. 15043 generic cells (4 MULs) — area watch |
| 2026-06-08 | (itermul) | 7 | 10005/10005 | 100.0 (32/32) | 1895 | pending | pending | MUL -> iterative-shared (1 multiplier, 4-cycle); cycle-accurate lockstep 36/36 + fuzz 10k/0; +RP2040 firmware. 1 $mul (vs 4); 16815 generic cells (mux artifact; real area needs PDK) |

## Flop budget tracker (scarcest resource)
Hard caps without operator approval:
- I-mem ≤ 64 × 16b = 1024 b
- Register file ≤ 2 warps × 4 lanes × 8 regs × 8b = 512 b
- Scratchpad ≤ 4 banks × 16 × 8b = 512 b

Measured by Yosys generic synth (`synth -flatten; stat`) on `warpone_core` @ P1 (2 warps):
| block | flops | cap | notes |
|-------|-------|-----|-------|
| I-mem (32×16) | 512 | 1024 b | P0=32 entries; up to 64 in P1 if area allows |
| Register file (2×4×8×8) | 512 | 512 b | **at cap** (2 warps) |
| Scratchpad (4×16×8) | 512 | 512 b | **at cap** (shared, banked) |
| Per-warp state ×2 (pc5+mask4+sp3+dstk16+flags5) | ~66 | — | divergence stack = 4×4b/warp |
| CSR/control + perf counters (5×16b) | ~289 | — | counters + imem_addr/dsel/flags/cur (incl. tool overhead) |
| **Total (Yosys DFF count)** | **1891** | — | ~14.4k generic cells pre-tech-map — watch util at Phase 7 (area fallback ladder ready) |
