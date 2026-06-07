#!/usr/bin/env python3
"""WarpOne assembler — encoding tables derived from isa/ISA.yaml (single source of truth).

Phase 0: scaffold. Loads and structurally validates ISA.yaml and exposes the
`Assembler` surface. The real `assemble()` (text -> 16-bit machine words) is
generated from the frozen ISA in Phase 1. This file never hand-codes encodings that
contradict ISA.yaml (standard #2).
"""
import os
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("asm.py requires pyyaml (pip install pyyaml)\n")
    raise

ISA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISA.yaml")


def load_isa(path=ISA_PATH):
    """Load the ISA single-source-of-truth as a dict."""
    with open(path) as f:
        return yaml.safe_load(f)


class Assembler:
    """Assembles WarpOne text programs into 16-bit machine words.

    Phase 0 holds only the ISA handle and the (currently empty) instruction table.
    """

    def __init__(self, isa=None):
        self.isa = isa or load_isa()
        self.instructions = self.isa.get("instructions") or {}
        self.width = self.isa["datapath"]["instr_width_bits"]

    def assemble(self, text):  # noqa: D401
        """Assemble a program string into a list of machine words."""
        raise NotImplementedError(
            "assemble() is generated from the frozen ISA in Phase 1")


def main():
    isa = load_isa()
    meta = isa["isa"]
    print(f"WarpOne assembler — ISA '{meta['name']}' v{meta['version']} "
          f"(frozen={meta['frozen']}); {len(isa.get('instructions') or {})} instr defined")
    return 0


if __name__ == "__main__":
    sys.exit(main())
