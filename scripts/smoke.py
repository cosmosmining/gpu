#!/usr/bin/env python3
"""WarpOne smoke test — the Phase 0 gate.

Fast, dependency-light, reproducible from a clean clone. Checks:
  1. Python >= 3.9
  2. isa/ISA.yaml parses and has the required top-level shape
  3. isa/asm.py and isa/sim.py import cleanly (they load ISA.yaml)
  4. the required repository tree exists
  5. if `iverilog` is present, the TT top stub compiles; otherwise this step is
     reported (not failed) — RTL compilation is enforced in CI.

Exit 0 = PASS. Non-zero with a clear message = FAIL.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_fails = 0


def ok(msg):
    print(f"  [ ok ] {msg}")


def note(msg):
    print(f"  [note] {msg}")


def fail(msg):
    global _fails
    _fails += 1
    print(f"  [FAIL] {msg}")


def check_python():
    print("1. Python version")
    if sys.version_info < (3, 9):
        fail(f"Python >= 3.9 required, found {sys.version.split()[0]}")
    else:
        ok(f"Python {sys.version.split()[0]}")


def check_isa():
    print("2. isa/ISA.yaml parses with required shape")
    try:
        import yaml
    except ImportError:
        fail("pyyaml not importable (pip install pyyaml)")
        return
    path = os.path.join(ROOT, "isa", "ISA.yaml")
    if not os.path.isfile(path):
        fail("isa/ISA.yaml missing")
        return
    try:
        with open(path) as f:
            doc = yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001
        fail(f"isa/ISA.yaml failed to parse: {e}")
        return
    if not isinstance(doc, dict):
        fail("isa/ISA.yaml must be a mapping at top level")
        return
    for key in ("isa", "datapath", "encoding", "instructions"):
        if key not in doc:
            fail(f"isa/ISA.yaml missing required top-level key: {key!r}")
    isa = doc.get("isa", {})
    for key in ("name", "version", "frozen"):
        if key not in isa:
            fail(f"isa/ISA.yaml: isa.{key} missing")
    dp = doc.get("datapath", {})
    for key in ("lanes", "width_bits", "regs_per_lane", "warps",
                "imem_entries", "instr_width_bits", "div_stack_depth"):
        if key not in dp:
            fail(f"isa/ISA.yaml: datapath.{key} missing")
    if _fails == 0:
        ok(f"ISA '{isa.get('name')}' v{isa.get('version')} "
           f"(frozen={isa.get('frozen')}); {len(doc.get('instructions') or {})} instr defined")


def _import_file(name, relpath):
    path = os.path.join(ROOT, relpath)
    if not os.path.isfile(path):
        fail(f"{relpath} missing")
        return
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok(f"{relpath} imports clean")
    except Exception as e:  # noqa: BLE001
        fail(f"{relpath} failed to import: {e}")


def check_consumers():
    print("3. ISA consumers import cleanly")
    _import_file("warpone_asm", "isa/asm.py")
    _import_file("warpone_sim", "isa/sim.py")


def check_tree():
    print("4. required repository tree exists")
    req_dirs = [
        "docs", "isa", "isa/compliance", "rtl/core", "rtl/tt_top", "regs",
        "dv/cocotb", "dv/fuzz", "dv/formal", "dft", "synth", "pnr", "fw",
        "kernels", "scripts", ".github/workflows", ".claude/commands",
    ]
    req_files = [
        "CLAUDE.md", "STATUS.md", "DECISIONS.md", "METRICS.md", "PREDICTIONS.md",
        "Makefile", "isa/ISA.yaml", "isa/asm.py", "isa/sim.py",
        "regs/warpone.rdl", "dv/regression.list",
        "docs/SPEC.md", "docs/VPLAN.md", "docs/INTEGRATION.md", "docs/ERRATA.md",
        "rtl/tt_top/tt_um_warpone.v", ".claude/settings.json",
    ]
    for d in req_dirs:
        if not os.path.isdir(os.path.join(ROOT, d)):
            fail(f"missing dir: {d}/")
    for f in req_files:
        if not os.path.isfile(os.path.join(ROOT, f)):
            fail(f"missing file: {f}")
    if _fails == 0:
        ok(f"{len(req_dirs)} dirs + {len(req_files)} files present")


def check_rtl_compile():
    print("5. RTL TT-top compiles (iverilog, if present)")
    top = os.path.join(ROOT, "rtl", "tt_top", "tt_um_warpone.v")
    if not os.path.isfile(top):
        fail("rtl/tt_top/tt_um_warpone.v missing")
        return
    iv = shutil.which("iverilog")
    if not iv:
        note("iverilog absent locally — RTL compile is enforced in CI (lint.yml/test.yml)")
        return
    srcs = []
    for base, _dirs, files in os.walk(os.path.join(ROOT, "rtl")):
        for fn in files:
            if fn.endswith((".v", ".sv")):
                srcs.append(os.path.join(base, fn))
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "a.out")
        cmd = [iv, "-g2012", "-Wall", "-o", out] + srcs
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail("iverilog compile failed:\n" + (r.stderr or r.stdout))
        else:
            ok(f"iverilog compiled {len(srcs)} RTL file(s) clean")


def main():
    print("=== WarpOne smoke ===")
    check_python()
    check_isa()
    check_consumers()
    check_tree()
    check_rtl_compile()
    print("=====================")
    if _fails:
        print(f"SMOKE: FAIL ({_fails} problem(s))")
        return 1
    print("SMOKE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
