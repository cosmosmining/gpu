"""WarpOne RP2040 firmware (Tiny Tapeout carrier, MicroPython / ttboard API).

Drives the WarpOne CSR host interface over the TT pins to: load a kernel into I-mem,
launch, run, and read back the register file / scratchpad / performance counters.

Pin/CSR protocol (must match rtl/tt_top/tt_um_warpone.v + docs/INTEGRATION.md):
  ui_in[7:0]   host write-data byte
  uio_in[3:0]  CSR address          uio_in[4] hi (0=stage low byte, 1=commit {hi,lo})
  uio_in[5]    write strobe (we)    uio_in[6] rd_hi (0 -> uo_out=rdata[7:0], 1 -> [15:8])
  uo_out[7:0]  CSR read-data byte
A 16-bit CSR value is two byte transfers (low staged, high commits). The project clock is
single-stepped so each `we` is sampled exactly once (core_we pulses only on the commit).

NOTE: written against the TT MicroPython API; not hardware-tested in this environment
(no carrier board). Reproduce the machine code with `isa/asm.py`.
"""
try:
    from ttboard.demoboard import DemoBoard
except ImportError:
    DemoBoard = None  # allows host-side import / linting without the board

# CSR addresses (match warpone_core.v)
A_ID, A_CTRL, A_STATUS, A_IADDR, A_IDATA, A_DSEL, A_DRD, A_DPC, \
    A_RET, A_DIV, A_ACT, A_BANK, A_CYC, A_WSTAT, A_SCR = range(15)

# Demo kernels (assembled by isa/asm.py from kernels/*.asm)
PROGRAMS = {
    "vecadd":     [0x5800, 0x1101, 0x4a04, 0x2308, 0x0800],
    "reduce_sum": [0x5800, 0x8000, 0x8800, 0x1100, 0x7a20, 0x1101, 0x7b20, 0x224c,
                   0x1102, 0x7b20, 0x224c, 0x1103, 0x7b20, 0x224c, 0x0800],
    "dotprod":    [0x5800, 0x1102, 0x2104, 0x9204, 0x8200, 0x8800, 0x1300, 0x7c60,
                   0x1301, 0x7d60, 0x2494, 0x1302, 0x7d60, 0x2494, 0x1303, 0x7d60,
                   0x2494, 0x0800],
    "parmax":     [0x5800, 0x1102, 0x4204, 0x8200, 0x8800, 0x1300, 0x7c60, 0x1301,
                   0x7d60, 0x9e94, 0xa4d4, 0x1302, 0x7d60, 0x9e94, 0xa4d4, 0x1303,
                   0x7d60, 0x9e94, 0xa4d4, 0x0800],
}


class WarpOne:
    def __init__(self, tt):
        self.tt = tt

    def _step(self):
        self.tt.clock_project_once()

    def csr_write(self, addr, val):
        # stage low byte (we=1, hi=0): wrapper latches hold_lo, core_we stays 0
        self.tt.ui_in.value = val & 0xFF
        self.tt.uio_in.value = (addr & 0xF) | (1 << 5)
        self._step()
        # commit (we=1, hi=1): core_we pulses once, csr_wdata = {hi, lo}
        self.tt.ui_in.value = (val >> 8) & 0xFF
        self.tt.uio_in.value = (addr & 0xF) | (1 << 4) | (1 << 5)
        self._step()
        self.tt.uio_in.value = 0           # deassert we

    def csr_read(self, addr):
        # combinational read; select low then high byte via rd_hi
        self.tt.uio_in.value = (addr & 0xF)
        lo = self.tt.uo_out.value & 0xFF
        self.tt.uio_in.value = (addr & 0xF) | (1 << 6)
        hi = self.tt.uo_out.value & 0xFF
        return (hi << 8) | lo

    def reset(self):
        self.tt.reset_project(True)
        for _ in range(3):
            self._step()
        self.tt.reset_project(False)
        self._step()

    def load(self, words):
        self.csr_write(A_IADDR, 0)
        for w in words:
            self.csr_write(A_IDATA, w)

    def launch(self):
        self.csr_write(A_CTRL, 0x1)

    def run(self, max_cycles=4000):
        for _ in range(max_cycles):
            self._step()
            if self.csr_read(A_STATUS) & 0x2:    # done
                return True
        return False

    def reg(self, warp, lane, r):
        self.csr_write(A_DSEL, (warp << 5) | (lane << 3) | r)
        return self.csr_read(A_DRD) & 0xFF

    def scratch(self, addr):
        self.csr_write(A_DSEL, addr & 0x3F)
        return self.csr_read(A_SCR) & 0xFF

    def perf(self):
        return {
            "cycles": self.csr_read(A_CYC), "retired": self.csr_read(A_RET),
            "divergence": self.csr_read(A_DIV), "active_lane_sum": self.csr_read(A_ACT),
            "bank_conflicts": self.csr_read(A_BANK),
        }


def run_kernel(name="vecadd"):
    if DemoBoard is None:
        raise RuntimeError("ttboard not available — run on the TT RP2040 carrier")
    tt = DemoBoard.get()
    tt.shuttle.tt_um_warpone.enable()
    tt.clock_project_stop()                 # we single-step the clock
    w = WarpOne(tt)
    w.reset()
    w.load(PROGRAMS[name])
    w.launch()
    ok = w.run()
    print("kernel:", name, "done" if ok else "TIMEOUT")
    for lane in range(4):
        regs = [w.reg(0, lane, r) for r in range(8)]
        print("  warp0 lane", lane, "regs", regs)
    print("  perf:", w.perf())
    return ok


if __name__ == "__main__":
    run_kernel("vecadd")
