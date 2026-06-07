#!/usr/bin/env python3
"""Generate rtl/core/warpone_decode.vh from isa/ISA.yaml.

The RTL opcode constants are single-sourced from the ISA (standard #2). Run via
`make isa` (Phase 2+). DO NOT hand-edit the generated .vh.
"""
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("gen_decoder.py requires pyyaml\n")
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    isa = yaml.safe_load(open(os.path.join(ROOT, "isa", "ISA.yaml")))
    ver = isa["isa"]["version"]
    enc = isa["encoding"]
    ow = enc["opcode"]["hi"] - enc["opcode"]["lo"] + 1
    out = os.path.join(ROOT, "rtl", "core", "warpone_decode.vh")
    lines = [
        f"// AUTO-GENERATED from isa/ISA.yaml v{ver} by scripts/gen_decoder.py — DO NOT EDIT.",
        "// Opcode constants + trap codes; single source of truth is isa/ISA.yaml.",
        "",
    ]
    for mnem, spec in isa["instructions"].items():
        lines.append(f"localparam [{ow-1}:0] OP_{mnem.upper():<6} = {ow}'h{spec['opcode']:02X};")
    lines.append("")
    for tname, t in isa["traps"].items():
        lines.append(f"localparam [1:0] TRAP_{tname.upper():<16} = 2'd{t['code']};")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(isa['instructions'])} opcodes, {len(isa['traps'])} traps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
