// tt_um_warpone — Tiny Tapeout top wrapper for the WarpOne SIMT core.
//
// PHASE 0 SCAFFOLD ONLY: this is a build-flow placeholder, not architectural RTL.
// Per engineering standard #1, core RTL begins in Phase 2 (after SPEC.md + the ISA
// are frozen). For now it presents the standard TT interface with safe tie-offs so
// the synthesis/lint/sim flow has a real top module to compile. The pin map
// (assignment of ui_in/uo_out/uio_* to functions) is defined in docs/INTEGRATION.md
// in Phase 1+; nothing about the microarchitecture is frozen here.

`default_nettype none

module tt_um_warpone (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // bidirectional: input path
    output wire [7:0] uio_out,  // bidirectional: output path
    output wire [7:0] uio_oe,   // bidirectional: output-enable (1 = drive)
    input  wire       ena,      // high when the design is selected
    input  wire       clk,      // single clock from the TT harness (target 50 MHz)
    input  wire       rst_n     // synchronous active-low reset
);

    // Phase 0 tie-offs (no core logic yet).
    assign uo_out  = 8'h00;
    assign uio_out = 8'h00;
    assign uio_oe  = 8'h00;     // all bidirectionals as inputs for now

    // Consume currently-unwired inputs to keep lint clean (no UNUSED warnings).
    wire _unused = &{ena, clk, rst_n, ui_in, uio_in, 1'b0};

endmodule

`default_nettype wire
