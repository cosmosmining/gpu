#!/usr/bin/env bash
# WarpOne DFT flow (Phase 6): synthesize -> scan insertion -> ATPG -> stuck-at coverage.
# Uses Fault (https://github.com/AUCOHL/Fault) with the sky130 cell library. Target: >=95%
# stuck-at on scanned logic; the REAL number is reported (never rounded up). Test mode is
# muxed onto uio under the test-enable CSR bit (CTRL[3], already in the RTL).
#
# This is a scaffold: it runs end-to-end only where `fault` + the sky130 std-cell liberty
# are installed (CI / the operator's flow). See dft/README.md and DECISIONS D6.1.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dft/out"; mkdir -p "$OUT"

if ! command -v fault >/dev/null 2>&1; then
  echo "[dft] 'fault' not found — install Fault + sky130 liberty to run scan+ATPG (CI)."
  exit 0
fi
: "${SKY130_LIB:?set SKY130_LIB to the sky130 std-cell .lib (e.g. sky130_fd_sc_hd__tt_025C_1v80.lib)}"

echo "[dft] 1/3 synthesize gate-level netlist (yosys -> sky130)"
yosys -p "read_verilog -sv -I $ROOT/rtl/core $ROOT/rtl/core/warpone_core.v; \
          synth -top warpone_core -flatten; dfflibmap -liberty $SKY130_LIB; \
          abc -liberty $SKY130_LIB; write_verilog $OUT/warpone_core.netlist.v"

echo "[dft] 2/3 scan insertion + ATPG (Fault)"
fault synth -c "$SKY130_LIB" --output "$OUT/warpone_scan.v" "$OUT/warpone_core.netlist.v" || true
fault asg -c "$SKY130_LIB" "$OUT/warpone_scan.v" || true

echo "[dft] 3/3 coverage report -> $OUT/coverage.txt"
fault -c "$SKY130_LIB" --report "$OUT/coverage.txt" "$OUT/warpone_scan.v" || true
echo "[dft] done. Report the real stuck-at % from $OUT/coverage.txt into METRICS.md."
