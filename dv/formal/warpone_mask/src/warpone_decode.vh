// AUTO-GENERATED from isa/ISA.yaml v1.0.0 by scripts/gen_decoder.py — DO NOT EDIT.
// Opcode constants + trap codes; single source of truth is isa/ISA.yaml.

localparam [4:0] OP_NOP    = 5'h00;
localparam [4:0] OP_HALT   = 5'h01;
localparam [4:0] OP_LDI    = 5'h02;
localparam [4:0] OP_MOV    = 5'h03;
localparam [4:0] OP_ADD    = 5'h04;
localparam [4:0] OP_SUB    = 5'h05;
localparam [4:0] OP_AND    = 5'h06;
localparam [4:0] OP_OR     = 5'h07;
localparam [4:0] OP_XOR    = 5'h08;
localparam [4:0] OP_SHL    = 5'h09;
localparam [4:0] OP_SHR    = 5'h0A;
localparam [4:0] OP_LANEID = 5'h0B;
localparam [4:0] OP_JMP    = 5'h0C;
localparam [4:0] OP_SPLIT  = 5'h0D;
localparam [4:0] OP_JOIN   = 5'h0E;
localparam [4:0] OP_LD     = 5'h0F;
localparam [4:0] OP_ST     = 5'h10;
localparam [4:0] OP_BAR    = 5'h11;
localparam [4:0] OP_MUL    = 5'h12;
localparam [4:0] OP_SETP   = 5'h13;
localparam [4:0] OP_SEL    = 5'h14;

localparam [1:0] TRAP_ILLEGAL_OPCODE   = 2'd1;
localparam [1:0] TRAP_STACK_OVERFLOW   = 2'd2;
localparam [1:0] TRAP_STACK_UNDERFLOW  = 2'd3;
