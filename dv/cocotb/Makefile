# cocotb lockstep bench (RTL vs isa/sim.py). Run from repo root via `make sim`.
SIM           ?= icarus
TOPLEVEL_LANG ?= verilog

ROOT := $(shell cd ../.. && pwd)

VERILOG_SOURCES := $(ROOT)/rtl/core/warpone_core.v
COMPILE_ARGS    += -I$(ROOT)/rtl/core -g2012

TOPLEVEL := warpone_core
MODULE   := test_lockstep

include $(shell cocotb-config --makefiles)/Makefile.sim
