---
description: Run the directed + compliance regression and summarize results
allowed-tools: Bash(make regress), Bash(make:*)
---
Run `make regress`. Summarize pass/fail counts and list any mismatches. On failure,
identify the first failing test and the exact divergence between RTL and `isa/sim.py`
(PC/RF/scratchpad/mask). Per engineering standard #2, NEVER edit `isa/sim.py` to make
failing RTL pass — `isa/ISA.yaml` arbitrates.
