---
description: Run one program on RTL + simulator and diff retired state
argument-hint: "<program.asm>"
---
Assemble `$ARGUMENTS`, run it on both the RTL (cocotb bench) and `isa/sim.py`, and diff
retired-instruction state: PC trace, register file, scratchpad, divergence masks.
Report the first divergence (cycle, field, expected vs actual). `isa/ISA.yaml`
arbitrates; never edit the simulator to make RTL pass (engineering standard #2).
