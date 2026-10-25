; =====================================================================
;  heron.asm - Raíz cuadrada por el método de Herón de Alejandría
;  (R. Peña, "De Euclides a Java", p. 26), usando el FPU emulado.
;
;     Dado x y un y0 con y0^2 < x:   y(i+1) = 1/2 * ( y(i) + x / y(i) )
;
;  Desde y1 la sucesión decrece hacia sqrt(x). En punto flotante se detiene
;  cuando deja de decrecer (y(i+1) >= y(i)): ya no hay un double más cercano.
;  Por seguridad se limita a 60 iteraciones.
; =====================================================================
.INCLUDE "macros.inc"
.EQU V_HERON, 30

inicio:
    FPU_INSTALL
    VECTOR V_HERON, heron
    PRINTS "Metodo de Heron - raiz cuadrada con el FPU IEEE 754 emulado\n"
    PRINTS "(cada linea: iteracion, valor decimal y patron binario de 64 bits)\n"

    MOV HX, c125                  ; ejemplo del libro: x = 125, y0 = 10
    MOV HY, c10
    CALL V_HERON
    MOV HX, c2
    MOV HY, c1
    CALL V_HERON
    MOV HX, c3
    MOV HY, c1
    CALL V_HERON
    MOV HX, c05
    MOV HY, c05
    CALL V_HERON
    MOV HX, c12345
    MOV HY, c100
    CALL V_HERON
    HALT

; ---------------------------------------------------------------------
;  heron: calcula sqrt(HX) partiendo de HY. Deja el resultado en HY.
; ---------------------------------------------------------------------
heron:
    PRINTS "\nx = "
    FPRINTV HX
    PRINTS "   y0 = "
    FPRINTV HY
    NL
    SET h_i, 0
h_ciclo:
    ADDI h_i, h_i, 1
    FDIVV h_t, HX, HY             ; x / y
    FADDV h_t, h_t, HY            ; y + x / y
    FMULV h_n, h_t, cmedio        ; (y + x / y) / 2
    PRINTS "  y"
    MOV PU_X, h_i
    SET PU_W, 2
    CALL V_PRINTU
    PRINTS " = "
    FPRINTV h_n
    PRINTS "   "
    FHEXV h_n
    NL
    JLTI h_i, 2, h_sigue          ; y1 puede ser mayor que y0
    FCMPV h_c, h_n, HY
    JNEI h_c, F_MENOR, h_fin      ; ya no decrece: convergió
h_sigue:
    MOV HY, h_n
    JLTI h_i, 60, h_ciclo
h_fin:
    PRINTS "  sqrt(x) ~= "
    FPRINTV HY
    PRINTS "   comprobacion y*y = "
    FMULV h_t, HY, HY
    FPRINTV h_t
    PRINTS "   ("
    MOV PU_X, h_i
    SET PU_W, 1
    CALL V_PRINTU
    PRINTS " iteraciones)\n"
    RET

; ---------------------------------------------------------------- datos
c125:   .DOUBLE 125.0
c10:    .DOUBLE 10.0
c2:     .DOUBLE 2.0
c1:     .DOUBLE 1.0
c3:     .DOUBLE 3.0
c05:    .DOUBLE 0.5
c12345: .DOUBLE 12345.678
c100:   .DOUBLE 100.0
cmedio: .DOUBLE 0.5
.VAR HX, HY, h_i, h_t, h_n, h_c

.INCLUDE "fpu.asm"
