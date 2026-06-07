; parallel-max — max over lanes, via per-lane SETP/SEL reduction over the scratchpad.
; v = lane XOR 2 -> (2,3,0,1); max = 3 in every lane.
        LANEID r0
        LDI    r1, 2
        XOR    r2, r0, r1   ; v = lane ^ 2
        ST     r2, r0       ; scratch[lane] = v
        BAR
        LDI    r3, 0
        LD     r4, r3       ; acc = scratch[0]
        LDI    r3, 1
        LD     r5, r3       ; cand = scratch[1]
        SETP   r6, r4, r5   ; r6 = (acc < cand)
        SEL    r4, r6, r5   ; acc = r6 ? cand : acc
        LDI    r3, 2
        LD     r5, r3
        SETP   r6, r4, r5
        SEL    r4, r6, r5
        LDI    r3, 3
        LD     r5, r3
        SETP   r6, r4, r5
        SEL    r4, r6, r5   ; r4 = max(v) = 3
        HALT
