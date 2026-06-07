---
description: Run a constrained-random lockstep fuzz campaign
argument-hint: "[num_programs]"
allowed-tools: Bash(make fuzz), Bash(make:*)
---
Run a constrained-random lockstep fuzz campaign of $ARGUMENTS programs (default 10000)
via `make fuzz`. Programs must be legal-by-construction (balanced SPLIT/JOIN, bounded
loops, in-range addresses). Report pass-rate and, for any mismatch, a minimal
reproducer plus the first divergent cycle. Gate: >=10,000 programs, 0 mismatches.
Parallelize the campaign (parallelism is free).
