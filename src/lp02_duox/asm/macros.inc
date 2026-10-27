; =====================================================================
;  macros.inc  -  Macros de la máquina DUOS
;
;  La máquina tiene dos registros de trabajo (TOS y NOS). Estas macros arman
;  un "lenguaje de memoria a memoria" sobre las instrucciones nativas:
;
;    desplazamiento a la izquierda k   =  MUL por 2^k
;    desplazamiento a la derecha  k    =  DIV por 2^k
;    AND con (2^k - 1)                 =  MOD por 2^k
;    a < b  (0 <= a,b < 2^63)          =  (a - b + 2^63) DIV 2^63 == 0
;    CALL n / RET                      =  INT n / IRET (llamada por vector)
;
;  CALL es aquí la llamada por vector: el ISA tiene CALL/RET nativos por
;  dirección, pero la librería se despacha con la tabla de vectores.
;
;  Recordatorio de la semántica nativa (ver docs/ISA_CPU.md):
;    LOAD x  : NOS <- TOS ; TOS <- MEM[x]      PUSH v : NOS <- TOS ; TOS <- v
;    ADD/MUL : TOS <- TOS (+,*) NOS            SUB    : TOS <- NOS - TOS
;    DIV/MOD : TOS <- TOS (//,%) NOS
;  Todas las variables de memoria contienen enteros sin signo de 64 bits.
; =====================================================================

.EQU BIT63, 1<<63
.EQU UNOS64, (1<<64)-1

; ---------------------------------------------------------- movimiento
.MACRO SET d, v            ; d <- v (constante)
    PUSH \v
    STORE \d
.ENDM

.MACRO MOV d, s            ; d <- s
    LOAD \s
    STORE \d
.ENDM

; ---------------------------------------------------------- aritmética
.MACRO ADDM d, a, b        ; d <- a + b
    LOAD \a
    LOAD \b
    ADD
    STORE \d
.ENDM

.MACRO ADDI d, a, v        ; d <- a + v
    LOAD \a
    PUSH \v
    ADD
    STORE \d
.ENDM

.MACRO SUBM d, a, b        ; d <- a - b
    LOAD \a
    LOAD \b
    SUB
    STORE \d
.ENDM

.MACRO SUBI d, a, v        ; d <- a - v
    LOAD \a
    PUSH \v
    SUB
    STORE \d
.ENDM

.MACRO RSUBI d, v, a       ; d <- v - a
    PUSH \v
    LOAD \a
    SUB
    STORE \d
.ENDM

.MACRO MULM d, a, b        ; d <- a * b
    LOAD \a
    LOAD \b
    MUL
    STORE \d
.ENDM

.MACRO MULI d, a, v        ; d <- a * v
    LOAD \a
    PUSH \v
    MUL
    STORE \d
.ENDM

.MACRO DIVM d, a, b        ; d <- a // b
    LOAD \b
    LOAD \a
    DIV
    STORE \d
.ENDM

.MACRO DIVI d, a, v        ; d <- a // v
    PUSH \v
    LOAD \a
    DIV
    STORE \d
.ENDM

.MACRO MODM d, a, b        ; d <- a % b
    LOAD \b
    LOAD \a
    MOD
    STORE \d
.ENDM

.MACRO MODI d, a, v        ; d <- a % v
    PUSH \v
    LOAD \a
    MOD
    STORE \d
.ENDM

; ------------------------------------------------- operaciones de bits
.MACRO SHLI d, a, k        ; d <- a << k        (MUL por 2^k)
    MULI \d, \a, (1<<(\k))
.ENDM

.MACRO SHRI d, a, k        ; d <- a >> k        (DIV por 2^k)
    DIVI \d, \a, (1<<(\k))
.ENDM

.MACRO LOWI d, a, k        ; d <- a AND (2^k-1) (MOD por 2^k)
    MODI \d, \a, (1<<(\k))
.ENDM

.MACRO BITI d, a, k        ; d <- bit k de a
    PUSH (1<<(\k))
    LOAD \a
    DIV
    PUSH 2
    SWAP
    MOD
    STORE \d
.ENDM

.MACRO SETLSB d            ; d <- d OR 1
    DIVI \d, \d, 2
    MULI \d, \d, 2
    ADDI \d, \d, 1
.ENDM

; ------------------------------------------------------------ saltos
.MACRO JEQ a, b, L         ; si a == b ir a L
    LOAD \a
    LOAD \b
    SUB
    JZ \L
.ENDM

.MACRO JEQI a, v, L        ; si a == v ir a L
    LOAD \a
    PUSH \v
    SUB
    JZ \L
.ENDM

.MACRO JNE a, b, L         ; si a != b ir a L
    LOAD \a
    LOAD \b
    SUB
    JZ %%no
    JMP \L
%%no:
.ENDM

.MACRO JNEI a, v, L        ; si a != v ir a L
    LOAD \a
    PUSH \v
    SUB
    JZ %%no
    JMP \L
%%no:
.ENDM

; Comparaciones sin signo para 0 <= a, b < 2^63:
;   t = (a - b + 2^63) DIV 2^63   vale 1 si a >= b y 0 si a < b
.MACRO _CMPT                ; TOS = a - b  ->  TOS = t ; Z = (t == 0)
    PUSH BIT63
    ADD
    PUSH BIT63
    SWAP
    DIV
    PUSH 0
    SUB
.ENDM

.MACRO _CMPT1               ; igual que _CMPT pero Z = (t == 1)
    PUSH BIT63
    ADD
    PUSH BIT63
    SWAP
    DIV
    PUSH 1
    SUB
.ENDM

.MACRO JLT a, b, L         ; si a < b ir a L
    LOAD \a
    LOAD \b
    SUB
    _CMPT
    JZ \L
.ENDM

.MACRO JLTI a, v, L        ; si a < v ir a L
    LOAD \a
    PUSH \v
    SUB
    _CMPT
    JZ \L
.ENDM

.MACRO JGE a, b, L         ; si a >= b ir a L
    LOAD \a
    LOAD \b
    SUB
    _CMPT1
    JZ \L
.ENDM

.MACRO JGEI a, v, L        ; si a >= v ir a L
    LOAD \a
    PUSH \v
    SUB
    _CMPT1
    JZ \L
.ENDM

.MACRO JGT a, b, L         ; si a > b ir a L
    JLT \b, \a, \L
.ENDM

.MACRO JLE a, b, L         ; si a <= b ir a L
    JGE \b, \a, \L
.ENDM

.MACRO JGTI a, v, L        ; si a > v ir a L
    JGEI \a, (\v)+1, \L
.ENDM

.MACRO JLEI a, v, L        ; si a <= v ir a L
    JLTI \a, (\v)+1, \L
.ENDM

; ------------------------------------------------------ subrutinas
.MACRO CALL n              ; llamada a subrutina por interrupción de software
    PUSH \n
    INT
.ENDM

.MACRO VECTOR n, rutina    ; instala MEM[n*8] <- dirección de la rutina
    PUSH \rutina
    STORE (\n)*8
.ENDM

.MACRO NL                  ; salto de línea
    PUTC 10
.ENDM

; ================================================== interfaz del FPU
; Vectores de interrupción (0 = teclado y 1 = print los usa el mini-SO)
.EQU V_FADD,   16
.EQU V_FSUB,   17
.EQU V_FMUL,   18
.EQU V_FDIV,   19
.EQU V_FCMP,   20
.EQU V_FI2F,   21
.EQU V_FF2I,   22
.EQU V_FPRINT, 23
.EQU V_FHEX,   24
.EQU V_PRINTU, 25
.EQU V_NRPACK, 26
.EQU V_SRJAM,  27
.EQU V_POW2,   28
.EQU V_NORM53, 29
; 30 y 31 quedan libres para las subrutinas del programa de usuario

.EQU F_IGUAL, 0            ; resultados de FCMP
.EQU F_MENOR, 1
.EQU F_MAYOR, 2
.EQU F_NOORD, 3

.MACRO FPU_INSTALL         ; instala los vectores del FPU (primer paso del programa)
    VECTOR V_FADD,   fpu_fadd
    VECTOR V_FSUB,   fpu_fsub
    VECTOR V_FMUL,   fpu_fmul
    VECTOR V_FDIV,   fpu_fdiv
    VECTOR V_FCMP,   fpu_fcmp
    VECTOR V_FI2F,   fpu_fi2f
    VECTOR V_FF2I,   fpu_ff2i
    VECTOR V_FPRINT, fpu_fprint
    VECTOR V_FHEX,   fpu_fhex
    VECTOR V_PRINTU, fpu_printu
    VECTOR V_NRPACK, fpu_nrpack
    VECTOR V_SRJAM,  fpu_srjam
    VECTOR V_POW2,   fpu_pow2
    VECTOR V_NORM53, fpu_norm53
    SET FPREC, 15
.ENDM

; Operaciones de alto nivel: d <- x (op) y   (x, y, d son variables double)
.MACRO FOP vec, d, x, y
    MOV FA, \x
    MOV FB, \y
    CALL \vec
    MOV \d, FR
.ENDM

.MACRO FADDV d, x, y
    FOP V_FADD, \d, \x, \y
.ENDM

.MACRO FSUBV d, x, y
    FOP V_FSUB, \d, \x, \y
.ENDM

.MACRO FMULV d, x, y
    FOP V_FMUL, \d, \x, \y
.ENDM

.MACRO FDIVV d, x, y
    FOP V_FDIV, \d, \x, \y
.ENDM

.MACRO FCMPV d, x, y       ; d <- 0 (=), 1 (<), 2 (>), 3 (no ordenados)
    FOP V_FCMP, \d, \x, \y
.ENDM

.MACRO I2FV d, i           ; d <- (double) i     (i entero de 64 bits con signo)
    MOV FA, \i
    CALL V_FI2F
    MOV \d, FR
.ENDM

.MACRO F2IV d, x           ; d <- (int64) x      (truncamiento hacia cero)
    MOV FA, \x
    CALL V_FF2I
    MOV \d, FR
.ENDM

.MACRO FPRINTV x           ; imprime x en decimal con FPREC decimales
    MOV FA, \x
    CALL V_FPRINT
.ENDM

.MACRO FHEXV x             ; imprime los 64 bits de x en hexadecimal
    MOV FA, \x
    CALL V_FHEX
.ENDM

.MACRO IPRINTV x           ; imprime el entero sin signo x
    MOV PU_X, \x
    SET PU_W, 1
    CALL V_PRINTU
.ENDM
