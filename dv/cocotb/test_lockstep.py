"""RTL-vs-simulator lockstep bench (Phase 2 gate).

Runs each directed P0 kernel on the RTL (warpone_core, via its CSR interface) and on the
golden simulator (isa/sim.py), then compares retired-instruction state: register file,
PC, active mask, divergence-stack pointer, trap, and all architectural perf counters.
Any mismatch fails. ISA.yaml arbitrates; the sim is never edited to make RTL pass (std #2).
"""
import os
import sys

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "isa"))
sys.path.insert(0, HERE)

from asm import Assembler          # noqa: E402
from sim import Simulator          # noqa: E402
from programs import PROGRAMS      # noqa: E402

# CSR addresses (must match rtl/core/warpone_core.v)
A_ID, A_CTRL, A_STATUS, A_IADDR, A_IDATA, A_DSEL, A_DRD, A_DPC, \
    A_RET, A_DIV, A_ACT, A_BANK, A_CYC = range(13)

ASM = Assembler()


async def csr_write(dut, addr, data):
    dut.csr_addr.value = addr
    dut.csr_wdata.value = data & 0xFFFF
    dut.csr_we.value = 1
    await RisingEdge(dut.clk)
    dut.csr_we.value = 0


async def csr_read(dut, addr):
    dut.csr_addr.value = addr
    await Timer(1, unit="ns")          # combinational read settles
    return int(dut.csr_rdata.value)


async def reset_dut(dut):
    dut.csr_we.value = 0
    dut.csr_re.value = 0
    dut.csr_addr.value = 0
    dut.csr_wdata.value = 0
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def load(dut, words):
    await csr_write(dut, A_IADDR, 0)
    for w in words:
        await csr_write(dut, A_IDATA, w)


async def run_core(dut, timeout=5000):
    await csr_write(dut, A_CTRL, 0x1)         # launch
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        if (await csr_read(dut, A_STATUS)) & 0x2:   # done
            return True
    return False


async def read_state(dut):
    regs = [[0] * 8 for _ in range(4)]
    for lane in range(4):
        for r in range(8):
            await csr_write(dut, A_DSEL, (lane << 3) | r)
            regs[lane][r] = await csr_read(dut, A_DRD)
    dpc = await csr_read(dut, A_DPC)
    status = await csr_read(dut, A_STATUS)
    return {
        "regs": regs,
        "pc": dpc & 0x1F,
        "mask": (dpc >> 6) & 0xF,
        "sp": (dpc >> 10) & 0x7,
        "trapped": (status >> 2) & 1,
        "trapcode": (status >> 8) & 0x3,
        "ret": await csr_read(dut, A_RET),
        "div": await csr_read(dut, A_DIV),
        "act": await csr_read(dut, A_ACT),
        "bank": await csr_read(dut, A_BANK),
        "cyc": await csr_read(dut, A_CYC),
    }


def sim_state(words):
    sim = Simulator()
    sim.load_program(words, active_warps=1)
    s = sim.run()
    p = s["perf"]
    tr, tc = s["trapped"][0]
    return {
        "regs": s["regs"][0],
        "pc": s["pc"][0],
        "mask": s["mask"][0],
        "sp": s["sp"][0],
        "trapped": 1 if tr else 0,
        "trapcode": tc,
        "ret": p["retired"],
        "div": p["divergence_pushes"],
        "act": p["active_lane_sum"],
        "bank": p["bank_conflicts"],
        "cyc": p["cycles"],
    }


def compare(name, rtl, sim):
    diffs = []
    for k in ("pc", "mask", "sp", "trapped", "trapcode",
              "ret", "div", "act", "bank", "cyc"):
        if rtl[k] != sim[k]:
            diffs.append(f"{k}: rtl={rtl[k]} sim={sim[k]}")
    for lane in range(4):
        for r in range(8):
            if rtl["regs"][lane][r] != sim["regs"][lane][r]:
                diffs.append(f"r{r}[lane{lane}]: rtl={rtl['regs'][lane][r]} "
                             f"sim={sim['regs'][lane][r]}")
    assert not diffs, f"LOCKSTEP MISMATCH in '{name}':\n  " + "\n  ".join(diffs)


async def _lockstep(dut, name, words):
    await reset_dut(dut)
    await load(dut, words)
    finished = await run_core(dut)
    assert finished, f"{name}: core did not reach done (timeout)"
    rtl = await read_state(dut)
    sim = sim_state(words)
    compare(name, rtl, sim)
    dut._log.info(f"[lockstep ok] {name}: ret={rtl['ret']} div={rtl['div']} "
                  f"act={rtl['act']} cyc={rtl['cyc']}")


@cocotb.test()
async def lockstep_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    npass = 0
    for name, text in PROGRAMS:
        words = ASM.assemble(text)
        await _lockstep(dut, name, words)
        npass += 1
    # reserved-opcode raw program (cannot be assembled): illegal-instruction trap
    await _lockstep(dut, "reserved_opcode", [0x15 << 11, 0x01 << 11])
    npass += 1
    dut._log.info(f"LOCKSTEP: {npass}/{len(PROGRAMS)+1} kernels bit-exact RTL vs sim")
