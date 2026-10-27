; =====================================================================
;  brun.asm - Estimación de la constante de Brun con el FPU emulado
;
;     B2 = (1/3 + 1/5) + (1/5 + 1/7) + (1/11 + 1/13) + (1/17 + 1/19) + ...
;
;  suma de los inversos de los primos gemelos (p, p+2). Brun (1919) probó
;  que la serie converge, pero lo hace con muchísima lentitud: la cola
;  después de N vale aproximadamente 4*C2/ln N (Hardy-Littlewood), con
;  C2 = 0.6601618158... (constante de los primos gemelos). Por eso el
;  programa imprime, para N = 10^2, 10^3, ..., NMAX:
;
;     B2(N)                 suma parcial de los pares con p+2 <= N
;     B2(N) + 4*C2 / ln N   estimación corregida
;
;  Todo par de primos gemelos salvo (3,5) tiene la forma (6k-1, 6k+1), así
;  que solo se prueban esos candidatos (primalidad por división de prueba
;  con divisores 6j-1 y 6j+1, usando las instrucciones enteras DIV/MOD).
;  ln N se calcula con el FPU: N = m*2^k, ln N = k ln2 + 2*atanh((m-1)/(m+1)).
; =====================================================================
.INCLUDE "macros.inc"
.EQU NMAX, 100000             ; potencia de 10; 10^6 tarda unos 20 min en el emulador
.EQU V_PRIMO, 30
.EQU V_LN, 31

inicio:
    FPU_INSTALL
    VECTOR V_PRIMO, es_primo
    VECTOR V_LN, ln
    VECTOR V_FILA, fila
    PRINTS "Constante de Brun con el FPU IEEE 754 emulado\n"
    PRINTS "N\tpares\tB2(N) suma parcial\tB2(N) + 4*C2/ln N\n"
    ; s = 1/3 + 1/5  (par (3,5))
    FDIVV br_s, d1, d3
    FDIVV br_t, d1, d5
    FADDV br_s, br_s, br_t
    SET br_pares, 1
    SET br_k, 1
    SET br_cp, 100                 ; siguiente punto de control (potencia de 10)
    SET br_x10, 2                  ; exponente de br_cp
    FMULV br_4c2, d4, dC2          ; 4*C2
br_ciclo:
    MULI br_p, br_k, 6
    SUBI br_p, br_p, 1              ; p = 6k - 1
    ADDI br_q, br_p, 2              ; q = 6k + 1
    ; ¿se pasó del punto de control? imprimir la fila
br_ctrl:
    JLE br_q, br_cp, br_prueba
    CALL V_FILA
    JGEI br_cp, NMAX, br_fin
    MULI br_cp, br_cp, 10
    ADDI br_x10, br_x10, 1
    JMP br_ctrl
br_prueba:
    MOV IP_N, br_p
    CALL V_PRIMO
    JEQI IP_R, 0, br_sig
    MOV IP_N, br_q
    CALL V_PRIMO
    JEQI IP_R, 0, br_sig
    ; par de primos gemelos: s = s + (1/p + 1/q)
    I2FV br_pf, br_p
    I2FV br_qf, br_q
    FDIVV br_t, d1, br_pf
    FDIVV br_u, d1, br_qf
    FADDV br_t, br_t, br_u
    FADDV br_s, br_s, br_t
    ADDI br_pares, br_pares, 1
br_sig:
    ADDI br_k, br_k, 1
    JMP br_ciclo
br_fin:
    PRINTS "\nValor de referencia (Sebah y Demichel, 2002): B2 = 1.902160583104...\n"
    HALT

; ---------------------------------------------------------------------
;  fila: imprime N, pares, B2(N) y la estimación corregida
; ---------------------------------------------------------------------
.EQU V_FILA, 15
fila:
    PRINTS "10^"
    IPRINTV br_x10
    PUTC 9                        ; tabulador
    IPRINTV br_pares
    PUTC 9
    FPRINTV br_s
    PUTC 9
    I2FV LN_X, br_cp
    CALL V_LN
    FDIVV br_t, br_4c2, LN_R
    FADDV br_t, br_s, br_t
    FPRINTV br_t
    NL
    IRET

; ---------------------------------------------------------------------
;  es_primo: IP_R <- 1 si IP_N (de la forma 6k+-1, >= 5) es primo, si no 0
; ---------------------------------------------------------------------
es_primo:
    SET IP_R, 1
    SET ip_d, 5
ip_ciclo:
    MULM ip_t, ip_d, ip_d
    JGT ip_t, IP_N, ip_fin        ; d*d > n: es primo
    MODM ip_t, IP_N, ip_d
    JEQI ip_t, 0, ip_comp
    ADDI ip_t, ip_d, 2
    MODM ip_t, IP_N, ip_t
    JEQI ip_t, 0, ip_comp
    ADDI ip_d, ip_d, 6
    JMP ip_ciclo
ip_comp:
    SET IP_R, 0
ip_fin:
    IRET

; ---------------------------------------------------------------------
;  ln: LN_R <- ln(LN_X) para LN_X double normal y positivo
;      LN_X = m * 2^k con m en [1,2);  ln m = 2*(t + t^3/3 + t^5/5 + ...)
;      con t = (m-1)/(m+1) <= 1/3   (24 términos: error < 1e-17)
; ---------------------------------------------------------------------
ln:
    SHRI ln_e, LN_X, 52           ; exponente sesgado
    I2FV ln_k, ln_e
    FSUBV ln_k, ln_k, d1023       ; k = e - 1023 (como double)
    LOWI ln_m, LN_X, 52
    ADDI ln_m, ln_m, 1023<<52     ; m = 1.f
    FSUBV ln_t, ln_m, d1
    FADDV ln_u, ln_m, d1
    FDIVV ln_t, ln_t, ln_u        ; t
    FMULV ln_t2, ln_t, ln_t       ; t^2
    MOV ln_pot, ln_t              ; t^(2j+1)
    SET ln_sum, 0
    MOV ln_den, d1                ; 2j+1
    SET ln_j, 24
ln_ciclo:
    FDIVV ln_u, ln_pot, ln_den
    FADDV ln_sum, ln_sum, ln_u
    FMULV ln_pot, ln_pot, ln_t2
    FADDV ln_den, ln_den, d2
    SUBI ln_j, ln_j, 1
    JNEI ln_j, 0, ln_ciclo
    FADDV ln_sum, ln_sum, ln_sum  ; 2*suma
    FMULV ln_u, ln_k, dLN2
    FADDV LN_R, ln_u, ln_sum
    IRET

; ---------------------------------------------------------------- datos
d1:    .DOUBLE 1.0
d2:    .DOUBLE 2.0
d3:    .DOUBLE 3.0
d4:    .DOUBLE 4.0
d5:    .DOUBLE 5.0
d1023: .DOUBLE 1023.0
dC2:   .DOUBLE 0.6601618158468696      ; constante de los primos gemelos
dLN2:  .DOUBLE 0.6931471805599453      ; ln 2
.VAR br_x10, br_s, br_t, br_u, br_pf, br_qf, br_p, br_q, br_k, br_pares, br_cp, br_4c2
.VAR IP_N, IP_R, ip_d, ip_t
.VAR LN_X, LN_R, ln_e, ln_k, ln_m, ln_t, ln_u, ln_t2, ln_pot, ln_sum, ln_den, ln_j

.INCLUDE "fpu.asm"
