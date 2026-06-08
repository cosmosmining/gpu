# fw — RP2040 firmware

`warpone.py` — MicroPython firmware for the Tiny Tapeout carrier (RP2040). Drives the
WarpOne CSR host interface over the TT pins to **upload a kernel, launch, run, and read
back** the register file, scratchpad, and performance counters.

## Use (on the TT carrier)
```python
import warpone
warpone.run_kernel("vecadd")     # or "reduce_sum", "dotprod", "parmax"
```
Prints each lane's register file and the perf counters. Expected (golden, from
`PREDICTIONS.md`): vecadd lane *l* → r3 = 3·*l*; reduce_sum → r2 = 6; dotprod → r4 = 26;
parmax → r4 = 3.

## How it works
The project clock is **single-stepped** so the synchronous CSR protocol is exact: a 16-bit
write is two byte transfers (low byte staged in the wrapper's `hold_lo`, high byte commits
`{hi,lo}`), so `core_we` pulses exactly once per write. Pin/CSR map: see
`docs/INTEGRATION.md`. The embedded machine code is produced by `isa/asm.py` from
`kernels/*.asm` (verified equal in CI-style check).

Not hardware-tested in the dev container (no carrier board); written against the TT
MicroPython API (`ttboard`).
