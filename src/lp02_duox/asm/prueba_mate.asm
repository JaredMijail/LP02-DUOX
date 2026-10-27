; =====================================================================
;  prueba_mate.asm - Prueba de las 40 instrucciones de mate.inc
;
;  Cada línea muestra la instrucción, sus entradas, el resultado obtenido
;  y el esperado. Enteros: deben ser iguales. Flotantes: OK si
;  |obtenido - esperado| <= 1e-12 * max(1, |esperado|). Los valores
;  esperados de punto flotante se calcularon con el módulo math de Python.
; =====================================================================
.INCLUDE "mate.inc"
.EQU V_CHKI, 30
.EQU V_CHKF, 31

inicio:
    MATE_INSTALL                      ; vectores del FPU (16-29) y de mate.inc (2-7)
    VECTOR V_CHKI, chk_ent
    VECTOR V_CHKF, chk_flo
    SET ok_n, 0
    PRINTS "== mate.inc: 40 instrucciones (obtenido / esperado) ==\n"

; ---------------------------------------------------------- enteras
    PRINTS "01 IABSV -7"
    SET ta, -7
    IABSV CK_R, ta
    SET CK_E, 7
    CALL V_CHKI

    PRINTS "02 INEGV 12345 (d = a)"
    SET ta, 12345
    INEGV ta, ta
    MOV CK_R, ta
    SET CK_E, -12345
    CALL V_CHKI

    PRINTS "03 ISGNV -42"
    SET ta, -42
    ISGNV CK_R, ta
    SET CK_E, -1
    CALL V_CHKI

    PRINTS "04 IMINV -5, 3"
    SET ta, -5
    SET tb, 3
    IMINV CK_R, ta, tb
    SET CK_E, -5
    CALL V_CHKI

    PRINTS "05 IMAXV -5, 3"
    IMAXV CK_R, ta, tb
    SET CK_E, 3
    CALL V_CHKI

    PRINTS "06 ICLAMPV 15, -10, 10"
    SET ta, 15
    SET tb, -10
    SET tc, 10
    ICLAMPV CK_R, ta, tb, tc
    SET CK_E, 10
    CALL V_CHKI

    PRINTS "07 IPOTV -3, 5"
    SET ta, -3
    SET tb, 5
    IPOTV CK_R, ta, tb
    SET CK_E, -243
    CALL V_CHKI

    PRINTS "08 IFACTV 15"
    SET ta, 15
    IFACTV CK_R, ta
    SET CK_E, 1307674368000
    CALL V_CHKI

    PRINTS "09 IMCDV 84, -36"
    SET ta, 84
    SET tb, -36
    IMCDV CK_R, ta, tb
    SET CK_E, 12
    CALL V_CHKI

    PRINTS "10 IMCMV 21, 6"
    SET ta, 21
    SET tb, 6
    IMCMV CK_R, ta, tb
    SET CK_E, 42
    CALL V_CHKI

    PRINTS "11 IRAIZV 99999999"
    SET ta, 99999999
    IRAIZV CK_R, ta
    SET CK_E, 9999
    CALL V_CHKI

    PRINTS "12 IPARV -7"
    SET ta, -7
    IPARV CK_R, ta
    SET CK_E, 0
    CALL V_CHKI

    PRINTS "13 IPROMV -7, 2"
    SET ta, -7
    SET tb, 2
    IPROMV CK_R, ta, tb
    SET CK_E, -2
    CALL V_CHKI

    PRINTS "14 IDIVSV -17, 5"
    SET ta, -17
    SET tb, 5
    IDIVSV CK_R, ta, tb
    SET CK_E, -3
    CALL V_CHKI

    PRINTS "15 IMODSV -17, 5"
    IMODSV CK_R, ta, tb
    SET CK_E, -2
    CALL V_CHKI

    PRINTS "16 IDISTV -8, 5"
    SET ta, -8
    IDISTV CK_R, ta, tb
    SET CK_E, 13
    CALL V_CHKI

    PRINTS "17 IPRIMOV 97"
    SET ta, 97
    IPRIMOV CK_R, ta
    SET CK_E, 1
    CALL V_CHKI

    PRINTS "18 ICOMBV 10, 3"
    SET ta, 10
    SET tb, 3
    ICOMBV CK_R, ta, tb
    SET CK_E, 120
    CALL V_CHKI

    PRINTS "19 ILOG2V 1000"
    SET ta, 1000
    ILOG2V CK_R, ta
    SET CK_E, 9
    CALL V_CHKI

    PRINTS "20 IFIBV 50"
    SET ta, 50
    IFIBV CK_R, ta
    SET CK_E, 12586269025
    CALL V_CHKI

; ---------------------------------------------------- punto flotante
    PRINTS "21 FABSV -2.5"
    FABSV CK_R, f_m25
    MOV CK_E, f_25
    CALL V_CHKF

    PRINTS "22 FNEGV 3.75"
    FNEGV CK_R, f_375
    MOV CK_E, f_m375
    CALL V_CHKF

    PRINTS "23 FSQRV -1.5"
    FSQRV CK_R, f_m15
    MOV CK_E, f_225
    CALL V_CHKF

    PRINTS "24 FSQRTV 2"
    FSQRTV CK_R, f_2
    MOV CK_E, f_raiz2
    CALL V_CHKF

    PRINTS "25 FPOTIV 1.5, -3"
    SET ta, -3
    FPOTIV CK_R, f_15, ta
    MOV CK_E, f_pot
    CALL V_CHKF

    PRINTS "26 FMINV 2.5, -1"
    FMINV CK_R, f_25, f_m1
    MOV CK_E, f_m1
    CALL V_CHKF

    PRINTS "27 FMAXV 2.5, -1"
    FMAXV CK_R, f_25, f_m1
    MOV CK_E, f_25
    CALL V_CHKF

    PRINTS "28 FRECV 8"
    FRECV CK_R, f_8
    MOV CK_E, f_0125
    CALL V_CHKF

    PRINTS "29 FEXPV 1"
    FEXPV CK_R, f_1
    MOV CK_E, f_e
    CALL V_CHKF

    PRINTS "30 FLNV 10"
    FLNV CK_R, f_10
    MOV CK_E, f_ln10
    CALL V_CHKF

    PRINTS "31 FPOTV 9, 0.5"
    FPOTV CK_R, f_9, f_05
    MOV CK_E, f_3
    CALL V_CHKF

    PRINTS "32 FSINV 10"
    FSINV CK_R, f_10
    MOV CK_E, f_sin10
    CALL V_CHKF

    PRINTS "33 FCOSV 1"
    FCOSV CK_R, f_1
    MOV CK_E, f_cos1
    CALL V_CHKF

    PRINTS "34 FTANV 0.5"
    FTANV CK_R, f_05
    MOV CK_E, f_tan05
    CALL V_CHKF

    PRINTS "35 FPROMV 1.5, 4"
    FPROMV CK_R, f_15, f_4
    MOV CK_E, f_275
    CALL V_CHKF

    PRINTS "36 FHIPOTV 3, 4"
    FHIPOTV CK_R, f_3, f_4
    MOV CK_E, f_5
    CALL V_CHKF

    PRINTS "37 FCLAMPV 7.5, 0, 5"
    FCLAMPV CK_R, f_75, f_0, f_5
    MOV CK_E, f_5
    CALL V_CHKF

    PRINTS "38 FSGNV -0.001"
    FSGNV CK_R, f_mmil
    MOV CK_E, f_m1
    CALL V_CHKF

    PRINTS "39 FTRUNCV -3.75"
    FTRUNCV CK_R, f_m375
    MOV CK_E, f_m3
    CALL V_CHKF

    PRINTS "40 FFLOORV -3.25"
    FFLOORV CK_R, f_m325
    MOV CK_E, f_m4
    CALL V_CHKF

    PRINTS "Correctas: "
    IPRINTV ok_n
    PRINTS " de 40\n"
    HALT

; ---------------------------------------------------------------------
;  chk_ent: imprime CK_R y CK_E (enteros con signo) y los compara
; ---------------------------------------------------------------------
chk_ent:
    PRINTS " = "
    ISPRINTV CK_R
    PRINTS "  esperado "
    ISPRINTV CK_E
    JEQ CK_R, CK_E, chk_ok
    PRINTS "  FALLO\n"
    IRET
chk_ok:
    ADDI ok_n, ok_n, 1
    PRINTS "  OK\n"
    IRET

; ---------------------------------------------------------------------
;  chk_flo: imprime CK_R y CK_E (double) y los compara con tolerancia
;  relativa. Solo usa macros de macros.inc, no las de mate.inc.
; ---------------------------------------------------------------------
chk_flo:
    PRINTS " = "
    FPRINTV CK_R
    PRINTS "  esperado "
    FPRINTV CK_E
    JEQ CK_R, CK_E, chk_ok            ; iguales bit a bit
    FSUBV cf_d, CK_R, CK_E
    LOWI cf_d, cf_d, 63               ; |obtenido - esperado|
    LOWI cf_m, CK_E, 63               ; |esperado|
    FCMPV cf_c, cf_m, f_1
    JNEI cf_c, F_MENOR, cf_escala
    MOV cf_m, f_1                     ; max(1, |esperado|)
cf_escala:
    FMULV cf_m, cf_m, f_tol
    FCMPV cf_c, cf_d, cf_m
    JEQI cf_c, F_MENOR, chk_ok
    JEQI cf_c, F_IGUAL, chk_ok
    PRINTS "  FALLO\n"
    IRET

; ---------------------------------------------------------------- datos
f_0:     .DOUBLE 0.0
f_05:    .DOUBLE 0.5
f_1:     .DOUBLE 1.0
f_m1:    .DOUBLE -1.0
f_15:    .DOUBLE 1.5
f_m15:   .DOUBLE -1.5
f_2:     .DOUBLE 2.0
f_225:   .DOUBLE 2.25
f_25:    .DOUBLE 2.5
f_m25:   .DOUBLE -2.5
f_275:   .DOUBLE 2.75
f_3:     .DOUBLE 3.0
f_m3:    .DOUBLE -3.0
f_m325:  .DOUBLE -3.25
f_375:   .DOUBLE 3.75
f_m375:  .DOUBLE -3.75
f_4:     .DOUBLE 4.0
f_m4:    .DOUBLE -4.0
f_5:     .DOUBLE 5.0
f_75:    .DOUBLE 7.5
f_8:     .DOUBLE 8.0
f_9:     .DOUBLE 9.0
f_10:    .DOUBLE 10.0
f_0125:  .DOUBLE 0.125
f_mmil:  .DOUBLE -0.001
f_raiz2: .DOUBLE 1.4142135623730951
f_pot:   .DOUBLE 0.2962962962962963
f_e:     .DOUBLE 2.718281828459045
f_ln10:  .DOUBLE 2.302585092994046
f_sin10: .DOUBLE -0.5440211108893698
f_cos1:  .DOUBLE 0.5403023058681398
f_tan05: .DOUBLE 0.5463024898437905
f_tol:   .DOUBLE 1e-12
.VAR ta, tb, tc, CK_R, CK_E, ok_n, cf_d, cf_m, cf_c

MATE_RUTINAS
.INCLUDE "fpu.asm"
