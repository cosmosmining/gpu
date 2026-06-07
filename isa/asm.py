#!/usr/bin/env python3
"""WarpOne assembler — encodings derived from isa/ISA.yaml (single source of truth).

Two-pass: collect labels, then encode. Syntax:
    ; comment            (also // )
    label:               (own line or inline)
        LDI  r0, 5
        ADD  r1, r0, r0
        SPLIT r1
        JMP  label
        HALT
Registers r0..r7. Immediates: decimal, 0xHEX, or negative (two's complement into imm8).
addr6 operands accept a label or a number. Emits a list of 16-bit ints.
"""
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("asm.py requires pyyaml (pip install pyyaml)\n")
    raise

ISA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISA.yaml")


def load_isa(path=ISA_PATH):
    with open(path) as f:
        return yaml.safe_load(f)


class AsmError(Exception):
    pass


def _parse_int(tok):
    tok = tok.strip()
    try:
        if tok.lower().startswith("0x") or tok.lower().startswith("-0x"):
            return int(tok, 16)
        return int(tok, 10)
    except ValueError as e:
        raise AsmError(f"bad integer literal: {tok!r}") from e


def _reg(tok):
    m = re.fullmatch(r"[rR]([0-7])", tok.strip())
    if not m:
        raise AsmError(f"expected register r0..r7, got {tok!r}")
    return int(m.group(1))


class Assembler:
    def __init__(self, isa=None):
        self.isa = isa or load_isa()
        self.enc = self.isa["encoding"]
        self.formats = self.enc["formats"]
        self.instr = self.isa["instructions"]
        self.width = self.isa["datapath"]["instr_width_bits"]
        self.regs = self.isa["datapath"]["regs_per_lane"]
        # mnemonic -> spec (upper-cased keys)
        self.by_mnem = {k.upper(): v for k, v in self.instr.items()}

    # -- field packing -------------------------------------------------------
    def _place(self, field_name, value):
        f = self.enc["fields"][field_name]
        hi, lo = f["hi"], f["lo"]
        width = hi - lo + 1
        if value < 0:
            value &= (1 << width) - 1
        if value >= (1 << width):
            raise AsmError(f"value {value} does not fit field {field_name} ({width} bits)")
        return value << lo

    def _opcode_bits(self, opcode):
        return self._place_opcode(opcode)

    def _place_opcode(self, opcode):
        o = self.enc["opcode"]
        return (opcode & ((1 << (o["hi"] - o["lo"] + 1)) - 1)) << o["lo"]

    # -- encode one instruction ---------------------------------------------
    def encode(self, mnem, operands, labels=None, pc=None):
        mnem = mnem.upper()
        if mnem not in self.by_mnem:
            raise AsmError(f"unknown instruction {mnem!r}")
        spec = self.by_mnem[mnem]
        fmt = self.formats[spec["format"]]
        opspecs = fmt["operands"]
        if len(operands) != len(opspecs):
            raise AsmError(f"{mnem}: expected {len(opspecs)} operand(s), got {len(operands)}")
        word = self._place_opcode(spec["opcode"])
        for tok, ospec in zip(operands, opspecs):
            kind = ospec["kind"]
            if kind == "reg":
                val = _reg(tok)
            elif kind == "imm8":
                val = _parse_int(tok) & 0xFF
            elif kind == "addr6":
                tok = tok.strip()
                if labels is not None and tok in labels:
                    val = labels[tok]
                else:
                    val = _parse_int(tok)
                if not (0 <= val < 64):
                    raise AsmError(f"{mnem}: addr {val} out of range 0..63")
            else:
                raise AsmError(f"unknown operand kind {kind!r}")
            word |= self._place(ospec["field"], val)
        return word & ((1 << self.width) - 1)

    # -- assemble a whole program -------------------------------------------
    def assemble(self, text):
        # pass 1: strip comments, split inline labels, collect label -> addr
        lines = []
        for raw in text.splitlines():
            line = re.sub(r"(;|//).*$", "", raw).strip()
            if not line:
                continue
            # peel leading "label:" possibly followed by an instruction
            while ":" in line.split()[0] if line.split() else False:
                head = line.split(None, 1)
                lab = head[0]
                if not lab.endswith(":"):
                    break
                lines.append(("label", lab[:-1]))
                line = head[1].strip() if len(head) > 1 else ""
                if not line:
                    break
            if not line:
                continue
            parts = line.split(None, 1)
            mnem = parts[0]
            ops = []
            if len(parts) > 1:
                ops = [o.strip() for o in parts[1].split(",")]
            lines.append(("instr", (mnem, ops)))

        labels = {}
        pc = 0
        for kind, payload in lines:
            if kind == "label":
                if payload in labels:
                    raise AsmError(f"duplicate label {payload!r}")
                labels[payload] = pc
            else:
                pc += 1

        # pass 2: encode
        words = []
        pc = 0
        for kind, payload in lines:
            if kind == "label":
                continue
            mnem, ops = payload
            words.append(self.encode(mnem, ops, labels=labels, pc=pc))
            pc += 1
        cap = self.isa["datapath"]["imem_entries"]
        if len(words) > cap:
            raise AsmError(f"program has {len(words)} instructions, I-mem holds {cap}")
        return words

    def assemble_file(self, path):
        with open(path) as f:
            return self.assemble(f.read())


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    asm = Assembler()
    if argv:
        words = asm.assemble_file(argv[0])
        for i, w in enumerate(words):
            print(f"{i:02d}: {w:04x}  {w:016b}")
        return 0
    meta = asm.isa["isa"]
    print(f"WarpOne assembler — ISA '{meta['name']}' v{meta['version']} "
          f"(frozen={meta['frozen']}); {len(asm.instr)} instructions encoded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
