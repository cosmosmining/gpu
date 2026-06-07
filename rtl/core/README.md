# rtl/core — WarpOne core RTL

`warpone_core` (datapath, warp scheduler, divergence mask stack, register file,
scratchpad, perf counters) plus the APB3 CSR interface.

**Empty by design in Phase 0.** Core RTL begins in **Phase 2**, after `docs/SPEC.md`
and `isa/ISA.yaml` are frozen and operator-approved (engineering standard #1). The
decoder is generated from `isa/ISA.yaml`.
