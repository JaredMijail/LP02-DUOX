; Programa mínimo para las pruebas automáticas del FPU:
; el script de pruebas escribe FA, FB y OPV en memoria, ejecuta y lee FR.
.INCLUDE "../asm/macros.inc"
    FPU_INSTALL
    LOAD OPV
    INT
    HALT
.INCLUDE "../asm/fpu.asm"
.VAR OPV
