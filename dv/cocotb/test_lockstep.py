"""RTL-vs-simulator lockstep bench (Phase 2 / Phase 5 gate).

Runs each directed kernel on the RTL (warpone_core, 2 warps) and the golden simulator
(isa/sim.py), then compares per-warp retired state (register file, PC, mask, divergence-
stack pointer, trap), the shared scratchpad, and all architectural perf counters. Any
mismatch fails. ISA.yaml arbitrates; the sim is never edited to make RTL pass (std #2).
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

A_ID, A_CTRL, A_STATUS, A_IADDR, A_IDATA, A_DSEL, A_DRD, A_DPC, \
    A_RET, A_DIV, A_ACT, A_BANK, A_CYC, A_WSTAT, A_SCR = range(15)

NWARPS, LANES, REGS, SCRATCH = 2, 4, 8, 64
ASM = Assembler()


async def csr_write(dut, addr, data):
    dut.csr_addr.value = addr
    dut.csr_wdata.value = data & 0xFFFF
    dut.csr_we.value = 1
    await RisingEdge(dut.clk)
    dut.csr_we.value = 0


async def csr_read(dut, addr):
    dut.csr_addr.value = addr
    await Timer(1, unit="ns")
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


async def run_core(dut, timeout=6000):
    await csr_write(dut, A_CTRL, 0x1)
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        if (await csr_read(dut, A_STATUS)) & 0x2:
            return True
    return False


async def read_state(dut, read_scratch=True):
    warps = []
    for w in range(NWARPS):
        regs = [[0] * REGS for _ in range(LANES)]
        for lane in range(LANES):
            for r in range(REGS):
                await csr_write(dut, A_DSEL, (w << 5) | (lane << 3) | r)
                regs[lane][r] = await csr_read(dut, A_DRD)
        await csr_write(dut, A_DSEL, (w << 5))
        dpc = await csr_read(dut, A_DPC)
        wst = await csr_read(dut, A_WSTAT)
        warps.append({
            "regs": regs, "pc": dpc & 0x1F, "mask": (dpc >> 6) & 0xF, "sp": (dpc >> 10) & 0x7,
            "halted": wst & 1, "trapcode": (wst >> 1) & 3,
            "trapped": (wst >> 3) & 1, "barriered": (wst >> 4) & 1,
        })
    scratch = [0] * SCRATCH
    if read_scratch:
        for a in range(SCRATCH):
            await csr_write(dut, A_DSEL, a)
            scratch[a] = await csr_read(dut, A_SCR)
    return {
        "warps": warps, "scratch": scratch,
        "ret": await csr_read(dut, A_RET), "div": await csr_read(dut, A_DIV),
        "act": await csr_read(dut, A_ACT), "bank": await csr_read(dut, A_BANK),
        "cyc": await csr_read(dut, A_CYC),
    }


def sim_state(words):
    s = Simulator()
    s.load_program(words, active_warps=NWARPS)
    snap = s.run()
    warps = []
    for w in range(NWARPS):
        tr, tc = snap["trapped"][w]
        warps.append({
            "regs": snap["regs"][w], "pc": snap["pc"][w], "mask": snap["mask"][w],
            "sp": snap["sp"][w], "halted": 1 if snap["halted"][w] else 0,
            "trapped": 1 if tr else 0, "trapcode": tc,
        })
    p = snap["perf"]
    return {
        "warps": warps, "scratch": snap["scratch"], "snap": snap,
        "ret": p["retired"], "div": p["divergence_pushes"], "act": p["active_lane_sum"],
        "bank": p["bank_conflicts"], "cyc": p["cycles"],
    }


def compare(name, rtl, sim, check_scratch=True):
    diffs = []
    for k in ("ret", "div", "act", "bank", "cyc"):
        if rtl[k] != sim[k]:
            diffs.append(f"{k}: rtl={rtl[k]} sim={sim[k]}")
    for w in range(NWARPS):
        for k in ("pc", "mask", "sp", "trapped", "trapcode"):
            if rtl["warps"][w][k] != sim["warps"][w][k]:
                diffs.append(f"w{w}.{k}: rtl={rtl['warps'][w][k]} sim={sim['warps'][w][k]}")
        for lane in range(LANES):
            for r in range(REGS):
                a, b = rtl["warps"][w]["regs"][lane][r], sim["warps"][w]["regs"][lane][r]
                if a != b:
                    diffs.append(f"w{w}.r{r}[lane{lane}]: rtl={a} sim={b}")
    if check_scratch:
        for a in range(SCRATCH):
            if rtl["scratch"][a] != sim["scratch"][a]:
                diffs.append(f"scratch[{a}]: rtl={rtl['scratch'][a]} sim={sim['scratch'][a]}")
    assert not diffs, f"LOCKSTEP MISMATCH in '{name}':\n  " + "\n  ".join(diffs[:20])


async def lockstep(dut, name, words):
    await reset_dut(dut)
    await load(dut, words)
    finished = await run_core(dut)
    assert finished, f"{name}: core did not reach done (timeout)"
    rtl = await read_state(dut)
    sim = sim_state(words)
    compare(name, rtl, sim)


@cocotb.test()
async def lockstep_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    n = 0
    for name, text in PROGRAMS:
        await lockstep(dut, name, ASM.assemble(text))
        n += 1
    await lockstep(dut, "reserved_opcode", [0x15 << 11, 0x01 << 11])
    n += 1
    dut._log.info(f"LOCKSTEP: {n}/{len(PROGRAMS)+1} kernels bit-exact RTL vs sim (2 warps)")
