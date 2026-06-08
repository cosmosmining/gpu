// warpone_core — WarpOne SIMT core (P1: 2 warps, 4 lanes, 8-bit).
//
// Single-issue: one instruction of one warp retires per issue-cycle, mirroring
// isa/sim.py for bit-exact lockstep. Storage is all flops (no SRAM macros). Decoder
// opcodes are generated from isa/ISA.yaml (warpone_decode.vh).
//
// P1 adds over P0: a 2nd hardware warp + round-robin scheduler (skips halted/barriered),
// a banked scratchpad (4 banks x 16 x 8b, shared) with LD/ST, bank-conflict serialization
// + counter and low-lane-wins store semantics, and the BAR barrier.
// MUL/SETP/SEL (P2) and reserved opcodes still trap (illegal) — Phase 7.
//
// Scheduler/accounting match the simulator: the perf "cycles" counter counts ISSUES only;
// a barrier-release is its own clock (retires the barriered warps but is not an issue).

`default_nettype none

module warpone_core #(
    parameter NWARPS = 2,
    parameter LANES  = 4,
    parameter REGS   = 8,
    parameter WIDTH  = 8,
    parameter IMEM   = 32,
    parameter DEPTH  = 4,
    parameter SCRATCH = 64,            // 4 banks x 16
    parameter CW     = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        csr_we,
    input  wire        csr_re,
    input  wire [4:0]  csr_addr,
    input  wire [15:0] csr_wdata,
    output reg  [15:0] csr_rdata
);
    /* verilator lint_off UNUSEDPARAM */
    `include "warpone_decode.vh"
    /* verilator lint_on UNUSEDPARAM */

    localparam PCW  = $clog2(IMEM);    // 5 for IMEM=32
    localparam SAW  = $clog2(SCRATCH); // 6 for 64

    localparam A_ID=0, A_CTRL=1, A_STATUS=2, A_IADDR=3, A_IDATA=4,
               A_DSEL=5, A_DRD=6, A_DPC=7,
               A_RET=8, A_DIV=9, A_ACT=10, A_BANK=11, A_CYC=12, A_WSTAT=13, A_SCR=14;

    // ---- architectural state ---------------------------------------------
    reg [WIDTH-1:0] rf   [0:NWARPS-1][0:LANES-1][0:REGS-1];
    reg [PCW-1:0]   pc   [0:NWARPS-1];
    reg [LANES-1:0] mask [0:NWARPS-1];
    reg [LANES-1:0] dstk [0:NWARPS-1][0:DEPTH-1];
    reg [2:0]       sp   [0:NWARPS-1];
    reg             halted   [0:NWARPS-1];
    reg             barriered[0:NWARPS-1];
    reg             trapped  [0:NWARPS-1];
    reg [1:0]       trapcode [0:NWARPS-1];
    reg [WIDTH-1:0] scratch  [0:SCRATCH-1];
    reg [15:0]      imem [0:IMEM-1];
    reg [PCW-1:0]   imem_addr;
    reg [5:0]       dsel;                          // {warp, lane[1:0], reg[2:0]}
    reg             running, done, test_en;
    reg [CW-1:0]    c_ret, c_div, c_act, c_bank, c_cyc;
    reg             cur;                           // round-robin pointer (NWARPS=2 -> 1 bit)
    // iterative-shared multiplier sequencer (one 8x8 MUL time-multiplexed over LANES cycles)
    reg             mul_busy;
    reg [1:0]       mul_lane;
    reg             mul_warp;

    integer i, j, k;

    // ---- scheduler (combinational) ---------------------------------------
    wire run0 = !halted[0] & !barriered[0];
    wire run1 = !halted[1] & !barriered[1];
    wire any_nonhalted = !halted[0] | !halted[1];
    // release when every non-halted warp is barriered (and >=1 non-halted exists)
    wire bar_release = any_nonhalted & (halted[0]|barriered[0]) & (halted[1]|barriered[1]);
    wire iw_valid = run0 | run1;
    wire sched_iw = cur ? (run1 ? 1'b1 : 1'b0)    // scan from cur (NWARPS=2)
                        : (run0 ? 1'b0 : 1'b1);
    // during an in-flight MUL the issuing-warp index is held to the multiplying warp
    wire iw = mul_busy ? mul_warp : sched_iw;
    wire [1:0] last_lane = LANES[1:0] - 2'd1;

    // ---- fetch / decode for the issuing warp -----------------------------
`ifdef FORMAL
    (* anyseq *) wire [15:0] instr;               // free stream (D4.2)
`else
    wire [15:0] instr = imem[pc[iw]];
`endif
    wire [4:0]  op    = instr[15:11];
    wire [2:0]  fa    = instr[10:8];
    wire [2:0]  fb    = instr[7:5];
    wire [2:0]  fc    = instr[4:2];
    wire [7:0]  imm8  = instr[7:0];
    wire [5:0]  addr6 = instr[5:0];

`ifdef FORMAL
    (* anyseq *) wire [LANES-1:0] taken;        // free predicate: prunes RF from the proof
`else
    reg [LANES-1:0] taken;
    integer lt;
    always_comb begin
        for (lt = 0; lt < LANES; lt = lt + 1)
            taken[lt] = mask[iw][lt] & (rf[iw][lt][fa] != {WIDTH{1'b0}});
    end
`endif

    reg [2:0] popcnt;
    integer lp;
    always_comb begin
        popcnt = 3'd0;
        for (lp = 0; lp < LANES; lp = lp + 1)
            popcnt = popcnt + {2'b0, mask[iw][lp]};
    end

    // ---- memory addressing (LD/ST) ---------------------------------------
    reg [SAW-1:0]   maddr [0:LANES-1];   // scratch byte address per lane (field b)
    reg [1:0]       mbank [0:LANES-1];   // bank = addr[1:0]
    reg [WIDTH-1:0] mword;
`ifdef FORMAL
    // Free addresses for formal: the write-port "winners are distinct" property holds for
    // ANY addresses, so this prunes the RF from the proof's COI (D4.2).
    (* anyseq *) wire [LANES*SAW-1:0] f_maddr;
    integer lmf;
    always_comb begin
        for (lmf = 0; lmf < LANES; lmf = lmf + 1) begin
            maddr[lmf] = f_maddr[lmf*SAW +: SAW];
            mbank[lmf] = f_maddr[lmf*SAW +: 2];
        end
    end
`else
    // (iverilog can't part-select an array word inside always_*, so copy to a scalar)
    integer lm;
    always_comb begin
        mword = {WIDTH{1'b0}};
        for (lm = 0; lm < LANES; lm = lm + 1) begin
            mword     = rf[iw][lm][fb];
            maddr[lm] = mword[SAW-1:0];
            mbank[lm] = mword[1:0];
        end
    end
`endif
    // bank-conflict count = active lanes - distinct banks touched
    reg [3:0] bank_seen;
    reg [2:0] distinct_banks;
    integer lb;
    always_comb begin
        bank_seen = 4'b0;
        for (lb = 0; lb < LANES; lb = lb + 1)
            if (mask[iw][lb]) bank_seen[mbank[lb]] = 1'b1;
        distinct_banks = {2'b0, bank_seen[0]} + {2'b0, bank_seen[1]}
                       + {2'b0, bank_seen[2]} + {2'b0, bank_seen[3]};
    end
    wire [2:0] conflicts = popcnt - distinct_banks;     // popcnt = active lane count here
    // store low-lane-wins: lane lx writes iff no lower active lane has the same address
    reg [LANES-1:0] st_win;
    integer si, sj;
    always_comb begin
        for (si = 0; si < LANES; si = si + 1) begin
            st_win[si] = mask[iw][si];
            for (sj = 0; sj < LANES; sj = sj + 1)
                if (sj < si && mask[iw][sj] && (maddr[sj] == maddr[si]))
                    st_win[si] = 1'b0;
        end
    end

    // ---- trap decode -----------------------------------------------------
    wire illegal = (op > OP_SEL);                  // P2 live; only 0x15..0x1F reserved -> trap
    wire ovf     = (op == OP_SPLIT) && (sp[iw] == DEPTH[2:0]);
    wire udf     = (op == OP_JOIN)  && (sp[iw] == 3'd0);
    wire is_trap = illegal | ovf | udf;
    wire [1:0] tcode = illegal ? TRAP_ILLEGAL_OPCODE :
                       ovf     ? TRAP_STACK_OVERFLOW : TRAP_STACK_UNDERFLOW;

    wire [1:0] push_idx = sp[iw][1:0];
    wire [1:0] pop_idx  = sp[iw][1:0] - 2'd1;
    wire do_issue = running & ~bar_release & iw_valid;

    // One shared 8x8 multiplier, time-multiplexed across lanes: lane 0 on the issue cycle,
    // lanes 1..LANES-1 on the following mul_busy cycles. mul_sel picks the current lane.
    wire [1:0]       mul_sel  = mul_busy ? mul_lane : 2'd0;
    wire [WIDTH-1:0] mul_prod = rf[iw][mul_sel][fb] * rf[iw][mul_sel][fc];

    // popcount of a 4-lane mask (barrier-release accounting)
    function automatic [2:0] popc(input logic [LANES-1:0] m);
        popc = {2'b0, m[0]} + {2'b0, m[1]} + {2'b0, m[2]} + {2'b0, m[3]};
    endfunction

    // barrier-release set (NWARPS=2): the non-halted barriered warps to retire together.
    // Counts are accumulated as single adds (a per-warp c_ret<=c_ret+1 loop would lose
    // increments under nonblocking last-write-wins).
    wire rel0 = ~halted[0] & barriered[0];
    wire rel1 = ~halted[1] & barriered[1];
    wire [CW-1:0] num_rel = {{(CW-1){1'b0}}, rel0} + {{(CW-1){1'b0}}, rel1};
    wire [CW-1:0] act_rel = (rel0 ? {{(CW-3){1'b0}}, popc(mask[0])} : {CW{1'b0}})
                          + (rel1 ? {{(CW-3){1'b0}}, popc(mask[1])} : {CW{1'b0}});

    // ---- sequential ------------------------------------------------------
    integer lx;
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < NWARPS; i = i + 1) begin
                for (j = 0; j < LANES; j = j + 1)
                    for (k = 0; k < REGS; k = k + 1) rf[i][j][k] <= {WIDTH{1'b0}};
                for (j = 0; j < DEPTH; j = j + 1) dstk[i][j] <= {LANES{1'b0}};
                pc[i] <= {PCW{1'b0}}; mask[i] <= {LANES{1'b1}}; sp[i] <= 3'd0;
                halted[i] <= 1'b0; barriered[i] <= 1'b0; trapped[i] <= 1'b0; trapcode[i] <= 2'd0;
            end
            for (i = 0; i < IMEM;    i = i + 1) imem[i]    <= 16'd0;
            for (i = 0; i < SCRATCH; i = i + 1) scratch[i] <= {WIDTH{1'b0}};
            imem_addr <= {PCW{1'b0}}; dsel <= 6'd0;
            running <= 1'b0; done <= 1'b0; test_en <= 1'b0; cur <= 1'b0;
            mul_busy <= 1'b0; mul_lane <= 2'd0; mul_warp <= 1'b0;
            c_ret <= 0; c_div <= 0; c_act <= 0; c_bank <= 0; c_cyc <= 0;
        end else begin
            // -- host CSR writes --
            if (csr_we) begin
                case (csr_addr)
                    A_CTRL: begin
                        if (csr_wdata[1]) begin                     // reset/clear core
                            for (i = 0; i < NWARPS; i = i + 1) begin
                                for (j = 0; j < LANES; j = j + 1)
                                    for (k = 0; k < REGS; k = k + 1) rf[i][j][k] <= {WIDTH{1'b0}};
                                for (j = 0; j < DEPTH; j = j + 1) dstk[i][j] <= {LANES{1'b0}};
                                pc[i] <= {PCW{1'b0}}; mask[i] <= {LANES{1'b1}}; sp[i] <= 3'd0;
                                halted[i] <= 1'b0; barriered[i] <= 1'b0;
                                trapped[i] <= 1'b0; trapcode[i] <= 2'd0;
                            end
                            for (i = 0; i < SCRATCH; i = i + 1) scratch[i] <= {WIDTH{1'b0}};
                            running <= 1'b0; done <= 1'b0; cur <= 1'b0;
                            mul_busy <= 1'b0; mul_lane <= 2'd0; mul_warp <= 1'b0;
                            c_ret <= 0; c_div <= 0; c_act <= 0; c_bank <= 0; c_cyc <= 0;
                        end
                        if (csr_wdata[0]) begin running <= 1'b1; done <= 1'b0; end  // launch
                        test_en <= csr_wdata[3];
                    end
                    A_IADDR: imem_addr <= csr_wdata[PCW-1:0];
                    A_IDATA: begin imem[imem_addr] <= csr_wdata; imem_addr <= imem_addr + 1'b1; end
                    A_DSEL:  dsel <= csr_wdata[5:0];
                    default: ;
                endcase
            end

            // -- scheduler step --
            if (running) begin
                if (mul_busy) begin
                    // iterative-shared MUL: write one lane's product per cycle; finish on the
                    // last lane (retire once, advance pc + round-robin). One multiplier total.
                    c_cyc <= c_cyc + 1'b1;
`ifndef FORMAL
                    if (mask[iw][mul_lane]) rf[iw][mul_lane][fa] <= mul_prod;
`endif
                    if (mul_lane == last_lane) begin
                        mul_busy <= 1'b0;
                        c_ret <= c_ret + 1'b1;
                        c_act <= c_act + {{(CW-3){1'b0}}, popcnt};
                        pc[iw] <= pc[iw] + 1'b1;
                        cur <= ~iw;
                    end else begin
                        mul_lane <= mul_lane + 1'b1;
                    end
                end else if (bar_release) begin
                    // release clock: retire all non-halted barriered warps (not an issue)
                    if (rel0) begin barriered[0] <= 1'b0; pc[0] <= pc[0] + 1'b1; end
                    if (rel1) begin barriered[1] <= 1'b0; pc[1] <= pc[1] + 1'b1; end
                    c_ret <= c_ret + num_rel;
                    c_act <= c_act + act_rel;
                end else if (iw_valid) begin
                    c_cyc <= c_cyc + 1'b1;                     // an issue
                    if ((op == OP_MUL) && !is_trap) begin
                        // start the shared multiplier: lane 0 now, lanes 1..LANES-1 follow;
                        // retire / pc-advance / round-robin happen when the sequencer ends.
`ifndef FORMAL
                        if (mask[iw][0]) rf[iw][0][fa] <= mul_prod;   // mul_sel=0 while !mul_busy
`endif
                        mul_busy <= 1'b1;
                        mul_lane <= 2'd1;
                        mul_warp <= iw;
                    end else begin
`ifndef FORMAL
                        // per-lane register / memory writes (data path). Excluded under FORMAL
                        // so RF/scratch prune from the proof COI; proven properties are
                        // data-independent.
                        for (lx = 0; lx < LANES; lx = lx + 1) begin
                            if (mask[iw][lx]) begin
                                case (op)
                                    OP_LDI:    rf[iw][lx][fa] <= imm8;
                                    OP_MOV:    rf[iw][lx][fa] <= rf[iw][lx][fb];
                                    OP_ADD:    rf[iw][lx][fa] <= rf[iw][lx][fb] + rf[iw][lx][fc];
                                    OP_SUB:    rf[iw][lx][fa] <= rf[iw][lx][fb] - rf[iw][lx][fc];
                                    OP_AND:    rf[iw][lx][fa] <= rf[iw][lx][fb] & rf[iw][lx][fc];
                                    OP_OR:     rf[iw][lx][fa] <= rf[iw][lx][fb] | rf[iw][lx][fc];
                                    OP_XOR:    rf[iw][lx][fa] <= rf[iw][lx][fb] ^ rf[iw][lx][fc];
                                    OP_SHL:    rf[iw][lx][fa] <=
                                                   rf[iw][lx][fb] << rf[iw][lx][fc][2:0];
                                    OP_SHR:    rf[iw][lx][fa] <=
                                                   rf[iw][lx][fb] >> rf[iw][lx][fc][2:0];
                                    OP_LANEID: rf[iw][lx][fa] <= lx[WIDTH-1:0];
                                    OP_LD:     rf[iw][lx][fa] <= scratch[maddr[lx]];
                                    OP_SETP:   rf[iw][lx][fa] <=
                                                   (rf[iw][lx][fb] < rf[iw][lx][fc]) ? 8'd1 : 8'd0;
                                    OP_SEL:    rf[iw][lx][fa] <=
                                                   (rf[iw][lx][fb] != 8'd0) ? rf[iw][lx][fc]
                                                                            : rf[iw][lx][fa];
                                    default:   ; // ST below; control ops no RF write
                                endcase
                            end
                        end
                        if (op == OP_ST) begin
                            for (lx = 0; lx < LANES; lx = lx + 1)
                                if (st_win[lx]) scratch[maddr[lx]] <= rf[iw][lx][fa];
                        end
`endif
                        // control + counters + mask stack (for warp iw)
                        if (is_trap) begin
                            trapped[iw]  <= 1'b1;
                            trapcode[iw] <= tcode;
                            halted[iw]   <= 1'b1;
                        end else if (op == OP_BAR) begin
                            barriered[iw] <= 1'b1;             // wait; retire happens at release
                        end else begin
                            c_ret <= c_ret + 1'b1;
                            c_act <= c_act + {{(CW-3){1'b0}}, popcnt};
                            if (op == OP_LD || op == OP_ST)
                                c_bank <= c_bank + {{(CW-3){1'b0}}, conflicts};
                            case (op)
                                OP_HALT: halted[iw] <= 1'b1;
                                OP_JMP:  pc[iw] <= addr6[PCW-1:0];
                                OP_SPLIT: begin
                                    dstk[iw][push_idx] <= mask[iw];
                                    sp[iw]   <= sp[iw] + 1'b1;
                                    mask[iw] <= mask[iw] & taken;
                                    c_div    <= c_div + 1'b1;
                                    pc[iw]   <= pc[iw] + 1'b1;
                                end
                                OP_JOIN: begin
                                    sp[iw]   <= sp[iw] - 1'b1;
                                    mask[iw] <= dstk[iw][pop_idx];
                                    pc[iw]   <= pc[iw] + 1'b1;
                                end
                                default: pc[iw] <= pc[iw] + 1'b1; // NOP/LDI/MOV/ALU/LANEID/LD/ST
                            endcase
                        end
                        cur <= ~iw;                            // round-robin advance
                    end
                end else begin
                    running <= 1'b0; done <= 1'b1;             // all warps halted
                end
            end
        end
    end

    // ---- CSR read (combinational) ----------------------------------------
    wire       dbg_w    = dsel[5];
    wire [1:0] dbg_lane = dsel[4:3];
    wire [2:0] dbg_reg  = dsel[2:0];
    always_comb begin
`ifdef FORMAL
        csr_rdata = 16'b0;                          // decouple outputs for COI (D4.2)
`else
        case (csr_addr)
            A_ID:     csr_rdata = 16'h574F;
            A_CTRL:   csr_rdata = {12'b0, test_en, 2'b0, running};
            A_STATUS: csr_rdata = {13'b0, (trapped[0]|trapped[1]), done, running};
            A_IADDR:  csr_rdata = {{(16-PCW){1'b0}}, imem_addr};
            A_IDATA:  csr_rdata = imem[imem_addr];
            A_DSEL:   csr_rdata = {10'b0, dsel};
            A_DRD:    csr_rdata = {8'b0, rf[dbg_w][dbg_lane][dbg_reg]};
            A_DPC:    csr_rdata = {3'b0, sp[dbg_w], mask[dbg_w], {(6-PCW){1'b0}}, pc[dbg_w]};
            A_WSTAT:  csr_rdata = {11'b0, barriered[dbg_w], trapped[dbg_w],
                                   trapcode[dbg_w], halted[dbg_w]};
            A_SCR:    csr_rdata = {8'b0, scratch[dsel[SAW-1:0]]};   // scratch peek (dsel=addr)
            A_RET:    csr_rdata = c_ret;
            A_DIV:    csr_rdata = c_div;
            A_ACT:    csr_rdata = c_act;
            A_BANK:   csr_rdata = c_bank;
            A_CYC:    csr_rdata = c_cyc;
            default:  csr_rdata = 16'h0000;
        endcase
`endif
    end

    wire _unused = &{1'b0, csr_re, addr6[5], do_issue, mword[7:6]};

`ifdef FORMAL
    // ---- Phase 5 formal: per-warp mask-stack safety + scheduler progress ----
    always_comb if ($initstate) assume (!rst_n);   // reset in initial state -> defines regs

    genvar w;
    generate
        for (w = 0; w < NWARPS; w = w + 1) begin : g_warp
            always_ff @(posedge clk)
                if (rst_n) assert (sp[w] <= DEPTH[2:0]);    // (A) no mask-stack overflow
        end
    endgenerate

    // (scheduler no-deadlock) while running with a non-halted warp present, the core makes
    // progress every cycle: it issues an instruction or releases a barrier — it never
    // silently stalls with work pending. Combinational (no 16-bit-counter $past, which the
    // local z3 chokes on).
    wire prog = do_issue | bar_release | mul_busy;
    always_ff @(posedge clk)
        if (rst_n && running && any_nonhalted) assert (prog);
    // NOTE: register/scratch write-port arbitration (store low-lane-wins => at most one
    // write per byte) is a combinational invariant verified dynamically by the 10k-program
    // 2-warp fuzz with bit-exact scratchpad comparison (a double-write would mismatch).
`endif

endmodule

`default_nettype wire
