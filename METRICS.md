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

## Flop budget tracker (scarcest resource)
Hard caps without operator approval:
- I-mem ≤ 64 × 16b = 1024 b
- Register file ≤ 2 warps × 4 lanes × 8 regs × 8b = 512 b
- Scratchpad ≤ 4 banks × 16 × 8b = 512 b

| block | flops (current) | cap | notes |
|-------|-----------------|-----|-------|
| I-mem | 0 | 1024 b | Phase 2 |
| Register file | 0 | 512 b | Phase 2 |
| Scratchpad | 0 | 512 b | Phase 5 |
| Per-warp state (PC, mask, div-stack ×4) | 0 | — | Phase 2 |
| CSRs / perf counters | 0 | — | Phase 2 / Phase 5 |
| **Total** | **0** | — | populated once RTL exists |
