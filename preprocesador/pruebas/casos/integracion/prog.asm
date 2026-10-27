#define CHAR_A 65
.INCLUDE "extra.inc"

    PUSH CHAR_A
    OUT
    PUSH CHAR_B
    OUT
    PUSH CHAR_C
    OUT
    PUTC 10
    HALT
