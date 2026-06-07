# isa/compliance — directed compliance programs + expected traces

One program per ISA feature with its golden retired-state trace (PC, RF, masks).
Authored in **Phase 1**; the compliance suite passing on `isa/sim.py` is the Phase 1
gate. These same programs seed the RTL lockstep regression in Phase 2.
