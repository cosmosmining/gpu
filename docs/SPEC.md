# WarpOne — Microarchitecture Specification

> **STATUS: v1.0 (Phase 1).** ISA frozen at `isa/ISA.yaml` v1.0.0. This document is
> normative for the microarchitecture. Core RTL (Phase 2+) is verified in lockstep
> against `isa/sim.py`, which implements this spec; when RTL and sim disagree, the ISA
> `sem` annotations arbitrate (standard #2).

## 1. Overview
4-lane, 2-warp SIMT compute core. The point is to demonstrate, in observable silicon,
the control mechanisms that define GPUs: lockstep lanes, predicated execution under
divergence, warp interleaving, banked-memory conflicts, and the counters that expose
them. Throughput is explicitly **not** a goal.

## 2. Datapath (authoritative params in `isa/ISA.yaml § datapath`)
- 4 lanes × 8-bit. 8 general-purpose registers per lane per warp (r0..r7; no hardwired zero).
- 16-bit fixed-width instructions. 5-bit opcode, three 3-bit register fields, 8-bit imm.
- 2 hardware warps. Per-warp state: PC (6b), active mask M (4b), 4-deep divergence
  stack of saved masks + stack pointer, register file (4×8×8b), halted/barriered/trap flags.
- Scratchpad (P1): 4 banks × 16 × 8b = 64 B, shared across warps. `bank = addr[1:0]`,
  `index = addr[5:2]`.
- **All storage is flops** (no SRAM macros). Flop budget tracked in `METRICS.md`.

## 3. Pipeline (4-stage, in-order)
`F → D → X → W`:
- **F (fetch):** read I-mem[PC] (flop array). One instruction per issued warp per cycle.
- **D (decode):** opcode/field decode from the ISA-generated decoder; read register file
  for the issuing warp's 4 lanes; scheduler selects the issuing warp.
- **X (execute):** 4 parallel 8-bit ALUs; SPLIT/JOIN mask algebra; branch/PC resolve;
  scratchpad access (P1); shared iterative multiplier (P2).
- **W (writeback):** masked register-file write (active lanes only); PC/mask/stack
  update; performance-counter update.

### 3.1 Hazard strategy (why this hits 50 MHz with no stalls)
Primary mechanism is **fine-grained (barrel) multithreading** — the canonical GPU
technique. With 2 warps issued round-robin, consecutive instructions of the *same* warp
are ≥2 cycles apart, which covers the D→W distance, so RAW hazards are hidden with zero
stalls when both warps are runnable. The register file is **write-first** (write in the
first half of the cycle, read in the second), and a single result-forwarding path
(X/W → D) covers the single-warp (P0) case so back-to-back dependent ALU ops also incur
no stall. Control changes (JMP/SPLIT/JOIN) resolve in X with a 1-cycle fetch bubble;
with 2 warps the bubble is filled by the other warp (0 effective penalty).

### 3.2 Timing justification (target 20 ns / 50 MHz; confirmed by OpenSTA in Phase 7)
Expected critical path: register-file read → forwarding mux → 8-bit ALU (add/sub is the
deepest, ~ripple of 8) → writeback mux. In sky130 at the tt corner an 8-bit add plus a
few mux levels and a small flop-based RF read is well under 20 ns; the decoder is a tiny
combinational LUT off the 5-bit opcode. The 8×8 multiplier (P2) is **iterative**
(time-multiplexed, multi-cycle) specifically so it never sits on the single-cycle path.
Pre-registered Fmax/WNS go in `PREDICTIONS.md` (Phase 7) and are measured, not asserted.

## 4. Warp scheduler
Round-robin over runnable warps. A warp is *runnable* iff not `halted` and not
`barriered`. Each cycle the scheduler issues the next runnable warp (wrapping). If no
warp is runnable: if all are halted → done; if remaining warps are barriered and the
barrier can release → release; else → deadlock (caught by the cycle cap). Fairness and
no-deadlock are proven formally in Phase 4.

## 5. Divergence semantics — SPLIT / JOIN  *(GATE ITEM — fully worked below)*
Structured divergence over a 4-deep per-warp stack, **one entry per SPLIT**.

**State:** active mask `M` (4 bits, one per lane), divergence stack `DS` of saved masks,
stack pointer `SP` (0..4).

**`SPLIT rp`** (predicate register `rp`, field `a`):
1. Compute the per-lane taken set among currently active lanes:
   `t[l] = M[l] AND (R[l][rp] != 0)`.
2. If `SP == 4` → **TRAP(stack_overflow)** (halt warp; no silent wrap).
3. Else: `DS[SP] = M; SP += 1; M = M AND t`. PC advances.
   Inactive lanes stay inactive; if no lane is taken, `M` becomes 0 and the then-region
   still *executes* but writes nothing (the all-lanes-inactive case).

**`JOIN`:**
1. If `SP == 0` → **TRAP(stack_underflow)**.
2. Else: `SP -= 1; M = DS[SP]` (reconverge). PC advances.

This is genuine SIMT divergence: within the then-region only the taken lanes are active
(masked predication), the not-taken lanes are idle, and reconvergence restores the prior
mask. `if/else` is expressed as two masked regions (SPLIT p … JOIN; SPLIT ¬p … JOIN);
nesting consumes stack depth. Because masked-off lanes still consume cycles, the
`active_lane_sum` / utilization counter directly exposes the cost of divergence — which
is the pedagogical payoff.

### 5.1 Worked example (cycle-by-cycle mask + PC trace)
Program (single warp, 4 lanes; all lanes start active, `M = 1111`, `SP = 0`):

```
addr  instruction     intent
 0    LANEID r0        r0[l] = l            -> lane0=0, lane1=1, lane2=2, lane3=3
 1    LDI    r1, 100   r1 = 100 (all lanes)
 2    SPLIT  r0        diverge: taken where r0 != 0  -> lanes 1,2,3
 3    LDI    r1, 200   then-region: only active (taken) lanes write
 4    JOIN             reconverge
 5    LDI    r2, 9     all lanes write 9
 6    HALT
```

Retirement trace (mask shown as lane3 lane2 lane1 lane0):

| step | PC | instruction | M (exec) | DS before | action                          | M after | DS after |
|------|----|-------------|----------|-----------|---------------------------------|---------|----------|
| 1 | 0 | LANEID r0  | `1111` | `[]`      | r0[l]=l                          | `1111` | `[]`       |
| 2 | 1 | LDI r1,100 | `1111` | `[]`      | r1=100 all                       | `1111` | `[]`       |
| 3 | 2 | SPLIT r0   | `1111` | `[]`      | t=`1110`; push `1111`; narrow    | `1110` | `[1111]`   |
| 4 | 3 | LDI r1,200 | `1110` | `[1111]`  | r1=200 on lanes 1,2,3            | `1110` | `[1111]`   |
| 5 | 4 | JOIN       | `1110` | `[1111]`  | pop → reconverge                 | `1111` | `[]`       |
| 6 | 5 | LDI r2,9   | `1111` | `[]`      | r2=9 all                         | `1111` | `[]`       |
| 7 | 6 | HALT       | `1111` | `[]`      | halt warp                        | —      | `[]`       |

**Result:** lane0 `r1=100` (masked out of the then-region); lanes 1–3 `r1=200`; all
lanes `r2=9`. Counters: `divergence_pushes=1`, `retired=7`,
`active_lane_sum = 4+4+4+3+3+4+4 = 26`, `utilization = 26/(7·4) = 92.86%`.
This exact program and these exact numbers are asserted in
`isa/compliance/test_compliance.py::test_split_join_basic`.

A depth-2 nested example is worked in `test_split_nested` (divergence_pushes=2).

## 6. Memory
- **I-mem:** 32×16b (P0; up to 64 in P1 if area allows). CSR-loadable write window.
- **Register file:** 2×4×8×8b = 512 b, write-first, masked writes.
- **Scratchpad (P1):** 4 banks × 16 × 8b. Per active lane: `addr = R[rs_addr] & 0x3F`.
  Bank-conflict serialization: lanes hitting distinct banks proceed together; lanes
  sharing a bank serialize. `bank_conflicts += active_lanes − distinct_banks_touched`
  per LD/ST. On `ST` collisions to the same address, **lowest lane id wins**
  (deterministic, so the sim is bit-exact).

## 7. Host interface
SPI slave → APB3 → PeakRDL CSRs (`regs/warpone.rdl`): I-mem write window, launch/halt
control, status, lane-register peek, debug (halt/resume/step), perf counters. Protocol
in `docs/INTEGRATION.md`.

## 8. Performance counters
Architectural (pipeline-independent; validated every lockstep run): `retired`,
`divergence_pushes`, `active_lane_sum` (→ utilization %), `bank_conflicts`. Timing
(pipeline-dependent; predicted by the Phase 7 timing model and frozen in
`PREDICTIONS.md`): `cycles`, `stall_cycles` by cause.

## 9. Traps (decode completeness — no X)
Every 16-bit value decodes: opcodes `0x15..0x1F` are reserved and **trap** as
illegal-instruction; SPLIT overflow and JOIN underflow trap. A trap sets the warp's
`trap`/`trap_code` and halts the warp. Proven exhaustively in Phase 4.

## 10. DFT *(Phase 6)*
Scan insertion + ATPG (Fault); test mode muxed onto `uio` under a test-enable CSR bit;
target ≥95% stuck-at on scanned logic (report the real number).

## 11. Area fallback ladder
Apply top-down if >70% utilization: drop P2 → I-mem 64→32 → scratchpad 4→2 banks →
drop second warp but keep scheduler interfaces. **Never** drop the divergence stack,
LANEID, perf counters, debug peek, or scan once implemented.
