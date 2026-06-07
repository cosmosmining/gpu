; reduce_sum — cross-lane reduction via the banked scratchpad + barrier.
; Each lane writes its value (= lane id) to scratch[lane]; after BAR, every lane reads all
; four slots and sums them, so each lane ends with sum(0..3) = 6. Exercises LD/ST, bank
; conflicts (the broadcast LDs all hit one bank), and the barrier.
        LANEID r0          ; r0 = this lane's value (= lane id)
        ST     r0, r0      ; scratch[lane] = lane     (data=r0, addr=r0)
        BAR                ; all stores visible before any load
        LDI    r1, 0
        LD     r2, r1      ; r2 = scratch[0]
        LDI    r1, 1
        LD     r3, r1
        ADD    r2, r2, r3  ; r2 += scratch[1]
        LDI    r1, 2
        LD     r3, r1
        ADD    r2, r2, r3  ; r2 += scratch[2]
        LDI    r1, 3
        LD     r3, r1
        ADD    r2, r2, r3  ; r2 += scratch[3]  -> r2 = 0+1+2+3 = 6 in every lane
        HALT
