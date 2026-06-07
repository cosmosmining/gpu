# kernels — demo kernels

Demonstration kernels, each bit-exact vs `isa/sim.py` and with pre-registered exact
perf-counter predictions (`PREDICTIONS.md`):
- **vecadd** — element-wise vector add (lockstep lanes).
- **dot-product** — multiply + lane-reduction (divergence/reconvergence).
- **parallel max** — lane reduction with predication.

Authored once the ISA + core exist (Phase 2+); predictions frozen in Phase 7.
