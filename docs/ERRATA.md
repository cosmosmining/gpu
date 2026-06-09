# WarpOne — Errata

> Known issues, deviations from spec, and silicon bugs. Each entry: id, date, severity,
> description, workaround, status.

## E1 — 2026-06-08 — Full design exceeds the 4×2 tile (HIGH; gates Phase 7 GDS)
Real sky130A place-and-route (LibreLane via tt-gds-action@ttsky26c, run 27157849886) ran
the full flow and **failed at global routing with congestion** (`[GRT-0116]`). Measured:
- design placement area **565.55 × 576.27 µm (~326k µm²)** vs 4×2 die **682.64 × 225.76 µm
  (~154k µm²)** — the design is **~2.1× the 4×2 area** and the wrong aspect (576 µm tall).
- global congestion 79.5% (met2 86.5%); setup violations not fully repaired.

Cause: the variable-index read-mux trees over I-mem (32×16), the 2×4×8×8 register file, and
the 4-bank scratchpad across 2 warps dominate area (~16.8k generic cells).

Workaround / status: **RESOLVED via larger tile (re-harden pending).** Operator approved
moving to a **6×4** tile (DECISIONS D7.3), keeping the full verified 2-warp + P2 +
scratchpad design (no feature loss, no re-verification). 6×4 ≈ 527k µm² → ~60% util. The
RTL is functionally complete and fully verified; this was a physical-area/PPA tradeoff,
not a bug. (The area fallback ladder remains the path if a 4×2 part is ever required.)

