# dv/formal — SymbiYosys properties

`.sby` files + properties for: mask-stack safety (no silent over/underflow), scheduler
no-deadlock + fairness, decode completeness (every encoding executes or traps, no X),
and register write-port arbitration. Bounded proofs state their depth and why it
suffices. Lands in **Phase 4**.
