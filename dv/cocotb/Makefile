# cocotb lockstep bench (RTL vs isa/sim.py). Run from repo root via `make sim` / `make fuzz`.
# Verilator: handles the multi-dim arrays correctly and is fast (good for the 10k fuzz).
SIM           ?= verilator
TOPLEVEL_LANG ?= verilog

ROOT := $(shell cd ../.. && pwd)

VERILOG_SOURCES := $(ROOT)/rtl/core/warpone_core.v
EXTRA_ARGS      += -I$(ROOT)/rtl/core --trace-depth 0

TOPLEVEL := warpone_core
MODULE   ?= test_lockstep

include $(shell cocotb-config --makefiles)/Makefile.sim
