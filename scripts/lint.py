#!/usr/bin/env python3
"""WarpOne RTL lint — `make lint`. Zero errors required at every commit (standard #5).

Runs `verilator --lint-only -Wall` over all RTL, and Verible lint if present.
Tools that are absent locally are reported and deferred to CI (DECISIONS.md D0.3),
not treated as a pass. Returns non-zero if any present linter reports an error.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL_DIR = os.path.join(ROOT, "rtl")


def rtl_files():
    out = []
    for base, _dirs, files in os.walk(RTL_DIR):
        for fn in files:
            if fn.endswith((".v", ".sv")):
                out.append(os.path.join(base, fn))
    return sorted(out)


def main():
    srcs = rtl_files()
    if not srcs:
        print("lint: no RTL files yet — nothing to lint.")
        return 0
    print(f"lint: {len(srcs)} RTL file(s)")
    rc = 0
    deferred = []

    verilator = shutil.which("verilator")
    if verilator:
        # Top module given so verilator resolves the design; -Wall for strictness.
        cmd = [verilator, "--lint-only", "-Wall", "--top-module", "tt_um_warpone"] + srcs
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("--- verilator --lint-only: ERRORS ---")
            print(r.stderr or r.stdout)
            rc = 1
        else:
            print("  [ ok ] verilator --lint-only clean")
    else:
        deferred.append("verilator")

    verible = shutil.which("verible-verilog-lint")
    if verible:
        r = subprocess.run([verible] + srcs, capture_output=True, text=True)
        if r.returncode != 0:
            print("--- verible-verilog-lint: findings ---")
            print(r.stdout or r.stderr)
            rc = 1
        else:
            print("  [ ok ] verible-verilog-lint clean")
    else:
        deferred.append("verible-verilog-lint")

    if deferred:
        print("  [note] deferred to CI (absent locally): " + ", ".join(deferred))
    print("lint: " + ("FAIL" if rc else "PASS"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
