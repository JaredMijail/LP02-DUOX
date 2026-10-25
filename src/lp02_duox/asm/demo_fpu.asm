; =====================================================================
;  demo_fpu.asm - Demostración del FPU IEEE 754 emulado:
;  formato (signo, exponente, fracción), las cuatro operaciones,
;  conversiones y casos especiales (cero con signo, subnormales,
;  infinitos, NaN y redondeo al par).
; =====================================================================
.INCLUDE "macros.inc"
.EQU V_CAMPOS, 30

inicio:
    FPU_INSTALL
    VECTOR V_CAMPOS, campos
    VECTOR V_MUESTRA, muestra
    PRINTS "== 1. Formato binary64: s | e (11 bits, sesgo 1023) | f (52 bits) ==\n"
    MOV DX, v1
    CALL V_CAMPOS
    MOV DX, vm1
    CALL V_CAMPOS
    MOV DX, v01
    CALL V_CAMPOS
    MOV DX, v125
    CALL V_CAMPOS
    MOV DX, vminsub
    CALL V_CAMPOS
    MOV DX, vmax
    CALL V_CAMPOS

    PRINTS "\n== 2. Operaciones ==\n"
    PRINTS "0.1 + 0.2       = "
    FADDV DR, v01, v02
    CALL V_MUESTRA
    PRINTS "0.3             = "
    MOV DR, v03
    CALL V_MUESTRA
    PRINTS "1 / 3           = "
    FDIVV DR, v1, v3
    CALL V_MUESTRA
    PRINTS "125 - 0.1       = "
    FSUBV DR, v125, v01
    CALL V_MUESTRA
    PRINTS "1.5 * -2.25     = "
    FMULV DR, v15, vm225
    CALL V_MUESTRA

    PRINTS "\n== 3. Redondeo al par mas cercano ==\n"
    PRINTS "1 + 2^-53       = "
    FADDV DR, v1, v2m53
    CALL V_MUESTRA
    PRINTS "(1+2^-52)+2^-53 = "
    FADDV DR, v1u, v2m53
    CALL V_MUESTRA

    PRINTS "\n== 4. Casos especiales ==\n"
    PRINTS "1e308 * 10      = "
    FMULV DR, v1e308, v10
    CALL V_MUESTRA
    PRINTS "-1 / 0          = "
    FDIVV DR, vm1, vcero
    CALL V_MUESTRA
    PRINTS "0 / 0           = "
    FDIVV DR, vcero, vcero
    CALL V_MUESTRA
    PRINTS "inf - inf       = "
    FMULV DT, v1e308, v10
    FSUBV DR, DT, DT
    CALL V_MUESTRA
    PRINTS "-1 * 0          = "
    FMULV DR, vm1, vcero
    CALL V_MUESTRA
    PRINTS "2^-1074 / 2     = "
    FDIVV DR, vminsub, v2
    CALL V_MUESTRA
    PRINTS "2^-1022 / 4     = "
    FDIVV DR, vminnor, v4
    CALL V_MUESTRA

    PRINTS "\n== 5. Conversiones ==\n"
    PRINTS "double(-7)      = "
    SET DT, UNOS64-6
    I2FV DR, DT
    CALL V_MUESTRA
    PRINTS "double(2^53+1)  = "
    SET DT, (1<<53)+1
    I2FV DR, DT
    CALL V_MUESTRA
    PRINTS "int(125 - 0.1)  = "
    FSUBV DT, v125, v01
    F2IV DR, DT
    IPRINTV DR
    NL
    PRINTS "\n== 6. Comparaciones (0 =, 1 <, 2 >, 3 sin orden) ==\n"
    PRINTS "cmp(0.1+0.2, 0.3) = "
    FADDV DT, v01, v02
    FCMPV DR, DT, v03
    IPRINTV DR
    PRINTS "   cmp(-0, +0) = "
    FCMPV DR, vmcero, vcero
    IPRINTV DR
    PRINTS "   cmp(NaN, 1) = "
    FDIVV DT, vcero, vcero
    FCMPV DR, DT, v1
    IPRINTV DR
    NL
    HALT

; --- muestra DR en decimal y hexadecimal
.EQU V_MUESTRA, 31
muestra:
    FPRINTV DR
    PRINTS "   ["
    FHEXV DR
    PRINTS "]\n"
    RET

; --- imprime los campos de DX
campos:
    FHEXV DX
    PRINTS "  s="
    SHRI DT, DX, 63
    IPRINTV DT
    PRINTS " e="
    SHRI DT, DX, 52
    LOWI DT, DT, 11
    IPRINTV DT
    PRINTS " f="
    LOWI DT, DX, 52
    FHEXV DT
    PRINTS "  valor="
    FPRINTV DX
    NL
    RET

v1:      .DOUBLE 1.0
vm1:     .DOUBLE -1.0
v01:     .DOUBLE 0.1
v02:     .DOUBLE 0.2
v03:     .DOUBLE 0.3
v125:    .DOUBLE 125.0
v15:     .DOUBLE 1.5
vm225:   .DOUBLE -2.25
v2:      .DOUBLE 2.0
v3:      .DOUBLE 3.0
v4:      .DOUBLE 4.0
v10:     .DOUBLE 10.0
v1e308:  .DOUBLE 1e308
v2m53:   .DOUBLE 1.1102230246251565e-16
v1u:     .DOUBLE 1.0000000000000002
vcero:   .WORD 0
vmcero:  .WORD 1<<63
vminsub: .WORD 1
vminnor: .WORD 1<<52
vmax:    .WORD 0x7FEFFFFFFFFFFFFF
.VAR DX, DR, DT

.INCLUDE "fpu.asm"
