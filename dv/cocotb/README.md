# dv/cocotb — lockstep testbench + directed suites

cocotb benches that run identical programs on the RTL and `isa/sim.py`, comparing
retired-instruction state (PC trace, RF, scratchpad, masks). Plus directed
divergence/barrier/bank-conflict suites. Lands in **Phase 2**.
