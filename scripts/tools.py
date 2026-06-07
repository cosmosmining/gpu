#!/usr/bin/env python3
"""WarpOne toolchain detection — `make tools`.

Reports which open-source flow tools are present, which are missing, and which
phase needs them. Missing tools are not failures here; per DECISIONS.md (D0.3),
anything uninstallable locally is wired into CI rather than silently skipped.
"""
import shutil
import sys

# (command, purpose, first phase needed)
TOOLS = [
    ("python3", "scripting / asm / sim", 0),
    ("make", "build entry points", 0),
    ("git", "version control", 0),
    ("iverilog", "Icarus sim + smoke compile", 0),
    ("verilator", "lint + fast sim", 0),
    ("yosys", "synthesis + formal frontend", 4),
    ("sby", "SymbiYosys formal", 4),
    ("verible-verilog-lint", "style lint", 0),
    ("verible-verilog-format", "formatter", 0),
    ("cocotb-config", "cocotb testbench runtime", 2),
    ("peakrdl", "CSR generation from SystemRDL", 1),
    ("openlane", "hardening to GDS (LibreLane)", 7),
    ("openroad", "PnR / STA", 7),
    ("klayout", "GDS/DRC view", 7),
    ("magic", "DRC / extraction", 7),
    ("netgen", "LVS", 7),
]

PY_MODS = [
    ("yaml", "ISA.yaml parsing", 0),
    ("cocotb", "testbench framework", 2),
    ("pytest", "test runner", 2),
    ("numpy", "kernel / model math", 1),
    ("systemrdl", "SystemRDL compiler", 1),
]


def have_cmd(name):
    return shutil.which(name) is not None


def have_mod(name):
    try:
        __import__(name)
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    print("=== WarpOne toolchain ===")
    print("\nExecutables:")
    miss = []
    for cmd, why, phase in TOOLS:
        present = have_cmd(cmd)
        print(f"  [{'x' if present else ' '}] {cmd:<22} P{phase}  {why}")
        if not present:
            miss.append((cmd, phase))
    print("\nPython modules:")
    for mod, why, phase in PY_MODS:
        present = have_mod(mod)
        print(f"  [{'x' if present else ' '}] {mod:<22} P{phase}  {why}")
        if not present:
            miss.append((mod, phase))
    if miss:
        print("\nMissing (deferred to CI per DECISIONS.md D0.3 — never silently skipped):")
        for name, phase in miss:
            print(f"  - {name} (needed by Phase {phase})")
    else:
        print("\nAll tracked tools present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
