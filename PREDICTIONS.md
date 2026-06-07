# PREDICTIONS

Pre-registered predictions. The **architectural** perf-counter predictions below are
golden-simulator-derived and have been verified RTL==sim in lockstep (33/33), so they are
frozen now. The **timing/area** predictions require the Phase 7 hardening run (OpenROAD /
OpenSTA on sky130A) and are appended when that runs; after that point this file is frozen
and corrections go only in dated addenda (engineering standard #8).

Reproduce the architectural section: `make predict`.

## Architectural perf-counter predictions (FROZEN — golden sim, single warp)

### vecadd  (5 instructions)
- retired = **5**, divergence_pushes = **0**
- active_lane_sum = **20**  → utilization **100.0%**
- bank_conflicts = **0**
- result: lane *l* → r3 = 3·*l*  (lanes 0..3 → 0,3,6,9)

### reduce_sum  (15 instructions; cross-lane sum via scratchpad + BAR)
- retired = **15**, divergence_pushes = **0**
- active_lane_sum = **60**  → utilization **100.0%**
- bank_conflicts = **12**  (four broadcast loads, all lanes one bank → 3 each)
- result: every lane → r2 = 0+1+2+3 = **6**

(dot-product and parallel-max need P2 MUL/SETP, reserved in v1.0 — see ERRATA.)

## Timing / area — PENDING Phase 7 hardening (OpenROAD/OpenSTA, sky130A tt corner)
To be frozen here from the hardening run:
- Fmax, WNS at the 50 MHz target (tt corner).
- Total cells, utilization %, area per block; total flops per block (1891 measured).
- HW cycle counts per kernel (architectural step-counts above + pipeline fill/drain).

## Dated addenda (corrections only; originals above stay intact)
_(none)_
