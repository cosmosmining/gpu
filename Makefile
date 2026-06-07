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

.PHONY: help tools decoder smoke lint compliance sim fuzz regress formal cov synth dft harden sweep predict isa clean

help: ## Show this help
	@echo "WarpOne make targets:"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

tools: ## Detect installed toolchain (have/missing report)
	@$(PY) $(ROOT)/scripts/tools.py

decoder: ## regenerate the RTL opcode include from isa/ISA.yaml
	@$(PY) $(ROOT)/scripts/gen_decoder.py

smoke: decoder ## Fast structural + ISA-parse + RTL-compile sanity (Phase 0 gate)
	@$(PY) $(ROOT)/scripts/smoke.py

lint: decoder ## RTL lint: verilator --lint-only (+ Verible if present); 0 errors required
	@$(PY) $(ROOT)/scripts/lint.py

compliance: ## ISA compliance suite on the simulator (Phase 1 gate)
	@$(PY) $(ROOT)/isa/compliance/test_compliance.py

# ---- targets that come online in later phases (scaffolded) --------------------
sim: decoder ## cocotb lockstep sim (RTL vs isa/sim.py)
	@$(MAKE) -C $(ROOT)/dv/cocotb

fuzz: decoder ## constrained-random lockstep campaign (FUZZ_N=10000 default; FUZZ_SEED=1)
	@FUZZ_N=$${FUZZ_N:-10000} FUZZ_SEED=$${FUZZ_SEED:-1} $(MAKE) -C $(ROOT)/dv/cocotb MODULE=test_fuzz

cov: ## show the latest fuzz functional-coverage report
	@$(PY) -c "import json;d=json.load(open('$(ROOT)/dv/fuzz/coverage.json'));print('coverage %.1f%% (%d/%d), %d programs, %d mismatches'%(d['coverage_pct'],d['coverage_hit'],d['coverage_total'],d['programs'],d['mismatches']));[print('  MISS',k) for k,v in d['bins'].items() if not v]"

regress: compliance sim ## run the full regression: ISA compliance + RTL lockstep
	@echo "regress: compliance + RTL lockstep complete."

formal: decoder ## formal proofs (yosys SAT temporal induction): mask-stack + scheduler
	@cd $(ROOT) && yosys -q dv/formal/warpone_mask.ys && echo "formal: PROVEN (temporal induction)"

synth: ## [Phase 5+] Yosys synthesis + cell/flop report
	@echo "[stub] synth: implemented in Phase 5 (Yosys; flop report -> METRICS.md)."

predict: ## emit pre-registered architectural perf-counter predictions per kernel (golden sim)
	@$(PY) $(ROOT)/scripts/predict.py

dft: ## [Phase 6] Fault scan insertion + ATPG (>=95% stuck-at). Requires the Fault tool.
	@if command -v fault >/dev/null 2>&1; then bash $(ROOT)/dft/scan_atpg.sh; \
	 else echo "dft: 'fault' not installed in this env — DFT runs in CI (see dft/README.md, DECISIONS D6.1)."; fi

harden: ## [Phase 7] harden to GDS. Local needs LibreLane/ORFS+sky130; signoff via TT GDS action (CI).
	@echo "harden: GDS signoff runs via the official Tiny Tapeout action (.github/workflows/gds.yml)."
	@echo "        Local LibreLane/ORFS hardening needs the sky130 PDK; see DECISIONS D7.1."

sweep: ## [Phase 7] parallel DSE (pipeline x utilization x clock) -> Pareto (needs hardening flow)
	@echo "sweep: DSE harness drives the harden flow across configs; needs LibreLane/ORFS (D7.1)."

isa: decoder ## regenerate consumers (decoder + asm/sim self-test) + run compliance
	@$(PY) $(ROOT)/isa/asm.py
	@$(PY) $(ROOT)/isa/sim.py
	@$(PY) $(ROOT)/isa/compliance/test_compliance.py

clean: ## Remove build artifacts
	@rm -rf $(ROOT)/build $(ROOT)/sim_build $(ROOT)/**/__pycache__ $(ROOT)/scripts/__pycache__ \
	        $(ROOT)/isa/__pycache__ $(ROOT)/*.vcd $(ROOT)/results.xml $(ROOT)/summary.json 2>/dev/null || true
	@echo "clean: done."
