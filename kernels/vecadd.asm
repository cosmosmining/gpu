; vecadd — per-lane c = a + b, fully independent lanes (pure SIMT, 100% utilization).
; Inputs derived from LANEID: a = lane, b = 2*lane  =>  c = 3*lane.
        LANEID r0          ; r0 = a = lane (0,1,2,3)
        LDI    r1, 1
        SHL    r2, r0, r1   ; r2 = b = lane << 1 = 2*lane
        ADD    r3, r0, r2   ; r3 = c = a + b = 3*lane
        HALT
; result: lane l has r3 = 3*l  (0,3,6,9)
