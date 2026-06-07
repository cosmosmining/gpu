; dot-product — sum over lanes of a[lane]*b[lane], via per-lane MUL + scratchpad reduction.
; a = lane (0,1,2,3); b = lane+2 (2,3,4,5); products = 0,3,8,15; dot = 26 in every lane.
        LANEID r0          ; a = lane
        LDI    r1, 2
        ADD    r1, r0, r1   ; b = lane + 2
        MUL    r2, r0, r1   ; p = a*b  (0,3,8,15)
        ST     r2, r0       ; scratch[lane] = p
        BAR
        LDI    r3, 0
        LD     r4, r3       ; acc = scratch[0]
        LDI    r3, 1
        LD     r5, r3
        ADD    r4, r4, r5   ; += scratch[1]
        LDI    r3, 2
        LD     r5, r3
        ADD    r4, r4, r5   ; += scratch[2]
        LDI    r3, 3
        LD     r5, r3
        ADD    r4, r4, r5   ; += scratch[3]  -> r4 = 0+3+8+15 = 26
        HALT
