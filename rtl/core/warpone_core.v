// warpone_core — WarpOne SIMT core (P0: single warp, 4 lanes, 8-bit).
//
// Single-cycle-per-instruction datapath (one instruction issues and retires per clock
// while running), mirroring isa/sim.py::_exec_one for bit-exact lockstep. Storage is all
// flops (no SRAM macros). Decoder opcodes are generated from isa/ISA.yaml (warpone_decode.vh).
//
// Host interface: a simple synchronous CSR backend (the APB3/SPI front-end attaches here;
// see DECISIONS D2.1). The host loads I-mem, launches, polls status, and peeks register
// file / perf counters through the CSRs below.
//
// P1 (Phase 5) adds: 2nd warp + round-robin scheduler, LD/ST + banked scratchpad, BAR.
// Until then, opcodes >= LD (0x0F) decode to an illegal-instruction trap (X-free).

`default_nettype none

module warpone_core #(
    parameter LANES = 4,
    parameter REGS  = 8,
    parameter WIDTH = 8,
    parameter IMEM  = 32,
    parameter DEPTH = 4,
    parameter CW    = 16            // performance-counter width
) (
    input  wire        clk,
    input  wire        rst_n,       // synchronous, active-low
    // CSR backend (16-bit data)
    input  wire        csr_we,
    input  wire        csr_re,      // (reads are combinational; kept for symmetry)
    input  wire [4:0]  csr_addr,
    input  wire [15:0] csr_wdata,
    output reg  [15:0] csr_rdata
);
    // Generated opcode constants. P1/P2 opcodes (LD/ST/BAR/MUL/SETP/SEL) and NOP are
    // defined here but not all referenced until their phase; waive UNUSEDPARAM for the
    // generated include only (waiver scoped + logged: DECISIONS D2.2).
    /* verilator lint_off UNUSEDPARAM */
    `include "warpone_decode.vh"
    /* verilator lint_on UNUSEDPARAM */

    localparam PCW = $clog2(IMEM);       // 5 for IMEM=32

    // CSR addresses
    localparam A_ID=0, A_CTRL=1, A_STATUS=2, A_IADDR=3, A_IDATA=4,
               A_DSEL=5, A_DRD=6, A_DPC=7,
               A_RET=8, A_DIV=9, A_ACT=10, A_BANK=11, A_CYC=12;

    // ---- architectural state (single warp) -------------------------------
    reg [WIDTH-1:0] rf   [0:LANES-1][0:REGS-1];
    reg [PCW-1:0]   pc;
    reg [LANES-1:0] mask;
    reg [LANES-1:0] dstk [0:DEPTH-1];
    reg [2:0]       sp;                  // 0..DEPTH
    reg             halted, trapped;
    reg [1:0]       trapcode;
    reg [15:0]      imem [0:IMEM-1];
    reg [PCW-1:0]   imem_addr;
    reg [4:0]       dsel;
    reg             running, done, test_en;
    // performance counters
    reg [CW-1:0]    c_ret, c_div, c_act, c_bank, c_cyc;

    integer i, j;

    // ---- fetch / decode (combinational) ----------------------------------
    wire [15:0] instr = imem[pc];
    wire [4:0]  op    = instr[15:11];
    wire [2:0]  fa    = instr[10:8];
    wire [2:0]  fb    = instr[7:5];
    wire [2:0]  fc    = instr[4:2];
    wire [7:0]  imm8  = instr[7:0];
    wire [5:0]  addr6 = instr[5:0];

    // per-lane taken predicate for SPLIT
    reg  [LANES-1:0] taken;
    integer lt;
    always_comb begin
        for (lt = 0; lt < LANES; lt = lt + 1)
            taken[lt] = mask[lt] & (rf[lt][fa] != {WIDTH{1'b0}});
    end

    // popcount of the execute-time mask
    reg [2:0] popcnt;
    integer lp;
    always_comb begin
        popcnt = 3'd0;
        for (lp = 0; lp < LANES; lp = lp + 1)
            popcnt = popcnt + {2'b0, mask[lp]};
    end

    // trap decode
    wire illegal = (op > OP_JOIN);                 // P0: LD..reserved unimplemented -> trap
    wire ovf     = (op == OP_SPLIT) && (sp == DEPTH[2:0]);
    wire udf     = (op == OP_JOIN)  && (sp == 3'd0);
    wire is_trap = illegal | ovf | udf;
    wire [1:0] tcode = illegal ? TRAP_ILLEGAL_OPCODE :
                       ovf     ? TRAP_STACK_OVERFLOW : TRAP_STACK_UNDERFLOW;

    wire do_issue = running & ~halted;

    // 2-bit divergence-stack indices (push when sp<DEPTH, pop when sp>0)
    wire [1:0] push_idx = sp[1:0];          // sp in 0..3 at a valid push
    wire [1:0] pop_idx  = sp[1:0] - 2'd1;   // sp in 1..4 at a valid pop -> 0..3

    // ---- sequential: reset, CSR writes, execution ------------------------
    integer lx;
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < LANES; i = i + 1)
                for (j = 0; j < REGS; j = j + 1) rf[i][j] <= {WIDTH{1'b0}};
            for (i = 0; i < IMEM;  i = i + 1) imem[i] <= 16'd0;
            for (i = 0; i < DEPTH; i = i + 1) dstk[i] <= {LANES{1'b0}};
            pc <= {PCW{1'b0}};
            mask <= {LANES{1'b1}};
            sp <= 3'd0;
            halted <= 1'b0; trapped <= 1'b0; trapcode <= 2'd0;
            imem_addr <= {PCW{1'b0}};
            dsel <= 5'd0; running <= 1'b0; done <= 1'b0; test_en <= 1'b0;
            c_ret <= 0; c_div <= 0; c_act <= 0; c_bank <= 0; c_cyc <= 0;
        end else begin
            // -- host CSR writes ------------------------------------------
            if (csr_we) begin
                case (csr_addr)
                    A_CTRL: begin
                        if (csr_wdata[1]) begin                 // reset/clear core
                            pc <= {PCW{1'b0}}; mask <= {LANES{1'b1}}; sp <= 3'd0;
                            halted <= 1'b0; trapped <= 1'b0; trapcode <= 2'd0;
                            running <= 1'b0; done <= 1'b0;
                            c_ret <= 0; c_div <= 0; c_act <= 0; c_bank <= 0; c_cyc <= 0;
                            for (i = 0; i < LANES; i = i + 1)
                                for (j = 0; j < REGS; j = j + 1) rf[i][j] <= {WIDTH{1'b0}};
                            for (i = 0; i < DEPTH; i = i + 1) dstk[i] <= {LANES{1'b0}};
                        end
                        if (csr_wdata[0]) begin running <= 1'b1; done <= 1'b0; end  // launch
                        test_en <= csr_wdata[3];
                    end
                    A_IADDR: imem_addr <= csr_wdata[PCW-1:0];
                    A_IDATA: begin imem[imem_addr] <= csr_wdata; imem_addr <= imem_addr + 1'b1; end
                    A_DSEL:  dsel <= csr_wdata[4:0];
                    default: ;
                endcase
            end

            // -- execution (single-cycle per instruction) -----------------
            if (do_issue) begin
                c_cyc <= c_cyc + 1'b1;                      // every issue is a cycle
                for (lx = 0; lx < LANES; lx = lx + 1) begin
                    if (mask[lx]) begin
                        case (op)
                            OP_LDI:    rf[lx][fa] <= imm8;
                            OP_MOV:    rf[lx][fa] <= rf[lx][fb];
                            OP_ADD:    rf[lx][fa] <= rf[lx][fb] + rf[lx][fc];
                            OP_SUB:    rf[lx][fa] <= rf[lx][fb] - rf[lx][fc];
                            OP_AND:    rf[lx][fa] <= rf[lx][fb] & rf[lx][fc];
                            OP_OR:     rf[lx][fa] <= rf[lx][fb] | rf[lx][fc];
                            OP_XOR:    rf[lx][fa] <= rf[lx][fb] ^ rf[lx][fc];
                            OP_SHL:    rf[lx][fa] <= rf[lx][fb] << rf[lx][fc][2:0];
                            OP_SHR:    rf[lx][fa] <= rf[lx][fb] >> rf[lx][fc][2:0];
                            OP_LANEID: rf[lx][fa] <= lx[WIDTH-1:0];
                            default:   ; // control / non-RF ops
                        endcase
                    end
                end
                if (is_trap) begin
                    trapped  <= 1'b1;
                    trapcode <= tcode;
                    halted   <= 1'b1;
                    running  <= 1'b0;
                    done     <= 1'b1;
                end else begin
                    c_ret <= c_ret + 1'b1;
                    c_act <= c_act + {{(CW-3){1'b0}}, popcnt};
                    case (op)
                        OP_HALT: begin halted <= 1'b1; running <= 1'b0; done <= 1'b1; end
                        OP_JMP:  pc <= addr6[PCW-1:0];
                        OP_SPLIT: begin
                            dstk[push_idx] <= mask;
                            sp   <= sp + 1'b1;
                            mask <= mask & taken;
                            c_div <= c_div + 1'b1;
                            pc <= pc + 1'b1;
                        end
                        OP_JOIN: begin
                            sp   <= sp - 1'b1;
                            mask <= dstk[pop_idx];
                            pc <= pc + 1'b1;
                        end
                        default: pc <= pc + 1'b1;   // NOP/LDI/MOV/ALU/LANEID
                    endcase
                end
            end
        end
    end

    // ---- CSR read (combinational) ----------------------------------------
    wire [1:0] dbg_lane = dsel[4:3];
    wire [2:0] dbg_reg  = dsel[2:0];
    always_comb begin
        case (csr_addr)
            A_ID:     csr_rdata = 16'h574F;                 // "WO"
            A_CTRL:   csr_rdata = {12'b0, test_en, 2'b0, running};
            A_STATUS: csr_rdata = {6'b0, trapcode, 5'b0, trapped, done, running};
            A_IADDR:  csr_rdata = {{(16-PCW){1'b0}}, imem_addr};
            A_IDATA:  csr_rdata = imem[imem_addr];
            A_DSEL:   csr_rdata = {11'b0, dsel};
            A_DRD:    csr_rdata = {8'b0, rf[dbg_lane][dbg_reg]};
            A_DPC:    csr_rdata = {3'b0, sp, mask, {(6-PCW){1'b0}}, pc};
            A_RET:    csr_rdata = c_ret;
            A_DIV:    csr_rdata = c_div;
            A_ACT:    csr_rdata = c_act;
            A_BANK:   csr_rdata = c_bank;
            A_CYC:    csr_rdata = c_cyc;
            default:  csr_rdata = 16'h0000;
        endcase
    end

    // csr_re unused while reads are combinational (kept in the port for the bus front-end);
    // addr6[5] is unused at IMEM=32 (PCW=5) but is needed when I-mem grows to 64 (P1).
    wire _unused = &{1'b0, csr_re, addr6[5]};

endmodule

`default_nettype wire
