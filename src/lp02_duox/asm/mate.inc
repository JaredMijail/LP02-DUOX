; =====================================================================
;  mate.inc  -  Mini librería matemática de 40 instrucciones para la
;               máquina DUOS (Taller 1, Grupo F)
;
;  Cada "instrucción" es una macro .MACRO/.ENDM que el preprocesador
;  expande SOLO a instrucciones nativas, directamente o a través de las
;  macros de macros.inc y de los servicios del FPU de fpu.asm.
;
;  Convenciones:
;    - Forma memoria a memoria, destino primero:  NOMBRE d, a[, b ...]
;      Prefijo I = entero, F = double IEEE 754; sufijo V = variables
;      (como FADDV o IPRINTV).
;    - Enteros: 64 bits con signo en complemento a dos. STORE trunca a
;      64 bits, así que -7 queda guardado como 2^64 - 7.
;    - Flotantes: la variable guarda el patrón binary64 del número.
;    - El destino puede ser el mismo operando (IABSV x, x): cada macro
;      calcula en temporales propios (mt_<macro>_*) y escribe d al final.
;
;  Subrutinas: los algoritmos largos (más de 1 KB si se expandieran en
;  línea) son subrutinas de MATE_RUTINAS y la macro solo pasa los
;  operandos, llama y recoge el resultado, igual que FADDV con el FPU:
;      MT_A, MT_B  operandos        MT_R  resultado
;
;  Vectores de interrupción (CALL n = PUSH n ; INT):
;      0, 1     mini-SO (teclado, print)
;      2 - 7    mate.inc: V_MSQRT, V_MEXP, V_MLN, V_MSIN, V_MCOS, V_MMCM
;      8 - 15   LIBRES para el programa de usuario
;      16 - 29  FPU (fpu.asm)
;      30, 31   LIBRES para el programa de usuario
;
;  Uso:
;      .INCLUDE "mate.inc"       ; al inicio (ya incluye macros.inc)
;      inicio:
;          MATE_INSTALL          ; instala FPU y librería (reemplaza a FPU_INSTALL)
;          ...
;          HALT
;      MATE_RUTINAS              ; UNA vez, después del HALT: subrutinas y datos
;      .INCLUDE "fpu.asm"
;
;  Este archivo no emite nada al incluirse: si declarara .VAR o código al
;  inicio, se ejecutaría desde 0x1000 (una palabra en cero es HALT). Por
;  eso subrutinas, constantes y temporales los emite MATE_RUTINAS donde
;  el programa lo indique.
; =====================================================================
.INCLUDE "macros.inc"

.EQU MT_NAN,     0x7FF8000000000000  ; NaN silencioso
.EQU MT_INF,     0x7FF0000000000000  ; +infinito
.EQU MT_MINF,    0xFFF0000000000000  ; -infinito
.EQU MT_EXP1,    0x3FF0000000000000  ; exponente sesgado 1023 en su lugar (= 1.0)
.EQU MT_SEMILLA, 0x1FF8000000000000  ; 1023 << 51: semilla de Herón

.EQU V_MSQRT, 2
.EQU V_MEXP,  3
.EQU V_MLN,   4
.EQU V_MSIN,  5
.EQU V_MCOS,  6
.EQU V_MMCM,  7

.MACRO MATE_INSTALL        ; instala los vectores del FPU y de la librería (primer paso)
    FPU_INSTALL
    VECTOR V_MSQRT, mt_rut_sqrt
    VECTOR V_MEXP,  mt_rut_exp
    VECTOR V_MLN,   mt_rut_ln
    VECTOR V_MSIN,  mt_rut_sin
    VECTOR V_MCOS,  mt_rut_cos
    VECTOR V_MMCM,  mt_rut_mcm
.ENDM

; ================================================== auxiliares
.MACRO _MOP1 vec, d, x     ; d <- subrutina vec (x)
    MOV MT_A, \x
    CALL \vec
    MOV \d, MT_R
.ENDM

.MACRO _MOP2 vec, d, a, b  ; d <- subrutina vec (a, b)
    MOV MT_A, \a
    MOV MT_B, \b
    CALL \vec
    MOV \d, MT_R
.ENDM

; Saltos con signo. JLT/JGE de macros.inc solo valen para 0 <= a, b < 2^63.
;   Signos distintos: el negativo es el menor.
;   Mismo signo     : a - b no desborda y su bit 63 es el signo de a - b.
.MACRO _JSLT a, b, L       ; si a < b (con signo) ir a L
    SHRI mt_js_a, \a, 63
    SHRI mt_js_b, \b, 63
    JEQ mt_js_a, mt_js_b, %%mismo
    JEQI mt_js_a, 1, \L
    JMP %%no
%%mismo:
    SUBM mt_js_d, \a, \b
    SHRI mt_js_d, mt_js_d, 63
    JEQI mt_js_d, 1, \L
%%no:
.ENDM

.MACRO _JSGE a, b, L       ; si a >= b (con signo) ir a L
    _JSLT \a, \b, %%no
    JMP \L
%%no:
.ENDM

.MACRO ISPRINTV x          ; imprime el entero con signo x
    SHRI mt_ip_s, \x, 63
    JEQI mt_ip_s, 0, %%pos
    PUTC '-'
    INEGV mt_ip_m, \x
    IPRINTV mt_ip_m
    JMP %%fin
%%pos:
    IPRINTV \x
%%fin:
.ENDM

; ================================================== enteras (1-20)
.MACRO INEGV d, a          ; 2. d <- -a  (complemento a uno + 1)
    JEQI \a, 0, %%cero
    RSUBI \d, UNOS64, \a
    ADDI \d, \d, 1
    JMP %%fin
%%cero:
    SET \d, 0
%%fin:
.ENDM

.MACRO IABSV d, a          ; 1. d <- |a|
    SHRI mt_ab_s, \a, 63
    JEQI mt_ab_s, 0, %%pos
    INEGV \d, \a
    JMP %%fin
%%pos:
    MOV \d, \a
%%fin:
.ENDM

.MACRO ISGNV d, a          ; 3. d <- -1, 0 o 1 según el signo de a
    SHRI mt_sg_s, \a, 63
    JEQI \a, 0, %%cero
    JEQI mt_sg_s, 1, %%neg
    SET \d, 1
    JMP %%fin
%%neg:
    SET \d, -1
    JMP %%fin
%%cero:
    SET \d, 0
%%fin:
.ENDM

.MACRO IMINV d, a, b       ; 4. d <- min(a, b) con signo
    _JSLT \b, \a, %%usab
    MOV \d, \a
    JMP %%fin
%%usab:
    MOV \d, \b
%%fin:
.ENDM

.MACRO IMAXV d, a, b       ; 5. d <- max(a, b) con signo
    _JSLT \a, \b, %%usab
    MOV \d, \a
    JMP %%fin
%%usab:
    MOV \d, \b
%%fin:
.ENDM

.MACRO ICLAMPV d, a, lo, hi    ; 6. d <- a limitado al rango [lo, hi]
    IMAXV mt_cl_t, \a, \lo
    IMINV \d, mt_cl_t, \hi
.ENDM

.MACRO IPOTV d, b, e       ; 7. d <- b^e (e >= 0), elevando al cuadrado y multiplicando
    SHRI mt_po_s, \b, 63
    LOWI mt_po_t, \e, 1
    MULM mt_po_s, mt_po_s, mt_po_t     ; 1 si b < 0 y e impar
    IABSV mt_po_b, \b
    MOV mt_po_e, \e
    SET mt_po_r, 1
%%ciclo:
    JEQI mt_po_e, 0, %%signo
    LOWI mt_po_t, mt_po_e, 1
    JEQI mt_po_t, 0, %%par
    MULM mt_po_r, mt_po_r, mt_po_b     ; bit de e en 1: r <- r * b
%%par:
    SHRI mt_po_e, mt_po_e, 1
    JEQI mt_po_e, 0, %%signo
    MULM mt_po_b, mt_po_b, mt_po_b     ; b <- b^2
    JMP %%ciclo
%%signo:
    JEQI mt_po_s, 0, %%pos
    INEGV \d, mt_po_r
    JMP %%fin
%%pos:
    MOV \d, mt_po_r
%%fin:
.ENDM

.MACRO IFACTV d, n         ; 8. d <- n!  (0 <= n <= 20)
    SET mt_fa_r, 1
    MOV mt_fa_i, \n
%%ciclo:
    JLTI mt_fa_i, 2, %%fin
    MULM mt_fa_r, mt_fa_r, mt_fa_i
    SUBI mt_fa_i, mt_fa_i, 1
    JMP %%ciclo
%%fin:
    MOV \d, mt_fa_r
.ENDM

.MACRO IMCDV d, a, b       ; 9. d <- MCD(|a|, |b|)  (algoritmo de Euclides)
    IABSV mt_mc_a, \a
    IABSV mt_mc_b, \b
%%ciclo:
    JEQI mt_mc_b, 0, %%fin
    MODM mt_mc_t, mt_mc_a, mt_mc_b
    MOV mt_mc_a, mt_mc_b
    MOV mt_mc_b, mt_mc_t
    JMP %%ciclo
%%fin:
    MOV \d, mt_mc_a
.ENDM

.MACRO IMCMV d, a, b       ; 10. d <- MCM(|a|, |b|)  (subrutina V_MMCM)
    _MOP2 V_MMCM, \d, \a, \b
.ENDM

.MACRO IRAIZV d, a         ; 11. d <- parte entera de la raíz de a (a >= 0), Newton entero
    MOV mt_rz_a, \a
    MOV mt_rz_x, \a
    JLTI mt_rz_x, 2, %%fin             ; 0 y 1 son su propia raíz
    ADDI mt_rz_y, mt_rz_x, 1
    SHRI mt_rz_y, mt_rz_y, 1           ; y = (x + 1) / 2
%%ciclo:
    JGE mt_rz_y, mt_rz_x, %%fin        ; deja de bajar: x es la raíz
    MOV mt_rz_x, mt_rz_y
    DIVM mt_rz_t, mt_rz_a, mt_rz_x
    ADDM mt_rz_y, mt_rz_x, mt_rz_t
    SHRI mt_rz_y, mt_rz_y, 1           ; y = (x + a / x) / 2
    JMP %%ciclo
%%fin:
    MOV \d, mt_rz_x
.ENDM

.MACRO IPARV d, a          ; 12. d <- 1 si a es par, 0 si es impar
    LOWI mt_pa_t, \a, 1
    RSUBI \d, 1, mt_pa_t
.ENDM

.MACRO IPROMV d, a, b      ; 13. d <- (a + b) / 2 truncado hacia cero
    ADDM mt_pm_s, \a, \b
    SHRI mt_pm_n, mt_pm_s, 63
    JEQI mt_pm_n, 0, %%pos
    INEGV mt_pm_s, mt_pm_s             ; suma negativa: -(|s| / 2)
    SHRI mt_pm_s, mt_pm_s, 1
    INEGV \d, mt_pm_s
    JMP %%fin
%%pos:
    SHRI \d, mt_pm_s, 1
%%fin:
.ENDM

.MACRO IDIVSV d, a, b      ; 14. d <- a / b con signo, truncado hacia cero (b = 0 -> 0)
    SET mt_dv_q, 0
    JEQI \b, 0, %%fin
    IABSV mt_dv_a, \a
    IABSV mt_dv_b, \b
    DIVM mt_dv_q, mt_dv_a, mt_dv_b
    SHRI mt_dv_s, \a, 63
    SHRI mt_dv_t, \b, 63
    JEQ mt_dv_s, mt_dv_t, %%fin        ; signos iguales: cociente positivo
    INEGV mt_dv_q, mt_dv_q
%%fin:
    MOV \d, mt_dv_q
.ENDM

.MACRO IMODSV d, a, b      ; 15. d <- residuo de a / b con el signo de a (b = 0 -> 0)
    SET mt_md_r, 0
    JEQI \b, 0, %%fin
    IABSV mt_md_a, \a
    IABSV mt_md_b, \b
    MODM mt_md_r, mt_md_a, mt_md_b
    SHRI mt_md_s, \a, 63
    JEQI mt_md_s, 0, %%fin
    INEGV mt_md_r, mt_md_r
%%fin:
    MOV \d, mt_md_r
.ENDM

.MACRO IDISTV d, a, b      ; 16. d <- |a - b|
    SUBM mt_di_t, \a, \b
    IABSV \d, mt_di_t
.ENDM

.MACRO IPRIMOV d, n        ; 17. d <- 1 si n es primo, 0 si no (división por tentativa)
    SET mt_pr_r, 0
    SHRI mt_pr_t, \n, 63
    JEQI mt_pr_t, 1, %%fin             ; negativo
    JLTI \n, 2, %%fin                  ; 0 y 1
    SET mt_pr_i, 2
%%ciclo:
    MULM mt_pr_t, mt_pr_i, mt_pr_i
    JGT mt_pr_t, \n, %%primo           ; i*i > n: no hay divisores
    MODM mt_pr_t, \n, mt_pr_i
    JEQI mt_pr_t, 0, %%fin             ; i divide a n
    ADDI mt_pr_i, mt_pr_i, 1
    JMP %%ciclo
%%primo:
    SET mt_pr_r, 1
%%fin:
    MOV \d, mt_pr_r
.ENDM

.MACRO ICOMBV d, n, k      ; 18. d <- C(n, k), combinaciones (0 <= k, n)
    SET mt_cb_r, 0
    JGT \k, \n, %%fin                  ; k > n: 0
    SUBM mt_cb_k, \n, \k
    JLT mt_cb_k, \k, %%menor           ; k <- min(k, n - k)
    MOV mt_cb_k, \k
%%menor:
    SUBM mt_cb_m, \n, mt_cb_k          ; m = n - k
    SET mt_cb_r, 1
    SET mt_cb_i, 0
%%ciclo:
    JEQ mt_cb_i, mt_cb_k, %%fin
    ADDI mt_cb_i, mt_cb_i, 1
    ADDM mt_cb_t, mt_cb_m, mt_cb_i
    MULM mt_cb_r, mt_cb_r, mt_cb_t
    DIVM mt_cb_r, mt_cb_r, mt_cb_i     ; división exacta: r = C(m + i, i)
    JMP %%ciclo
%%fin:
    MOV \d, mt_cb_r
.ENDM

.MACRO ILOG2V d, a         ; 19. d <- parte entera de log2(a)  (-1 si a <= 0)
    SET mt_lg_c, -1
    SHRI mt_lg_t, \a, 63
    JEQI mt_lg_t, 1, %%fin
    JEQI \a, 0, %%fin
    SET mt_lg_c, 0
    MOV mt_lg_x, \a
%%ciclo:
    JLTI mt_lg_x, 2, %%fin
    SHRI mt_lg_x, mt_lg_x, 1
    ADDI mt_lg_c, mt_lg_c, 1
    JMP %%ciclo
%%fin:
    MOV \d, mt_lg_c
.ENDM

.MACRO IFIBV d, n          ; 20. d <- n-ésimo número de Fibonacci (F0 = 0, F1 = 1; n <= 92)
    SET mt_fb_a, 0
    SET mt_fb_b, 1
    MOV mt_fb_i, \n
%%ciclo:
    JEQI mt_fb_i, 0, %%fin
    ADDM mt_fb_t, mt_fb_a, mt_fb_b
    MOV mt_fb_a, mt_fb_b
    MOV mt_fb_b, mt_fb_t
    SUBI mt_fb_i, mt_fb_i, 1
    JMP %%ciclo
%%fin:
    MOV \d, mt_fb_a
.ENDM

; ================================================== punto flotante (21-40)
.MACRO FABSV d, x          ; 21. d <- |x|  (apaga el bit de signo)
    LOWI \d, \x, 63
.ENDM

.MACRO FNEGV d, x          ; 22. d <- -x  (invierte el bit de signo)
    SHRI mt_fn_s, \x, 63
    LOWI mt_fn_m, \x, 63
    RSUBI mt_fn_s, 1, mt_fn_s
    SHLI mt_fn_s, mt_fn_s, 63
    ADDM \d, mt_fn_m, mt_fn_s
.ENDM

.MACRO FSQRV d, x          ; 23. d <- x * x
    FMULV \d, \x, \x
.ENDM

.MACRO FSQRTV d, x         ; 24. d <- raíz cuadrada de x (Herón, subrutina V_MSQRT)
    _MOP1 V_MSQRT, \d, \x
.ENDM

.MACRO FPOTIV d, x, n      ; 25. d <- x^n, n entero con signo (n < 0: 1 / x^|n|)
    MOV mt_pi_b, \x
    IABSV mt_pi_e, \n
    MOV mt_pi_r, MT_UNO
%%ciclo:
    JEQI mt_pi_e, 0, %%signo
    LOWI mt_pi_t, mt_pi_e, 1
    JEQI mt_pi_t, 0, %%par
    FMULV mt_pi_r, mt_pi_r, mt_pi_b
%%par:
    SHRI mt_pi_e, mt_pi_e, 1
    JEQI mt_pi_e, 0, %%signo
    FMULV mt_pi_b, mt_pi_b, mt_pi_b
    JMP %%ciclo
%%signo:
    SHRI mt_pi_t, \n, 63
    JEQI mt_pi_t, 0, %%fin
    FDIVV mt_pi_r, MT_UNO, mt_pi_r
%%fin:
    MOV \d, mt_pi_r
.ENDM

.MACRO FMINV d, x, y       ; 26. d <- min(x, y)  (si hay NaN devuelve x)
    FCMPV mt_mn_c, \x, \y
    MOV mt_mn_r, \x
    JNEI mt_mn_c, F_MAYOR, %%fin
    MOV mt_mn_r, \y
%%fin:
    MOV \d, mt_mn_r
.ENDM

.MACRO FMAXV d, x, y       ; 27. d <- max(x, y)  (si hay NaN devuelve x)
    FCMPV mt_mx_c, \x, \y
    MOV mt_mx_r, \x
    JNEI mt_mx_c, F_MENOR, %%fin
    MOV mt_mx_r, \y
%%fin:
    MOV \d, mt_mx_r
.ENDM

.MACRO FRECV d, x          ; 28. d <- 1 / x
    FDIVV \d, MT_UNO, \x
.ENDM

.MACRO FEXPV d, x          ; 29. d <- e^x  (Taylor con reducción de rango, subrutina V_MEXP)
    _MOP1 V_MEXP, \d, \x
.ENDM

.MACRO FLNV d, x           ; 30. d <- ln x  (serie de atanh, subrutina V_MLN)
    _MOP1 V_MLN, \d, \x
.ENDM

.MACRO FPOTV d, x, y       ; 31. d <- x^y = e^(y ln x)  (x > 0)
    FLNV mt_pt_l, \x
    FMULV mt_pt_l, mt_pt_l, \y
    FEXPV \d, mt_pt_l
.ENDM

.MACRO FSINV d, x          ; 32. d <- sen x  (Taylor, subrutina V_MSIN)
    _MOP1 V_MSIN, \d, \x
.ENDM

.MACRO FCOSV d, x          ; 33. d <- cos x  (Taylor, subrutina V_MCOS)
    _MOP1 V_MCOS, \d, \x
.ENDM

.MACRO FTANV d, x          ; 34. d <- tan x = sen x / cos x
    FSINV mt_tn_s, \x
    FCOSV mt_tn_c, \x
    FDIVV \d, mt_tn_s, mt_tn_c
.ENDM

.MACRO FPROMV d, x, y      ; 35. d <- (x + y) / 2
    FADDV mt_pf_t, \x, \y
    FMULV \d, mt_pf_t, MT_MEDIO
.ENDM

.MACRO FHIPOTV d, x, y     ; 36. d <- raíz(x^2 + y^2)
    FSQRV mt_hp_a, \x
    FSQRV mt_hp_b, \y
    FADDV mt_hp_a, mt_hp_a, mt_hp_b
    FSQRTV \d, mt_hp_a
.ENDM

.MACRO FCLAMPV d, x, lo, hi    ; 37. d <- x limitado al rango [lo, hi]
    FMAXV mt_fc_t, \x, \lo
    FMINV \d, mt_fc_t, \hi
.ENDM

.MACRO FSGNV d, x          ; 38. d <- -1.0 (x < 0), 1.0 (x > 0), x si es +-0 o NaN
    FCMPV mt_fs_c, \x, MT_CERO
    MOV mt_fs_r, \x
    JEQI mt_fs_c, F_MENOR, %%neg
    JNEI mt_fs_c, F_MAYOR, %%fin
    MOV mt_fs_r, MT_UNO
    JMP %%fin
%%neg:
    MOV mt_fs_r, MT_MENOS1
%%fin:
    MOV \d, mt_fs_r
.ENDM

.MACRO FTRUNCV d, x        ; 39. d <- parte entera de x (hacia cero), solo con aritmética entera
    MOV mt_tr_r, \x
    SHRI mt_tr_e, \x, 52
    LOWI mt_tr_e, mt_tr_e, 11          ; exponente sesgado e
    JGEI mt_tr_e, 1075, %%fin          ; |x| >= 2^52, inf o NaN: ya es entero
    JGEI mt_tr_e, 1023, %%cortar
    SHRI mt_tr_r, \x, 63               ; |x| < 1: cero con el signo de x
    SHLI mt_tr_r, mt_tr_r, 63
    JMP %%fin
%%cortar:                              ; borrar los k = 1075 - e bits fraccionarios
    RSUBI P2N, 1075, mt_tr_e
    CALL V_POW2                        ; P2R = 2^k
    DIVM mt_tr_r, mt_tr_r, P2R
    MULM mt_tr_r, mt_tr_r, P2R
%%fin:
    MOV \d, mt_tr_r
.ENDM

.MACRO FFLOORV d, x        ; 40. d <- mayor entero <= x (como double)
    FTRUNCV mt_fl_t, \x
    SHRI mt_fl_s, \x, 63
    JEQI mt_fl_s, 0, %%fin
    JEQ mt_fl_t, \x, %%fin             ; negativo pero ya era entero
    FSUBV mt_fl_t, mt_fl_t, MT_UNO
%%fin:
    MOV \d, mt_fl_t
.ENDM

; ================================================== subrutinas
.MACRO _FRED2PI r, x       ; r <- x reducido a [-pi, pi] restando múltiplos de 2 pi
    FDIVV mt_rd_q, \x, MT_DOSPI
    F2IV mt_rd_q, mt_rd_q              ; q = trunc(x / 2pi)
    I2FV mt_rd_q, mt_rd_q
    FMULV mt_rd_q, mt_rd_q, MT_DOSPI
    FSUBV mt_rd_r, \x, mt_rd_q         ; r en (-2pi, 2pi)
    FCMPV mt_rd_c, mt_rd_r, MT_PI
    JNEI mt_rd_c, F_MAYOR, %%nomayor
    FSUBV mt_rd_r, mt_rd_r, MT_DOSPI
%%nomayor:
    FCMPV mt_rd_c, mt_rd_r, MT_MENOSPI
    JNEI mt_rd_c, F_MENOR, %%listo
    FADDV mt_rd_r, mt_rd_r, MT_DOSPI
%%listo:
    MOV \r, mt_rd_r
.ENDM

; MATE_RUTINAS emite el código de las subrutinas, las constantes y los
; temporales. Va UNA vez, en una zona que no se ejecute en secuencia
; (después del HALT), igual que el .INCLUDE "fpu.asm".
.MACRO MATE_RUTINAS
; ---------------------------------------------------------------------
;  V_MSQRT: MT_R <- raíz(MT_A)  (método de Herón)
;  +-0, +inf y NaN se devuelven igual; x < 0 -> NaN
; ---------------------------------------------------------------------
mt_rut_sqrt:
    MOV mt_sq_x, MT_A
    MOV MT_R, MT_A
    LOWI mt_sq_t, MT_A, 63
    JEQI mt_sq_t, 0, msq_fin           ; +0 y -0
    SHRI mt_sq_t, MT_A, 52
    JEQI mt_sq_t, 0x7FF, msq_fin       ; +inf o NaN
    JLTI mt_sq_t, 0x800, msq_pos
    SET MT_R, MT_NAN                   ; x < 0
    RET
msq_pos:
    SHRI mt_sq_y, MT_A, 1              ; semilla: exponente dividido entre 2
    ADDI mt_sq_y, mt_sq_y, MT_SEMILLA
    SET mt_sq_i, 0
msq_ciclo:
    ADDI mt_sq_i, mt_sq_i, 1
    FDIVV mt_sq_n, mt_sq_x, mt_sq_y
    FADDV mt_sq_n, mt_sq_n, mt_sq_y
    FMULV mt_sq_n, mt_sq_n, MT_MEDIO   ; y' = (y + x / y) / 2
    JLTI mt_sq_i, 2, msq_sigue         ; y1 puede ser mayor que y0
    FCMPV mt_sq_t, mt_sq_n, mt_sq_y
    JNEI mt_sq_t, F_MENOR, msq_listo   ; ya no decrece: convergió
msq_sigue:
    MOV mt_sq_y, mt_sq_n
    JLTI mt_sq_i, 60, msq_ciclo
msq_listo:
    MOV MT_R, mt_sq_y
msq_fin:
    RET

; ---------------------------------------------------------------------
;  V_MEXP: MT_R <- e^MT_A
;  a = |x| se divide entre 2 k veces hasta a <= 0.5; Taylor para e^a;
;  se eleva al cuadrado k veces; x < 0 -> 1 / e^|x|
; ---------------------------------------------------------------------
mt_rut_exp:
    MOV mt_ex_x, MT_A
    MOV MT_R, MT_A
    FCMPV mt_ex_c, mt_ex_x, mt_ex_x
    JEQI mt_ex_c, F_NOORD, mex_fin     ; NaN
    FABSV mt_ex_a, mt_ex_x
    FCMPV mt_ex_c, mt_ex_a, MT_710
    JEQI mt_ex_c, F_MENOR, mex_rango
    SET MT_R, MT_INF                   ; |x| >= 710: e^x desborda...
    SHRI mt_ex_c, mt_ex_x, 63
    JEQI mt_ex_c, 0, mex_fin
    SET MT_R, 0                        ; ...o se vuelve 0
    RET
mex_rango:
    SET mt_ex_k, 0
mex_mitad:
    FCMPV mt_ex_c, mt_ex_a, MT_MEDIO
    JNEI mt_ex_c, F_MAYOR, mex_taylor
    FMULV mt_ex_a, mt_ex_a, MT_MEDIO
    ADDI mt_ex_k, mt_ex_k, 1
    JMP mex_mitad
mex_taylor:                            ; s = 1 + a + a^2/2! + a^3/3! + ...
    MOV mt_ex_s, MT_UNO
    MOV mt_ex_t, MT_UNO
    MOV mt_ex_n, MT_UNO
mex_termino:
    FMULV mt_ex_t, mt_ex_t, mt_ex_a
    FDIVV mt_ex_t, mt_ex_t, mt_ex_n    ; t <- t * a / n
    FADDV mt_ex_u, mt_ex_s, mt_ex_t
    JEQ mt_ex_u, mt_ex_s, mex_cuadrar  ; el término ya no cambia la suma
    MOV mt_ex_s, mt_ex_u
    FADDV mt_ex_n, mt_ex_n, MT_UNO
    JMP mex_termino
mex_cuadrar:                           ; e^|x| = (e^a)^(2^k)
    JEQI mt_ex_k, 0, mex_signo
    FMULV mt_ex_s, mt_ex_s, mt_ex_s
    SUBI mt_ex_k, mt_ex_k, 1
    JMP mex_cuadrar
mex_signo:
    MOV MT_R, mt_ex_s
    SHRI mt_ex_c, mt_ex_x, 63
    JEQI mt_ex_c, 0, mex_fin
    FDIVV MT_R, MT_UNO, mt_ex_s        ; x < 0: e^x = 1 / e^|x|
mex_fin:
    RET

; ---------------------------------------------------------------------
;  V_MLN: MT_R <- ln(MT_A)
;  x = m 2^E (con los bits del exponente), m en [0.707, 1.414];
;  ln m = 2 atanh(t) = 2 (t + t^3/3 + t^5/5 + ...), t = (m-1)/(m+1)
; ---------------------------------------------------------------------
mt_rut_ln:
    MOV mt_ln_x, MT_A
    SHRI mt_ln_e, mt_ln_x, 52          ; signo y exponente
    LOWI mt_ln_t, mt_ln_x, 63
    SET MT_R, MT_MINF
    JEQI mt_ln_t, 0, mln_fin           ; ln(+-0) = -inf
    MOV MT_R, mt_ln_x
    JEQI mt_ln_e, 0x7FF, mln_fin       ; ln(+inf) = +inf, ln(NaN) = NaN
    SET MT_R, MT_NAN
    JGEI mt_ln_e, 0x800, mln_fin       ; x < 0: NaN
    SET mt_ln_k, 0
    JNEI mt_ln_e, 0, mln_normal
    FMULV mt_ln_x, mt_ln_x, MT_2P52    ; subnormal: x * 2^52 y se descuentan 52
    SET mt_ln_k, 52
    SHRI mt_ln_e, mt_ln_x, 52
mln_normal:
    SUBI mt_ln_e, mt_ln_e, 1023
    SUBM mt_ln_e, mt_ln_e, mt_ln_k     ; E (entero con signo)
    LOWI mt_ln_m, mt_ln_x, 52
    ADDI mt_ln_m, mt_ln_m, MT_EXP1     ; m = 1.f en [1, 2)
    FCMPV mt_ln_t, mt_ln_m, MT_RAIZ2
    JNEI mt_ln_t, F_MAYOR, mln_serie
    SUBI mt_ln_m, mt_ln_m, 1<<52       ; m > raiz(2): m <- m / 2 ; E <- E + 1
    ADDI mt_ln_e, mt_ln_e, 1
mln_serie:
    FSUBV mt_ln_t, mt_ln_m, MT_UNO
    FADDV mt_ln_u, mt_ln_m, MT_UNO
    FDIVV mt_ln_t, mt_ln_t, mt_ln_u
    FMULV mt_ln_t2, mt_ln_t, mt_ln_t
    MOV mt_ln_s, mt_ln_t
    MOV mt_ln_p, mt_ln_t
    MOV mt_ln_n, MT_UNO
mln_termino:
    FMULV mt_ln_p, mt_ln_p, mt_ln_t2   ; p = t^n
    FADDV mt_ln_n, mt_ln_n, MT_DOS
    FDIVV mt_ln_u, mt_ln_p, mt_ln_n
    FADDV mt_ln_u, mt_ln_s, mt_ln_u
    JEQ mt_ln_u, mt_ln_s, mln_junta    ; el término ya no cambia la suma
    MOV mt_ln_s, mt_ln_u
    JMP mln_termino
mln_junta:                             ; ln x = E ln2 + 2 s
    I2FV mt_ln_u, mt_ln_e
    FMULV mt_ln_u, mt_ln_u, MT_LN2
    FADDV mt_ln_s, mt_ln_s, mt_ln_s
    FADDV MT_R, mt_ln_u, mt_ln_s
mln_fin:
    RET

; ---------------------------------------------------------------------
;  V_MSIN / V_MCOS: MT_R <- sen(MT_A) / cos(MT_A)
;  Comparten el código: r = x reducido a [-pi, pi] y la serie
;      t <- -t r^2 / ((n+1)(n+2))
;  empezando en t = r, n = 1 (seno) o en t = 1, n = 0 (coseno).
; ---------------------------------------------------------------------
mt_rut_sin:
    SET mt_tg_c, 0
    JMP mtg_comun
mt_rut_cos:
    SET mt_tg_c, 1
mtg_comun:
    SET MT_R, MT_NAN
    SHRI mt_tg_t, MT_A, 52
    LOWI mt_tg_t, mt_tg_t, 11
    JEQI mt_tg_t, 0x7FF, mtg_fin       ; sen/cos de inf o NaN = NaN
    _FRED2PI mt_tg_x, MT_A
    FMULV mt_tg_x2, mt_tg_x, mt_tg_x
    MOV mt_tg_s, mt_tg_x               ; seno: s = t = r, n = 1
    SET mt_tg_n, 1
    JEQI mt_tg_c, 0, mtg_serie
    MOV mt_tg_s, MT_UNO                ; coseno: s = t = 1, n = 0
    SET mt_tg_n, 0
mtg_serie:
    MOV mt_tg_t, mt_tg_s
mtg_termino:
    ADDI mt_tg_k, mt_tg_n, 1
    ADDI mt_tg_n, mt_tg_n, 2
    MULM mt_tg_k, mt_tg_k, mt_tg_n
    I2FV mt_tg_k, mt_tg_k              ; (n+1)(n+2) como double
    FMULV mt_tg_t, mt_tg_t, mt_tg_x2
    FDIVV mt_tg_t, mt_tg_t, mt_tg_k
    FNEGV mt_tg_t, mt_tg_t
    FADDV mt_tg_u, mt_tg_s, mt_tg_t
    JEQ mt_tg_u, mt_tg_s, mtg_listo    ; el término ya no cambia la suma
    MOV mt_tg_s, mt_tg_u
    JMP mtg_termino
mtg_listo:
    MOV MT_R, mt_tg_s
mtg_fin:
    RET

; ---------------------------------------------------------------------
;  V_MMCM: MT_R <- MCM(|MT_A|, |MT_B|) = |a| / MCD * |b|  (0 si alguno es 0)
; ---------------------------------------------------------------------
mt_rut_mcm:
    IABSV mt_mm_a, MT_A
    IABSV mt_mm_b, MT_B
    SET MT_R, 0
    JEQI mt_mm_a, 0, mmc_fin
    JEQI mt_mm_b, 0, mmc_fin
    IMCDV mt_mm_g, mt_mm_a, mt_mm_b
    DIVM MT_R, mt_mm_a, mt_mm_g
    MULM MT_R, MT_R, mt_mm_b
mmc_fin:
    RET

; ---------------------------------------------------------------------
;  Constantes y temporales
; ---------------------------------------------------------------------
MT_CERO:    .WORD 0
MT_UNO:     .DOUBLE 1.0
MT_MENOS1:  .DOUBLE -1.0
MT_DOS:     .DOUBLE 2.0
MT_MEDIO:   .DOUBLE 0.5
MT_PI:      .DOUBLE 3.141592653589793
MT_MENOSPI: .DOUBLE -3.141592653589793
MT_DOSPI:   .DOUBLE 6.283185307179586
MT_LN2:     .DOUBLE 0.6931471805599453
MT_RAIZ2:   .DOUBLE 1.4142135623730951
MT_2P52:    .DOUBLE 4503599627370496.0
MT_710:     .DOUBLE 710.0
.VAR MT_A, MT_B, MT_R
.VAR mt_js_a, mt_js_b, mt_js_d, mt_ip_s, mt_ip_m
.VAR mt_ab_s, mt_sg_s, mt_cl_t, mt_pa_t, mt_di_t
.VAR mt_po_s, mt_po_t, mt_po_b, mt_po_e, mt_po_r
.VAR mt_fa_r, mt_fa_i
.VAR mt_mc_a, mt_mc_b, mt_mc_t
.VAR mt_mm_a, mt_mm_b, mt_mm_g
.VAR mt_rz_a, mt_rz_x, mt_rz_y, mt_rz_t
.VAR mt_pm_s, mt_pm_n
.VAR mt_dv_q, mt_dv_a, mt_dv_b, mt_dv_s, mt_dv_t
.VAR mt_md_r, mt_md_a, mt_md_b, mt_md_s
.VAR mt_pr_r, mt_pr_t, mt_pr_i
.VAR mt_cb_r, mt_cb_k, mt_cb_i, mt_cb_m, mt_cb_t
.VAR mt_lg_c, mt_lg_t, mt_lg_x
.VAR mt_fb_a, mt_fb_b, mt_fb_i, mt_fb_t
.VAR mt_fn_s, mt_fn_m
.VAR mt_sq_x, mt_sq_y, mt_sq_t, mt_sq_i, mt_sq_n
.VAR mt_pi_b, mt_pi_e, mt_pi_r, mt_pi_t
.VAR mt_mn_c, mt_mn_r, mt_mx_c, mt_mx_r
.VAR mt_ex_x, mt_ex_c, mt_ex_a, mt_ex_k, mt_ex_s, mt_ex_t, mt_ex_n, mt_ex_u
.VAR mt_ln_x, mt_ln_e, mt_ln_t, mt_ln_k, mt_ln_m, mt_ln_u, mt_ln_t2
.VAR mt_ln_s, mt_ln_p, mt_ln_n
.VAR mt_pt_l, mt_rd_q, mt_rd_r, mt_rd_c
.VAR mt_tg_c, mt_tg_t, mt_tg_x, mt_tg_x2, mt_tg_s, mt_tg_n, mt_tg_k, mt_tg_u
.VAR mt_tn_s, mt_tn_c, mt_pf_t, mt_hp_a, mt_hp_b, mt_fc_t
.VAR mt_fs_c, mt_fs_r, mt_tr_r, mt_tr_e, mt_fl_t, mt_fl_s
.ENDM
