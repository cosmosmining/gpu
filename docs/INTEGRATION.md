# WarpOne — Integration Guide

> **STATUS: SKELETON (Phase 0).** CSR map, kernel-launch protocol, debug port, and the
> TT pin map are authored in **Phase 1+** as the host interface solidifies.

## TT pin map _(Phase 1)_
Top: `tt_um_warpone`. Standard TT interface (`ui_in[7:0]`, `uo_out[7:0]`,
`uio_in[7:0]`, `uio_out[7:0]`, `uio_oe[7:0]`, `ena`, `clk`, `rst_n`). Per-pin function
assignment (SPI lines on `uio`, status/debug on `uo_out`, test-enable muxing) is
defined here and must match `regs/warpone.rdl`.

## CSR map _(Phase 1, generated from regs/warpone.rdl via PeakRDL)_
control · status · I-mem write window · debug (halt/resume/step/peek) · perf counters.
Address table generated; do not hand-edit.

## Kernel-launch protocol _(Phase 1)_
1. Hold reset / idle. 2. Write program words through the I-mem window. 3. Configure
launch CSR. 4. Poll status for completion/halt. 5. Read back RF / scratchpad / perf
counters via debug + counter CSRs.

## Debug port _(P1)_
Halt, resume, single-step, PC/register peek via CSR.

## RP2040 firmware _(Phase 8, see fw/)_
Upload kernel, launch, read back results, dump perf counters.
