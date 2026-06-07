// tt_um_warpone — Tiny Tapeout top wrapper for the WarpOne SIMT core.
//
// Wraps warpone_core and maps its 16-bit CSR backend onto the TT pins with a simple,
// synthesizable parallel host protocol (the pin map; see docs/INTEGRATION.md and
// DECISIONS D2.1). A 16-bit CSR value is written as two byte transfers (low then high);
// reads return one byte selected by rd_hi. The SPI→APB3 front-end (spec §7) can later
// replace this shim without touching the core; the CSR map is unchanged.
//
// Pin map:
//   ui_in[7:0]   host write-data byte (staged low byte, then high byte commits)
//   uio_in[3:0]  CSR address (0..12)
//   uio_in[4]    hi: 0 = stage low byte; 1 = commit write {ui_in, staged_low}
//   uio_in[5]    we: write strobe (qualified by ena)
//   uio_in[6]    rd_hi: 0 = uo_out is rdata[7:0]; 1 = rdata[15:8]
//   uio_in[7]    reserved (0)
//   uo_out[7:0]  CSR read-data byte
//   uio_out/oe   0 (uio used as inputs in functional mode)

`default_nettype none

module tt_um_warpone (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    wire [3:0] caddr   = uio_in[3:0];
    wire       load_hi = uio_in[4];
    wire       we_stb  = uio_in[5] & ena;
    wire       rd_hi   = uio_in[6];

    reg  [7:0] hold_lo;                       // staged low byte for 16-bit writes
    always_ff @(posedge clk) begin
        if (!rst_n)                hold_lo <= 8'd0;
        else if (we_stb & ~load_hi) hold_lo <= ui_in;
    end

    wire        core_we    = we_stb & load_hi;          // commit on the high-byte write
    wire [15:0] core_wdata = {ui_in, hold_lo};
    wire [15:0] core_rdata;

    warpone_core u_core (
        .clk      (clk),
        .rst_n    (rst_n),
        .csr_we   (core_we),
        .csr_re   (1'b0),
        .csr_addr ({1'b0, caddr}),
        .csr_wdata(core_wdata),
        .csr_rdata(core_rdata)
    );

    assign uo_out  = rd_hi ? core_rdata[15:8] : core_rdata[7:0];
    assign uio_out = 8'h00;
    assign uio_oe  = 8'h00;                    // all bidirectionals are inputs (functional mode)

    wire _unused = &{1'b0, uio_in[7]};        // reserved pin
endmodule

`default_nettype wire
