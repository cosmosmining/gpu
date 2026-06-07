# WarpOne — Integration Guide

> **STATUS: v1.0 (Phase 2).** Pin map + CSR map for the current core. The host loads a
> program, launches, polls status, and reads back register file / perf counters through
> the CSRs. (Spec §7's SPI→APB3 front-end can replace the parallel shim later without
> changing the CSR map; see DECISIONS D2.1.)

## TT pin map (`tt_um_warpone`)
Single clock (`clk`, 50 MHz target), synchronous active-low reset (`rst_n`), `ena`.
A 16-bit CSR value is written as two byte transfers (low byte staged, high byte commits).

| Pin | Dir | Function |
|---|---|---|
| `ui_in[7:0]`  | in  | host write-data byte |
| `uio_in[3:0]` | in  | CSR address (0..12) |
| `uio_in[4]`   | in  | hi: 0 = stage low byte; 1 = commit write `{ui_in, staged_low}` |
| `uio_in[5]`   | in  | we: write strobe (qualified by `ena`) |
| `uio_in[6]`   | in  | rd_hi: 0 → `uo_out = rdata[7:0]`; 1 → `rdata[15:8]` |
| `uio_in[7]`   | in  | reserved (0) |
| `uo_out[7:0]` | out | CSR read-data byte (selected by rd_hi) |
| `uio_out`,`uio_oe` | out | 0 (uio are inputs in functional mode; test mode muxes scan here in Phase 6) |

## CSR map (backend; mirrors `regs/warpone.rdl`)
| Addr | Name | Acc | Contents |
|---|---|---|---|
| 0x00 | ID       | ro | 0x574F ("WO") |
| 0x01 | CTRL     | rw | [0] launch, [1] reset-core, [3] test_enable |
| 0x02 | STATUS   | ro | [0] running, [1] done, [2] trapped, [9:8] trapcode |
| 0x03 | IMEM_ADDR| rw | I-mem write/read pointer (auto-increments on IMEM_DATA) |
| 0x04 | IMEM_DATA| rw | write `imem[IMEM_ADDR]=data`, addr++ ; read `imem[IMEM_ADDR]` |
| 0x05 | DBG_SEL  | rw | `{lane[1:0], reg[2:0]}` register-file peek selector |
| 0x06 | DBG_RDATA| ro | `rf[lane][reg]` (8-bit, zero-extended) |
| 0x07 | DBG_PC   | ro | `{sp[12:10], mask[9:6], pc[4:0]}` |
| 0x08 | PERF_RETIRED | ro | retired instructions |
| 0x09 | PERF_DIV     | ro | divergence pushes |
| 0x0A | PERF_ACTIVE  | ro | active-lane-sum (→ utilization%) |
| 0x0B | PERF_BANK    | ro | bank conflicts (P1) |
| 0x0C | PERF_CYCLES  | ro | execution cycles |

## Kernel-launch protocol
1. Pulse `rst_n` (or write CTRL.reset-core). 2. `IMEM_ADDR=0`, then stream instructions
to `IMEM_DATA`. 3. Write `CTRL.launch=1`. 4. Poll `STATUS.done`. 5. Read back via
`DBG_SEL`/`DBG_RDATA`, `DBG_PC`, `STATUS` (trap), and `PERF_*`. The cocotb lockstep bench
(`dv/cocotb/test_lockstep.py`) drives exactly this sequence.

## Debug port
`DBG_SEL`/`DBG_RDATA` peek the register file; `DBG_PC` reads PC/mask/stack-pointer;
`STATUS` reports trap. Halt/resume/single-step are added with the 2nd warp in Phase 5.

## RP2040 firmware *(Phase 8, see fw/)*
Upload kernel, launch, read back results, dump perf counters over the pin protocol above.
