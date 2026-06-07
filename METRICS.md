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

## Flop budget tracker (scarcest resource)
Hard caps without operator approval:
- I-mem ≤ 64 × 16b = 1024 b
- Register file ≤ 2 warps × 4 lanes × 8 regs × 8b = 512 b
- Scratchpad ≤ 4 banks × 16 × 8b = 512 b

Measured by Yosys generic synth (`synth -flatten; stat`) on `warpone_core` @ P0 (1 warp):
| block | flops (current) | cap | notes |
|-------|-----------------|-----|-------|
| I-mem (32×16) | 512 | 1024 b | P0=32 entries; up to 64 in P1 if area allows |
| Register file (1×4×8×8) | 256 | 512 b | P0 single warp; doubles to 512 at P1 (2 warps) |
| Scratchpad | 0 | 512 b | Phase 5 (P1) |
| Per-warp state (pc5+mask4+sp3+dstk16+flags4) | ~32 | — | divergence stack = 4×4b |
| CSR/control + perf counters (5×16b) | ~82 | — | imem_addr/dsel/flags + counters |
| **Total (Yosys SDFF* count)** | **882** | — | ~5.3k generic cells pre-tech-map (imem/rf read muxes dominate) |
