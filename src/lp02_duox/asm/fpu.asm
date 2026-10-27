; =====================================================================
;  fpu.asm  -  Emulador de FPU IEEE 754 binary64 (doble precisión)
;              escrito en el ensamblador de la máquina DUOS (Tarea 10)
;
;  "Registros" del FPU (en memoria):
;     FA, FB  operandos       FR  resultado       FPREC  decimales a imprimir
;
;  Servicios (se invocan con CALL n = PUSH n ; INT):
;     V_FADD   FR <- FA + FB          V_FI2F   FR <- double(FA entero con signo)
;     V_FSUB   FR <- FA - FB          V_FF2I   FR <- int64(FA) truncado
;     V_FMUL   FR <- FA * FB          V_FCMP   FR <- 0 (=) 1 (<) 2 (>) 3 (NaN)
;     V_FDIV   FR <- FA / FB          V_FPRINT imprime FA en decimal
;     V_FHEX   imprime FA en hex      V_PRINTU imprime el entero PU_X
;
;  Formato binary64:  s (1 bit) | e (11 bits, sesgo 1023) | f (52 bits)
;     e = 0      -> cero (f = 0) o subnormal: 0.f x 2^-1022
;     e = 2047   -> infinito (f = 0) o NaN (f != 0)
;     otro e     -> normal: 1.f x 2^(e-1023)
;
;  Redondeo: al más cercano, empates al par (roundTiesToEven, IEEE 754-2008
;  §4.3.1). Se usan 10 bits extra (guarda, redondeo) y un bit "pegajoso"
;  (sticky) para obtener siempre el resultado correctamente redondeado.
;
;  Convención interna para el empaquetado (NRPACK):
;     valor = R_SIG x 2^(R_E - OFF - 1084)
;  con R_SIG < 2^63. OFF desplaza los exponentes para que nunca sean
;  negativos (la máquina solo maneja bien enteros sin signo).
;
;  Ningún registro de la máquina supera 64 bits durante estas rutinas
;  (comprobado con "ejecutar.py --verificar64" y con pruebas/pruebas_fpu.py).
; =====================================================================

.EQU OFF, 4096
.EQU EXPMAX, 0x7FF
.EQU HID, 1<<52                ; bit implícito
.EQU QNAN, 0x7FF8000000000000  ; NaN silencioso por defecto
.EQU QBIT, 1<<51               ; bit que distingue NaN silencioso
.EQU D_UNMEDIO, 0x3FE0000000000000   ; 0.5
.EQU D_UNO, 0x3FF0000000000000       ; 1.0
.EQU D_DIEZ, 0x4024000000000000      ; 10.0

; ---------------------------------------------------- UNPACK x -> s, e, f
.MACRO UNPACK x, s, e, f
    SHRI \s, \x, 63
    SHRI \e, \x, 52
    LOWI \e, \e, 11
    LOWI \f, \x, 52
.ENDM

; FR <- x con el bit de NaN silencioso encendido
.MACRO QUIET x
    MOV FR, \x
    BITI fq_t, \x, 51
    JNEI fq_t, 0, %%ya
    ADDI FR, FR, QBIT
%%ya:
.ENDM

; FR <- infinito con signo s
.MACRO MKINF s
    SHLI FR, \s, 63
    ADDI FR, FR, EXPMAX<<52
.ENDM

; =====================================================================
;  POW2: P2R <- 2^P2N   (0 <= P2N <= 63), por descomposición binaria
; =====================================================================
fpu_pow2:
    SET P2R, 1
    MOV p2_t, P2N
    JLTI p2_t, 32, p2_16
    MULI P2R, P2R, 1<<32
    SUBI p2_t, p2_t, 32
p2_16:
    JLTI p2_t, 16, p2_8
    MULI P2R, P2R, 1<<16
    SUBI p2_t, p2_t, 16
p2_8:
    JLTI p2_t, 8, p2_4
    MULI P2R, P2R, 1<<8
    SUBI p2_t, p2_t, 8
p2_4:
    JLTI p2_t, 4, p2_2
    MULI P2R, P2R, 1<<4
    SUBI p2_t, p2_t, 4
p2_2:
    JLTI p2_t, 2, p2_1
    MULI P2R, P2R, 1<<2
    SUBI p2_t, p2_t, 2
p2_1:
    JLTI p2_t, 1, p2_fin
    MULI P2R, P2R, 2
p2_fin:
    IRET

; =====================================================================
;  SRJAM: J_X <- J_X >> J_N, con "jamming": si algún bit descartado es 1,
;  se enciende el bit menos significativo del resultado (bit pegajoso).
; =====================================================================
fpu_srjam:
    JEQI J_N, 0, srj_fin
    JLTI J_N, 63, srj_corto
    JEQI J_X, 0, srj_fin            ; desplazamiento >= 63: queda 0 o 1
    SET J_X, 1
    JMP srj_fin
srj_corto:
    MOV P2N, J_N
    CALL V_POW2
    MODM srj_perd, J_X, P2R          ; bits que se pierden
    DIVM J_X, J_X, P2R
    JEQI srj_perd, 0, srj_fin
    SETLSB J_X
srj_fin:
    IRET

; =====================================================================
;  NORM53: normaliza un operando finito distinto de cero.
;  Entrada: N_E (campo exponente 0..2046), N_F (fracción)
;  Salida : N_M en [2^52, 2^53) y N_E = E + OFF tal que valor = N_M x 2^(E-1075)
; =====================================================================
fpu_norm53:
    ADDI N_E, N_E, OFF
    JEQI N_E, OFF, n53_sub
    ADDI N_M, N_F, HID                ; normal: se agrega el 1 implícito
    IRET
n53_sub:                              ; subnormal: E = 1 y se corre a la izquierda
    SET N_E, OFF+1
    MOV N_M, N_F
    JGEI N_M, 1<<21, n53_16
    SHLI N_M, N_M, 32
    SUBI N_E, N_E, 32
n53_16:
    JGEI N_M, 1<<37, n53_8
    SHLI N_M, N_M, 16
    SUBI N_E, N_E, 16
n53_8:
    JGEI N_M, 1<<45, n53_4
    SHLI N_M, N_M, 8
    SUBI N_E, N_E, 8
n53_4:
    JGEI N_M, 1<<49, n53_2
    SHLI N_M, N_M, 4
    SUBI N_E, N_E, 4
n53_2:
    JGEI N_M, 1<<51, n53_1
    SHLI N_M, N_M, 2
    SUBI N_E, N_E, 2
n53_1:
    JGEI N_M, 1<<52, n53_fin
    SHLI N_M, N_M, 1
    SUBI N_E, N_E, 1
n53_fin:
    IRET

; =====================================================================
;  NRPACK: normaliza, redondea y empaqueta.
;  Entrada: R_S (signo), R_E (exponente + OFF), R_SIG (< 2^63)
;  Salida : FR (patrón binary64)
; =====================================================================
fpu_nrpack:
    JNEI R_SIG, 0, nrp_norm
    SHLI FR, R_S, 63                  ; cero con signo
    IRET
nrp_norm:                             ; llevar el 1 más alto al bit 62
    JGEI R_SIG, 1<<31, nrp_16
    SHLI R_SIG, R_SIG, 32
    SUBI R_E, R_E, 32
nrp_16:
    JGEI R_SIG, 1<<47, nrp_8
    SHLI R_SIG, R_SIG, 16
    SUBI R_E, R_E, 16
nrp_8:
    JGEI R_SIG, 1<<55, nrp_4
    SHLI R_SIG, R_SIG, 8
    SUBI R_E, R_E, 8
nrp_4:
    JGEI R_SIG, 1<<59, nrp_2
    SHLI R_SIG, R_SIG, 4
    SUBI R_E, R_E, 4
nrp_2:
    JGEI R_SIG, 1<<61, nrp_1
    SHLI R_SIG, R_SIG, 2
    SUBI R_E, R_E, 2
nrp_1:
    JGEI R_SIG, 1<<62, rp_rango
    SHLI R_SIG, R_SIG, 1
    SUBI R_E, R_E, 1
rp_rango:
    JGEI R_E, OFF, rp_nosub
    ; ---- exponente < 0: resultado subnormal (desbordamiento gradual)
    RSUBI J_N, OFF, R_E
    MOV J_X, R_SIG
    CALL V_SRJAM
    MOV R_SIG, J_X
    SET R_E, OFF
    JMP rp_redondeo
rp_nosub:
    JLTI R_E, OFF+0x7FE, rp_redondeo
    MKINF R_S                         ; desbordamiento -> infinito
    IRET
rp_redondeo:
    LOWI rp_bits, R_SIG, 10           ; los 10 bits que se descartan
    ADDI R_SIG, R_SIG, 0x200          ; sumar medio ulp
    SHRI R_SIG, R_SIG, 10
    JNEI rp_bits, 0x200, rp_empaca
    SHRI R_SIG, R_SIG, 1              ; empate exacto: forzar par
    SHLI R_SIG, R_SIG, 1
rp_empaca:                            ; FR = s<<63 + e<<52 + sig
    SUBI rp_t, R_E, OFF               ; (el 1 implícito de sig suma 1 a e;
    SHLI rp_t, rp_t, 52               ;  si el redondeo desborda la mantisa
    ADDM rp_t, rp_t, R_SIG            ;  el exponente sube solo)
    SHLI rp_u, R_S, 63
    ADDM FR, rp_t, rp_u
    IRET

; =====================================================================
;  FADD / FSUB
; =====================================================================
fpu_fsub:
    UNPACK FA, a_s, a_e, a_f
    UNPACK FB, b_s, b_e, b_f
    RSUBI b_s, 1, b_s                 ; a - b = a + (-b)
    JMP add_nucleo
fpu_fadd:
    UNPACK FA, a_s, a_e, a_f
    UNPACK FB, b_s, b_e, b_f
add_nucleo:
    JEQI a_e, EXPMAX, add_aesp
    JEQI b_e, EXPMAX, add_besp
    ; ---- ambos finitos: mantisa con bit implícito y exponente efectivo
    MOV a_m, a_f
    JEQI a_e, 0, add_asub
    ADDI a_m, a_m, HID
    JMP add_a2
add_asub:
    SET a_e, 1
add_a2:
    MOV b_m, b_f
    JEQI b_e, 0, add_bsub
    ADDI b_m, b_m, HID
    JMP add_b2
add_bsub:
    SET b_e, 1
add_b2:
    JNEI a_m, 0, add_nocero
    JNEI b_m, 0, add_nocero
    MULM FR, a_s, b_s                 ; 0 + 0: negativo solo si ambos lo son
    SHLI FR, FR, 63
    IRET
add_nocero:
    SHLI a_m, a_m, 9                  ; 9 bits extra de precisión
    SHLI b_m, b_m, 9
    ; ---- ordenar para que |A| >= |B|
    JGT a_e, b_e, add_orden
    JLT a_e, b_e, add_inter
    JGE a_m, b_m, add_orden
add_inter:
    MOV add_t, a_s
    MOV a_s, b_s
    MOV b_s, add_t
    MOV add_t, a_e
    MOV a_e, b_e
    MOV b_e, add_t
    MOV add_t, a_m
    MOV a_m, b_m
    MOV b_m, add_t
add_orden:
    ; ---- alinear B al exponente de A (con bit pegajoso)
    SUBM J_N, a_e, b_e
    MOV J_X, b_m
    CALL V_SRJAM
    MOV b_m, J_X
    MOV R_S, a_s
    ADDI R_E, a_e, OFF
    JNE a_s, b_s, add_resta
    ADDM R_SIG, a_m, b_m              ; misma signo: suma de magnitudes
    JMP add_empaca
add_resta:
    SUBM R_SIG, a_m, b_m              ; signos distintos: resta de magnitudes
    JNEI R_SIG, 0, add_empaca
    SET FR, 0                         ; x - x = +0
    IRET
add_empaca:
    CALL V_NRPACK
    IRET
    ; ---- casos especiales
add_aesp:                             ; A es infinito o NaN
    JNEI a_f, 0, add_qa
    JNEI b_e, EXPMAX, add_ra          ; inf + finito = inf
    JNEI b_f, 0, add_qb
    JEQ a_s, b_s, add_ra              ; inf + inf (mismo signo) = inf
    SET FR, QNAN                      ; inf - inf = NaN (operación inválida)
    IRET
add_besp:                             ; A finito, B infinito o NaN
    JNEI b_f, 0, add_qb
    MKINF b_s
    IRET
add_ra:
    MOV FR, FA
    IRET
add_qa:
    QUIET FA
    IRET
add_qb:
    QUIET FB
    IRET

; =====================================================================
;  FMUL
; =====================================================================
fpu_fmul:
    UNPACK FA, a_s, a_e, a_f
    UNPACK FB, b_s, b_e, b_f
    ADDM R_S, a_s, b_s                ; signo = a_s XOR b_s
    LOWI R_S, R_S, 1
    JNEI a_e, EXPMAX, mul_1
    JNEI a_f, 0, mul_qa
mul_1:
    JNEI b_e, EXPMAX, mul_2
    JNEI b_f, 0, mul_qb
mul_2:
    JEQI a_e, EXPMAX, mul_ainf
    JEQI b_e, EXPMAX, mul_binf
    JNEI a_e, 0, mul_3                ; ¿algún cero?
    JEQI a_f, 0, mul_cero
mul_3:
    JNEI b_e, 0, mul_4
    JEQI b_f, 0, mul_cero
mul_4:
    MOV N_E, a_e
    MOV N_F, a_f
    CALL V_NORM53
    MOV a_m, N_M
    MOV a_e, N_E
    MOV N_E, b_e
    MOV N_F, b_f
    CALL V_NORM53
    MOV b_m, N_M
    MOV b_e, N_E
    ; ---- producto de 106 bits con mitades de 32 bits:
    ;      P = hh*2^64 + (ah*bl + al*bh)*2^32 + ll
    SHRI a_h, a_m, 32
    LOWI a_l, a_m, 32
    SHRI b_h, b_m, 32
    LOWI b_l, b_m, 32
    MULM m_hh, a_h, b_h               ; < 2^42
    MULM m_c1, a_h, b_l               ; < 2^53
    MULM m_c2, a_l, b_h
    ADDM m_mid, m_c1, m_c2            ; < 2^54
    MULM m_ll, a_l, b_l               ; < 2^64
    ; ---- Q = P >> 43 (< 2^63) y bit pegajoso = (P mod 2^43 != 0)
    SHLI m_q, m_hh, 21
    SHRI m_t, m_mid, 11
    ADDM m_q, m_q, m_t
    SHRI m_t, m_ll, 43
    ADDM m_q, m_q, m_t
    LOWI m_t, m_mid, 11
    SHLI m_t, m_t, 32
    LOWI m_u, m_ll, 43
    ADDM m_t, m_t, m_u                ; parte baja (< 2^44)
    SHRI m_u, m_t, 43                 ; acarreo hacia Q
    ADDM m_q, m_q, m_u
    LOWI m_t, m_t, 43
    JEQI m_t, 0, mul_exacto
    SETLSB m_q
mul_exacto:
    MOV R_SIG, m_q
    ADDM R_E, a_e, b_e                ; E = Ea + Eb - 1023
    SUBI R_E, R_E, OFF+1023
    CALL V_NRPACK
    IRET
mul_ainf:                             ; inf * 0 = NaN ; inf * x = inf
    JNEI b_e, 0, mul_inf
    JEQI b_f, 0, mul_nan
    JMP mul_inf
mul_binf:
    JNEI a_e, 0, mul_inf
    JEQI a_f, 0, mul_nan
mul_inf:
    MKINF R_S
    IRET
mul_nan:
    SET FR, QNAN
    IRET
mul_cero:
    SHLI FR, R_S, 63
    IRET
mul_qa:
    QUIET FA
    IRET
mul_qb:
    QUIET FB
    IRET

; =====================================================================
;  FDIV
; =====================================================================
fpu_fdiv:
    UNPACK FA, a_s, a_e, a_f
    UNPACK FB, b_s, b_e, b_f
    ADDM R_S, a_s, b_s
    LOWI R_S, R_S, 1
    JNEI a_e, EXPMAX, div_1
    JNEI a_f, 0, mul_qa
div_1:
    JNEI b_e, EXPMAX, div_2
    JNEI b_f, 0, mul_qb
div_2:
    JNEI a_e, EXPMAX, div_3
    JEQI b_e, EXPMAX, mul_nan         ; inf / inf = NaN
    JMP mul_inf                       ; inf / x = inf
div_3:
    JEQI b_e, EXPMAX, mul_cero        ; x / inf = 0
    JNEI b_e, 0, div_4                ; ¿divisor cero?
    JNEI b_f, 0, div_4
    JNEI a_e, 0, mul_inf              ; x / 0 = inf (división por cero)
    JEQI a_f, 0, mul_nan              ; 0 / 0 = NaN
    JMP mul_inf
div_4:
    JNEI a_e, 0, div_5
    JEQI a_f, 0, mul_cero             ; 0 / x = 0
div_5:
    MOV N_E, a_e
    MOV N_F, a_f
    CALL V_NORM53
    MOV a_m, N_M
    MOV a_e, N_E
    MOV N_E, b_e
    MOV N_F, b_f
    CALL V_NORM53
    MOV b_m, N_M
    MOV b_e, N_E
    ; ---- división larga en bloques de 10 bits: Q = floor(Ma * 2^60 / Mb)
    DIVM d_q, a_m, b_m
    MODM d_r, a_m, b_m
    SET d_i, 6
div_ciclo:
    SHLI d_r, d_r, 10                 ; r < Mb < 2^53  ->  r*2^10 < 2^63
    SHLI d_q, d_q, 10
    DIVM d_t, d_r, b_m
    ADDM d_q, d_q, d_t
    MODM d_r, d_r, b_m
    SUBI d_i, d_i, 1
    JNEI d_i, 0, div_ciclo
    JEQI d_r, 0, div_exacto
    SETLSB d_q                        ; residuo != 0 -> bit pegajoso
div_exacto:
    MOV R_SIG, d_q
    ADDI R_E, a_e, 1024+OFF           ; E = Ea - Eb + 1024
    SUBM R_E, R_E, b_e
    CALL V_NRPACK
    IRET

; =====================================================================
;  FI2F: FR <- double(FA), FA entero de 64 bits en complemento a dos
; =====================================================================
fpu_fi2f:
    JNEI FA, 0, i2f_nocero
    SET FR, 0
    IRET
i2f_nocero:
    SET R_S, 0
    MOV R_SIG, FA
    SET R_E, 1084+OFF
    SHRI i2f_t, FA, 63
    JEQI i2f_t, 0, i2f_pos
    SET R_S, 1
    RSUBI R_SIG, UNOS64, FA           ; magnitud = 2^64 - FA
    ADDI R_SIG, R_SIG, 1
i2f_pos:
    JNEI R_SIG, BIT63, i2f_ok         ; único caso >= 2^63: -2^63
    SET R_SIG, 1<<62
    SET R_E, 1085+OFF
i2f_ok:
    CALL V_NRPACK
    IRET

; =====================================================================
;  FF2I: FR <- int64(FA) truncado hacia cero.
;  NaN, infinito o |FA| >= 2^63 devuelven 0x8000000000000000 ("indefinido",
;  como la instrucción CVTTSD2SI de x86).
; =====================================================================
fpu_ff2i:
    UNPACK FA, a_s, a_e, a_f
    JGEI a_e, 1023, f2i_1
    SET FR, 0                         ; |x| < 1
    IRET
f2i_1:
    JLTI a_e, 1086, f2i_2
    SET FR, BIT63
    IRET
f2i_2:
    ADDI a_m, a_f, HID
    JLTI a_e, 1075, f2i_der
    SUBI P2N, a_e, 1075
    CALL V_POW2
    MULM a_m, a_m, P2R
    JMP f2i_signo
f2i_der:
    RSUBI P2N, 1075, a_e
    CALL V_POW2
    DIVM a_m, a_m, P2R
f2i_signo:
    JEQI a_s, 0, f2i_pos
    RSUBI FR, UNOS64, a_m             ; complemento a dos
    ADDI FR, FR, 1
    IRET
f2i_pos:
    MOV FR, a_m
    IRET

; =====================================================================
;  FCMP: FR <- 0 si FA = FB, 1 si FA < FB, 2 si FA > FB, 3 si hay NaN
; =====================================================================
fpu_fcmp:
    UNPACK FA, a_s, a_e, a_f
    UNPACK FB, b_s, b_e, b_f
    JNEI a_e, EXPMAX, cmp_1
    JNEI a_f, 0, cmp_noord
cmp_1:
    JNEI b_e, EXPMAX, cmp_2
    JNEI b_f, 0, cmp_noord
cmp_2:
    LOWI a_m, FA, 63                  ; magnitudes (sin el bit de signo)
    LOWI b_m, FB, 63
    JNEI a_m, 0, cmp_3
    JEQI b_m, 0, cmp_igual            ; +0 = -0
cmp_3:
    JEQ a_s, b_s, cmp_mismo
    JEQI a_s, 1, cmp_menor
    JMP cmp_mayor
cmp_mismo:
    JEQ a_m, b_m, cmp_igual
    JLT a_m, b_m, cmp_magmenor
    JEQI a_s, 0, cmp_mayor
    JMP cmp_menor
cmp_magmenor:
    JEQI a_s, 0, cmp_menor
    JMP cmp_mayor
cmp_igual:
    SET FR, F_IGUAL
    IRET
cmp_menor:
    SET FR, F_MENOR
    IRET
cmp_mayor:
    SET FR, F_MAYOR
    IRET
cmp_noord:
    SET FR, F_NOORD
    IRET

; =====================================================================
;  PRINTU: imprime el entero sin signo PU_X (< 10^18) en decimal, con al
;  menos PU_W dígitos (rellenando con ceros a la izquierda)
; =====================================================================
fpu_printu:
    SET pu_p, 1
    SET pu_k, 1
pu_buscar:
    JGEI pu_p, 100000000000000000, pu_listo
    MULI pu_t, pu_p, 10
    JLE pu_t, PU_X, pu_crecer
    JLT pu_k, PU_W, pu_crecer
    JMP pu_listo
pu_crecer:
    MOV pu_p, pu_t
    ADDI pu_k, pu_k, 1
    JMP pu_buscar
pu_listo:
    DIVM pu_d, PU_X, pu_p
    LOAD pu_d
    PUSH '0'
    ADD
    OUT
    MODM PU_X, PU_X, pu_p
    DIVI pu_p, pu_p, 10
    JNEI pu_p, 0, pu_listo
    IRET

; =====================================================================
;  FHEX: imprime FA como 0x + 16 dígitos hexadecimales
; =====================================================================
fpu_fhex:
    PRINTS "0x"
    MOV hx_x, FA
    SET hx_p, 1<<60
hx_ciclo:
    DIVM hx_d, hx_x, hx_p
    MODM hx_x, hx_x, hx_p
    JLTI hx_d, 10, hx_dig
    ADDI hx_d, hx_d, 'A'-10
    JMP hx_out
hx_dig:
    ADDI hx_d, hx_d, '0'
hx_out:
    LOAD hx_d
    OUT
    DIVI hx_p, hx_p, 16
    JNEI hx_p, 0, hx_ciclo
    IRET

; =====================================================================
;  FPRINT: imprime FA en decimal con FPREC cifras decimales (0..17).
;    2^-7 <= |x| < 2^50 : notación fija, conversión exacta (redondeo al par)
;    otro caso          : notación científica con 12 decimales; se escala
;                         con el propio FPU (FCMP, FMUL, FDIV), así que la
;                         última cifra es aproximada. Destruye FA, FB y FR.
; =====================================================================
fpu_fprint:
    MOV pf_x, FA
    SHRI pf_t, pf_x, 63
    JEQI pf_t, 0, pf_pos
    PUTC '-'
pf_pos:
    LOWI pf_x, pf_x, 63               ; |x|
    SHRI pf_e, pf_x, 52
    JNEI pf_e, EXPMAX, pf_finito
    LOWI pf_t, pf_x, 52
    JEQI pf_t, 0, pf_inf
    PRINTS "nan"
    IRET
pf_inf:
    PRINTS "inf"
    IRET
pf_finito:
    SET pf_sci, 0
    JEQI pf_x, 0, pf_ok               ; cero: notación fija
    JLTI pf_e, 1016, pf_cien          ; |x| < 2^-7  -> notación científica
    JLTI pf_e, 1073, pf_ok            ; |x| < 2^50  -> notación fija
pf_cien:
    ; ---- notación científica: llevar |x| a [1, 10) multiplicando o
    ;      dividiendo por 10 (la última cifra mostrada es aproximada)
    SET pf_sci, 1
    SET pf_dexp, 0
    SET pf_dneg, 0
    MOV pf_prs, FPREC
    SET FPREC, 12
pf_mayor:
    MOV FA, pf_x
    SET FB, D_DIEZ
    CALL V_FCMP
    JEQI FR, F_MENOR, pf_menor
    MOV FA, pf_x
    SET FB, D_DIEZ
    CALL V_FDIV
    MOV pf_x, FR
    ADDI pf_dexp, pf_dexp, 1
    JMP pf_mayor
pf_menor:
    MOV FA, pf_x
    SET FB, D_UNO
    CALL V_FCMP
    JNEI FR, F_MENOR, pf_ok
    MOV FA, pf_x
    SET FB, D_DIEZ
    CALL V_FMUL
    MOV pf_x, FR
    ADDI pf_dneg, pf_dneg, 1
    JMP pf_menor
pf_ok:
    ; ---- conversión EXACTA con aritmética entera:  |x| = m / 2^k
    ;      parte entera = m DIV 2^k ; fracción = (m MOD 2^k) / 2^k
    ;      cada cifra decimal: r <- 10 r ; d = r DIV 2^k ; r <- r MOD 2^k
    SET pf_ent, 0
    SET pf_r, 0
    SET pf_k, 1
    JEQI pf_x, 0, pf_dig0             ; cero
    SHRI pf_e, pf_x, 52
    LOWI pf_r, pf_x, 52
    ADDI pf_r, pf_r, HID              ; m (en este rango x siempre es normal)
    RSUBI P2N, 1075, pf_e             ; k = 1075 - e  (3 <= k <= 59)
    CALL V_POW2
    MOV pf_k, P2R                     ; pf_k = 2^k
    DIVM pf_ent, pf_r, pf_k
    MODM pf_r, pf_r, pf_k             ; r < 2^k <= 2^59  ->  10 r < 2^63
pf_dig0:
    SET pf_dig, 0
    SET pf_esc, 1
    MOV pf_i, FPREC
pf_cifra:
    JEQI pf_i, 0, pf_redondeo
    MULI pf_r, pf_r, 10
    DIVM pf_t, pf_r, pf_k
    MODM pf_r, pf_r, pf_k
    MULI pf_dig, pf_dig, 10
    ADDM pf_dig, pf_dig, pf_t
    MULI pf_esc, pf_esc, 10
    SUBI pf_i, pf_i, 1
    JMP pf_cifra
pf_redondeo:                          ; al más cercano, empates al par
    MULI pf_r, pf_r, 2                ; comparar 2r con 2^k
    JLT pf_r, pf_k, pf_imprime
    JGT pf_r, pf_k, pf_sube
    MOV pf_t, pf_dig                  ; empate: ¿la última cifra es impar?
    JNEI FPREC, 0, pf_par
    MOV pf_t, pf_ent
pf_par:
    LOWI pf_t, pf_t, 1
    JEQI pf_t, 0, pf_imprime
pf_sube:
    ADDI pf_dig, pf_dig, 1
    JLT pf_dig, pf_esc, pf_imprime    ; acarreo a la parte entera (0.99..9 -> 1.0)
    SUBM pf_dig, pf_dig, pf_esc
    ADDI pf_ent, pf_ent, 1
pf_imprime:
    MOV PU_X, pf_ent
    SET PU_W, 1
    CALL V_PRINTU
    JEQI FPREC, 0, pf_fin
    PUTC '.'
    MOV PU_X, pf_dig
    MOV PU_W, FPREC
    CALL V_PRINTU
pf_fin:
    JEQI pf_sci, 0, pf_ret
    MOV FPREC, pf_prs
    PUTC 'e'
    JEQI pf_dneg, 0, pf_epos
    PUTC '-'
    IPRINTV pf_dneg
    IRET
pf_epos:
    PUTC '+'
    IPRINTV pf_dexp
pf_ret:
    IRET

; =====================================================================
;  Datos del FPU
; =====================================================================
.VAR FA, FB, FR, FPREC
.VAR P2N, P2R, p2_t
.VAR J_X, J_N, srj_perd
.VAR N_E, N_F, N_M
.VAR R_S, R_E, R_SIG, rp_bits, rp_t, rp_u
.VAR a_s, a_e, a_f, a_m, a_h, a_l
.VAR b_s, b_e, b_f, b_m, b_h, b_l
.VAR add_t, fq_t
.VAR m_hh, m_c1, m_c2, m_mid, m_ll, m_q, m_t, m_u
.VAR d_q, d_r, d_t, d_i
.VAR i2f_t
.VAR PU_X, PU_W, pu_p, pu_k, pu_t, pu_d
.VAR hx_x, hx_p, hx_d
.VAR pf_x, pf_t, pf_e, pf_ent, pf_fr, pf_esc, pf_i, pf_dig
.VAR pf_sci, pf_dexp, pf_dneg, pf_prs, pf_r, pf_k
