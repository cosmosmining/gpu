# WarpOne — reproducible build/test/harden entry points.
# Every result reproduces from a clean clone via `make <target>` (standard #10).
# Real in Phase 0: tools, smoke, lint, clean. Others are scaffolded stubs that
# come online in their phase (see CLAUDE.md table).

SHELL := /bin/bash
PY    ?= python3
ROOT  := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# RTL source roots
RTL_SRCS := $(shell find $(ROOT)/rtl -name '*.v' -o -name '*.sv' 2>/dev/null)

.DEFAULT_GOAL := help

.PHONY: help tools smoke lint compliance sim fuzz regress formal cov synth dft harden sweep predict isa clean

help: ## Show this help
	@echo "WarpOne make targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

tools: ## Detect installed toolchain (have/missing report)
	@$(PY) $(ROOT)/scripts/tools.py

smoke: ## Fast structural + ISA-parse + RTL-compile sanity (Phase 0 gate)
	@$(PY) $(ROOT)/scripts/smoke.py

lint: ## RTL lint: verilator --lint-only (+ Verible if present); 0 errors required
	@$(PY) $(ROOT)/scripts/lint.py

compliance: ## ISA compliance suite on the simulator (Phase 1 gate)
	@$(PY) $(ROOT)/isa/compliance/test_compliance.py

# ---- targets that come online in later phases (scaffolded) --------------------
sim: ## [Phase 2+] cocotb lockstep sim (RTL vs isa/sim.py)
	@echo "[stub] sim: implemented in Phase 2 (lockstep cocotb bench)."

fuzz: ## [Phase 3+] constrained-random program campaign, lockstep
	@echo "[stub] fuzz: implemented in Phase 3 (>=10k legal-by-construction programs)."

regress: compliance ## run the regression (compliance now; + RTL lockstep from Phase 2)
	@echo "regress: compliance done; RTL lockstep suite is added in Phase 2."

formal: ## [Phase 4+] SymbiYosys properties (mask stack, scheduler, decode, write-port)
	@echo "[stub] formal: implemented in Phase 4 (SymbiYosys .sby properties)."

cov: ## [Phase 3+] functional coverage report vs docs/VPLAN.md
	@echo "[stub] cov: implemented in Phase 3 (functional coverage >=95%)."

synth: ## [Phase 5+] Yosys synthesis + cell/flop report
	@echo "[stub] synth: implemented in Phase 5 (Yosys; flop report -> METRICS.md)."

dft: ## [Phase 6] Fault scan insertion + ATPG, stuck-at coverage
	@echo "[stub] dft: implemented in Phase 6 (Fault scan + ATPG, >=95% stuck-at)."

harden: ## [Phase 7] LibreLane/ORFS hardening to GDS
	@echo "[stub] harden: implemented in Phase 7 (LibreLane/ORFS -> GDS)."

sweep: ## [Phase 7] parallel DSE (pipeline x utilization x clock) -> Pareto
	@echo "[stub] sweep: implemented in Phase 7 (parallel DSE -> Pareto table)."

predict: ## [Phase 7] emit pre-registered predictions vs sim
	@echo "[stub] predict: implemented in Phase 7 (freeze PREDICTIONS.md)."

isa: ## validate ISA consumers + run compliance (RTL decoder gen added Phase 2)
	@$(PY) $(ROOT)/isa/asm.py
	@$(PY) $(ROOT)/isa/sim.py
	@$(PY) $(ROOT)/isa/compliance/test_compliance.py

clean: ## Remove build artifacts
	@rm -rf $(ROOT)/build $(ROOT)/sim_build $(ROOT)/**/__pycache__ $(ROOT)/scripts/__pycache__ \
	        $(ROOT)/isa/__pycache__ $(ROOT)/*.vcd $(ROOT)/results.xml $(ROOT)/summary.json 2>/dev/null || true
	@echo "clean: done."
