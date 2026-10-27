# Mapeo de la librería `mate.inc` a instrucciones nativas DUOS

Librería de 40 instrucciones matemáticas para el preprocesador de la máquina DUOS (Taller 1,
Grupo F). Cada instrucción es una macro `.MACRO/.ENDM` de
[`src/lp02_duox/asm/mate.inc`](../src/lp02_duox/asm/mate.inc). El preprocesador la expande
**solo a instrucciones nativas**: directamente, pasando por las macros de `macros.inc`, o como
llamada (`PUSH n ; INT`) a una subrutina escrita a su vez en instrucciones nativas. Esas
subrutinas son las del FPU de `fpu.asm` o las de la propia librería. La librería no agrega
opcodes: todo se expande al ISA de [`ISA_CPU.md`](ISA_CPU.md).

- Prueba: [`src/lp02_duox/asm/prueba_mate.asm`](../src/lp02_duox/asm/prueba_mate.asm)
  (`py ejecutar.py asm/prueba_mate.asm` → `Correctas: 40 de 40`).
- Los conteos de este documento salen de
  [`src/lp02_duox/pruebas/mapeo_mate.py`](../src/lp02_duox/pruebas/mapeo_mate.py), que expande cada
  macro con el mismo expansor de `ensamblador.py`. Para regenerarlos: `py pruebas/mapeo_mate.py`
  (tablas) o `py pruebas/mapeo_mate.py FABSV IPARV` (listado nativo completo de esas macros).

## 1. Repertorio nativo de referencia

| Mnemónico | Opcode | Bytes | Efecto |
|---|---|---|---|
| HALT | 27 | 1 | detiene el núcleo |
| ADD | 01 | 1 | TOS ← TOS + NOS |
| SUB | 02 | 1 | TOS ← NOS − TOS |
| MUL | 03 | 1 | TOS ← TOS · NOS |
| DIV | 04 | 1 | TOS ← TOS // NOS |
| MOD | 05 | 1 | TOS ← TOS % NOS |
| INT | 54 | 1 | apila PC+1 y PSW.I ; PC ← MEM[TOS·8] |
| IRET | 55 | 1 | desapila PSW.I y PC |
| OUT | 45 | 1 | escribe el carácter TOS & 0xFF |
| PUSH imm | 10 | 9 | NOS ← TOS ; TOS ← imm |
| SWAP | 13 | 1 | intercambia TOS y NOS |
| STORE dir | 15 | 9 | MEM[dir] ← TOS |
| LOAD dir | 14 | 9 | NOS ← TOS ; TOS ← MEM[dir] |
| JZ dir | 21 | 9 | si Z: PC ← dir |
| JMP dir | 20 | 9 | PC ← dir |

El ISA completo (48 instrucciones) está en [`ISA_CPU.md`](ISA_CPU.md).

Las expansiones de las 40 macros usan 12 de estas instrucciones: ADD, SUB, MUL, DIV, MOD, INT,
PUSH, SWAP, STORE, LOAD, JZ y JMP. Las subrutinas de la librería agregan IRET. HALT y OUT
no aparecen (OUT sí está dentro de los servicios de impresión del FPU), y tampoco EI, DI, LDI ni POP.

## 2. Organización y convenciones

- **Forma:** `NOMBRE d, a[, b ...]`, memoria a memoria y con el destino primero, igual que `ADDM d, a, b`.
  Prefijo `I` = entero, `F` = double IEEE 754; sufijo `V` = operandos en variables (como `FADDV`).
- **Enteros:** 64 bits con signo, en complemento a dos. `STORE` trunca a 64 bits, así que `SET x, -7`
  deja 2^64 − 7 en memoria. Las comparaciones `JLT/JGE` de `macros.inc` solo sirven para
  0 ≤ a, b < 2^63; para comparar con signo se usa el auxiliar `_JSLT`.
- **Flotantes:** la variable guarda el patrón binary64. Las operaciones aritméticas usan `FADDV`,
  `FSUBV`, `FMULV`, `FDIVV`, `FCMPV`, `I2FV` y `F2IV` (servicios del FPU). `FABSV`, `FNEGV` y `FTRUNCV`
  trabajan directamente sobre los bits con aritmética entera.
- **Alias:** el destino puede ser un operando (`IABSV x, x`). Cada macro calcula en temporales
  propios `mt_<macro>_*` y escribe `d` al final.
- **En línea o subrutina.** Las macros cortas se expanden completas donde se usan. Los algoritmos
  que ocuparían más de 1 KB por uso son subrutinas que existen una sola vez en el programa:
  raíz, exp, ln, sen/cos y MCM. La macro pasa los operandos en los "registros" de memoria
  `MT_A` y `MT_B`, llama con `CALL vector` (= `PUSH n ; INT`), la subrutina vuelve con `IRET`
  y la macro recoge `MT_R`. Es la misma convención de `FADDV` con `FA`, `FB`, `FR`.
  FPOTV, FTANV y FHIPOTV quedan pequeñas porque llaman a esas subrutinas.

### 2.1 Vectores de interrupción

| Vector | Dirección MEM[n·8] | Dueño | Uso |
|---|---|---|---|
| 0, 1 | 0x00, 0x08 | mini-SO | teclado, print |
| 2 | 0x10 | mate.inc | `V_MSQRT` → `mt_rut_sqrt` |
| 3 | 0x18 | mate.inc | `V_MEXP` → `mt_rut_exp` |
| 4 | 0x20 | mate.inc | `V_MLN` → `mt_rut_ln` |
| 5 | 0x28 | mate.inc | `V_MSIN` → `mt_rut_sin` |
| 6 | 0x30 | mate.inc | `V_MCOS` → `mt_rut_cos` |
| 7 | 0x38 | mate.inc | `V_MMCM` → `mt_rut_mcm` |
| **8 – 15** | 0x40 – 0x78 | **libres** | para el programa de usuario |
| 16 – 29 | 0x80 – 0xE8 | fpu.asm | `V_FADD` … `V_NORM53` |
| **30, 31** | 0xF0, 0xF8 | **libres** | para el programa de usuario (`prueba_mate.asm` usa 30 y 31) |

### 2.2 Instalación y uso en un programa

```asm
.INCLUDE "mate.inc"      ; al inicio (incluye macros.inc); no emite código ni datos
inicio:
    MATE_INSTALL         ; FPU_INSTALL + vectores 2-7 de la librería
    ...                  ; aquí se usan las 40 instrucciones
    HALT
MATE_RUTINAS             ; UNA vez, después del HALT: subrutinas, constantes y temporales
.INCLUDE "fpu.asm"
```

- `MATE_INSTALL` reemplaza a `FPU_INSTALL`, porque ya lo incluye, y luego hace `VECTOR 2..7`. Tiene que
  ejecutarse antes de la primera instrucción de la librería. Si falta, el vector vale 0, `CALL 2..7`
  salta a la dirección 0 y la máquina se detiene (ahí el primer byte es 0x00 = `HALT`).
- `MATE_RUTINAS` emite código, así que debe quedar en una zona que no se ejecute en secuencia, igual
  que el `.INCLUDE "fpu.asm"`. `mate.inc` no puede emitir nada al incluirse: lo que hubiera al inicio
  se ejecutaría desde 0x1000, y una palabra en cero es `HALT`.

## 3. Las 40 instrucciones

**Instr.** y **Bytes** son el tamaño de una expansión en el punto de uso (los ciclos ejecutan más en
tiempo de ejecución). **INT** es cuántas llamadas a subrutinas (FPU o librería) contiene. La columna de
expansión nativa da cada mnemónico como `opcode/bytes ×veces`. En las macros que llaman a una
subrutina de la librería, el tamaño de esa subrutina está en la §3.3 y se paga una sola vez.

### 3.1 Enteras

| # | Nombre | Operandos | Qué hace | Expansión (un nivel) | Expansión nativa | Instr. / Bytes / INT | Ejemplo |
|---|---|---|---|---|---|---|---|
| 1 | IABSV | d, a | d ← \|a\| | `SHRI` signo; si es 1 `INEGV`, si no `MOV` | PUSH 10/9 ×6, LOAD 14/9 ×6, STORE 15/9 ×5, SUB 02/1 ×3, JZ 21/9 ×2, JMP 20/9 ×2, DIV 04/1 ×1, ADD 01/1 ×1 | 26 / 194 / 0 | `IABSV r, a` ; a=−7 → 7 |
| 2 | INEGV | d, a | d ← −a | `JEQI a,0`; `RSUBI d, UNOS64, a`; `ADDI d, d, 1` (complemento a uno + 1) | PUSH 10/9 ×4, LOAD 14/9 ×3, STORE 15/9 ×3, SUB 02/1 ×2, JZ 21/9 ×1, ADD 01/1 ×1, JMP 20/9 ×1 | 15 / 111 / 0 | `INEGV x, x` ; 12345 → −12345 |
| 3 | ISGNV | d, a | d ← −1, 0 ó 1 | `SHRI` signo, `JEQI a,0`, `SET` | PUSH 10/9 ×6, STORE 15/9 ×4, LOAD 14/9 ×3, SUB 02/1 ×2, JZ 21/9 ×2, JMP 20/9 ×2, DIV 04/1 ×1 | 20 / 156 / 0 | −42 → −1 |
| 4 | IMINV | d, a, b | mínimo con signo | `_JSLT b, a`; `MOV` | LOAD 14/9 ×11, STORE 15/9 ×6, PUSH 10/9 ×5, SUB 02/1 ×4, DIV 04/1 ×3, JZ 21/9 ×3, JMP 20/9 ×2 | 34 / 250 / 0 | (−5, 3) → −5 |
| 5 | IMAXV | d, a, b | máximo con signo | `_JSLT a, b`; `MOV` | LOAD 14/9 ×11, STORE 15/9 ×6, PUSH 10/9 ×5, SUB 02/1 ×4, DIV 04/1 ×3, JZ 21/9 ×3, JMP 20/9 ×2 | 34 / 250 / 0 | (−5, 3) → 3 |
| 6 | ICLAMPV | d, a, lo, hi | limita a al rango [lo, hi] | `IMAXV t, a, lo`; `IMINV d, t, hi` | LOAD 14/9 ×22, STORE 15/9 ×12, PUSH 10/9 ×10, SUB 02/1 ×8, DIV 04/1 ×6, JZ 21/9 ×6, JMP 20/9 ×4 | 68 / 500 / 0 | (15, −10, 10) → 10 |
| 7 | IPOTV | d, b, e | d ← b^e (e ≥ 0) | elevar al cuadrado y multiplicar sobre \|b\| (`LOWI`, `MULM`, `SHRI`); `INEGV` si b<0 y e impar | LOAD 14/9 ×25, PUSH 10/9 ×19, STORE 15/9 ×18, SUB 02/1 ×9, JZ 21/9 ×7, JMP 20/9 ×5, DIV 04/1 ×3, MUL 03/1 ×3, MOD 05/1 ×2, ADD 01/1 ×2 | 93 / 685 / 0 | (−3, 5) → −243 |
| 8 | IFACTV | d, n | d ← n! (0 ≤ n ≤ 20) | ciclo `MULM r, r, i` ; `SUBI i, i, 1` mientras i ≥ 2 | PUSH 10/9 ×6, LOAD 14/9 ×6, STORE 15/9 ×5, SUB 02/1 ×3, ADD 01/1 ×1, SWAP 13/1 ×1, DIV 04/1 ×1, JZ 21/9 ×1, MUL 03/1 ×1, JMP 20/9 ×1 | 26 / 178 / 0 | 15 → 1307674368000 |
| 9 | IMCDV | d, a, b | MCD(\|a\|, \|b\|) | `IABSV` ×2; Euclides: `MODM t, a, b`, a ← b, b ← t | LOAD 14/9 ×18, STORE 15/9 ×14, PUSH 10/9 ×13, SUB 02/1 ×7, JZ 21/9 ×5, JMP 20/9 ×5, DIV 04/1 ×2, ADD 01/1 ×2, MOD 05/1 ×1 | 67 / 507 / 0 | (84, −36) → 12 |
| 10 | IMCMV | d, a, b | MCM(\|a\|, \|b\|); 0 si alguno es 0 | `_MOP2 V_MMCM, d, a, b` → subrutina `mt_rut_mcm`: `IABSV` ×2, `IMCDV g`, `DIVM`, `MULM` | LOAD 14/9 ×3, STORE 15/9 ×3, PUSH 10/9 ×1, INT 54/1 ×1 | 8 / 64 / 1 | (21, 6) → 42 |
| 11 | IRAIZV | d, a | ⌊√a⌋ (a ≥ 0) | Newton entero: y = (x + a/x)/2 hasta que y ≥ x (`DIVM`, `ADDM`, `SHRI`, `JGE`) | LOAD 14/9 ×14, PUSH 10/9 ×10, STORE 15/9 ×9, DIV 04/1 ×5, SUB 02/1 ×4, ADD 01/1 ×4, SWAP 13/1 ×2, JZ 21/9 ×2, JMP 20/9 ×1 | 51 / 339 / 0 | 99999999 → 9999 |
| 12 | IPARV | d, a | 1 si a es par, 0 si es impar | `LOWI t, a, 1`; `RSUBI d, 1, t` | PUSH 10/9 ×2, LOAD 14/9 ×2, STORE 15/9 ×2, MOD 05/1 ×1, SUB 02/1 ×1 | 8 / 56 / 0 | −7 → 0 |
| 13 | IPROMV | d, a, b | (a + b)/2 truncado hacia cero | `ADDM s`; si s<0: `INEGV`, `SHRI 1`, `INEGV`; si no `SHRI 1` | LOAD 14/9 ×12, PUSH 10/9 ×12, STORE 15/9 ×10, SUB 02/1 ×5, ADD 01/1 ×3, DIV 04/1 ×3, JZ 21/9 ×3, JMP 20/9 ×3 | 51 / 371 / 0 | (−7, 2) → −2 |
| 14 | IDIVSV | d, a, b | a / b con signo, truncado (como en C); b = 0 → 0 | `IABSV` ×2; `DIVM`; `INEGV` si los signos difieren | LOAD 14/9 ×23, PUSH 10/9 ×20, STORE 15/9 ×18, SUB 02/1 ×10, JZ 21/9 ×7, DIV 04/1 ×5, JMP 20/9 ×5, ADD 01/1 ×3 | 91 / 675 / 0 | (−17, 5) → −3 |
| 15 | IMODSV | d, a, b | residuo con el signo de a; b = 0 → 0 | `IABSV` ×2; `MODM`; `INEGV` si a < 0 | LOAD 14/9 ×21, PUSH 10/9 ×20, STORE 15/9 ×17, SUB 02/1 ×10, JZ 21/9 ×7, JMP 20/9 ×5, DIV 04/1 ×3, ADD 01/1 ×3, MOD 05/1 ×1 | 87 / 647 / 0 | (−17, 5) → −2 |
| 16 | IDISTV | d, a, b | \|a − b\| | `SUBM t, a, b`; `IABSV d, t` | LOAD 14/9 ×8, STORE 15/9 ×6, PUSH 10/9 ×6, SUB 02/1 ×4, JZ 21/9 ×2, JMP 20/9 ×2, DIV 04/1 ×1, ADD 01/1 ×1 | 30 / 222 / 0 | (−8, 5) → 13 |
| 17 | IPRIMOV | d, n | 1 si n es primo, 0 si no | división por tentativa: i = 2, 3, … mientras i·i ≤ n (`MULM`, `JGT`, `MODM`) | PUSH 10/9 ×14, LOAD 14/9 ×12, STORE 15/9 ×8, SUB 02/1 ×6, JZ 21/9 ×4, DIV 04/1 ×3, ADD 01/1 ×3, SWAP 13/1 ×2, MUL 03/1 ×1, MOD 05/1 ×1, JMP 20/9 ×1 | 55 / 367 / 0 | 97 → 1 |
| 18 | ICOMBV | d, n, k | C(n, k) (n, k ≥ 0) | k ← min(k, n−k); r ← r·(n−k+i)/i para i = 1..k (`MULM`, `DIVM` exacta) | LOAD 14/9 ×19, STORE 15/9 ×11, PUSH 10/9 ×10, SUB 02/1 ×7, ADD 01/1 ×4, DIV 04/1 ×3, JZ 21/9 ×3, SWAP 13/1 ×2, MUL 03/1 ×1, JMP 20/9 ×1 | 61 / 413 / 0 | (10, 3) → 120 |
| 19 | ILOG2V | d, a | ⌊log₂ a⌋; −1 si a ≤ 0 | dividir entre 2 (`SHRI 1`) y contar mientras a ≥ 2 | PUSH 10/9 ×11, LOAD 14/9 ×8, STORE 15/9 ×7, SUB 02/1 ×4, DIV 04/1 ×3, JZ 21/9 ×3, ADD 01/1 ×2, SWAP 13/1 ×1, JMP 20/9 ×1 | 40 / 280 / 0 | 1000 → 9 |
| 20 | IFIBV | d, n | F(n), con F0 = 0 y F1 = 1 (n ≤ 92) | ciclo `ADDM t, a, b`; a ← b; b ← t | STORE 15/9 ×8, LOAD 14/9 ×8, PUSH 10/9 ×4, SUB 02/1 ×2, JZ 21/9 ×1, ADD 01/1 ×1, JMP 20/9 ×1 | 25 / 201 / 0 | 50 → 12586269025 |

### 3.2 Punto flotante (FPU IEEE 754 doble precisión)

| # | Nombre | Operandos | Qué hace | Expansión (un nivel) | Expansión nativa | Instr. / Bytes / INT | Ejemplo |
|---|---|---|---|---|---|---|---|
| 21 | FABSV | d, x | \|x\| | `LOWI d, x, 63` (apaga el bit de signo) | PUSH 10/9 ×1, LOAD 14/9 ×1, MOD 05/1 ×1, STORE 15/9 ×1 | 4 / 28 / 0 | −2.5 → 2.5 |
| 22 | FNEGV | d, x | −x | d = (x mod 2^63) + (1 − signo)·2^63 (`SHRI`, `LOWI`, `RSUBI`, `SHLI`, `ADDM`) | LOAD 14/9 ×6, STORE 15/9 ×5, PUSH 10/9 ×4, DIV 04/1 ×1, MOD 05/1 ×1, SUB 02/1 ×1, MUL 03/1 ×1, ADD 01/1 ×1 | 20 / 140 / 0 | 3.75 → −3.75 |
| 23 | FSQRV | d, x | x² | `FMULV d, x, x` | LOAD 14/9 ×3, STORE 15/9 ×3, PUSH 10/9 ×1, INT 54/1 ×1 | 8 / 64 / 1 | −1.5 → 2.25 |
| 24 | FSQRTV | d, x | √x (Herón) | `_MOP1 V_MSQRT, d, x` → subrutina `mt_rut_sqrt` (§3.3) | LOAD 14/9 ×2, STORE 15/9 ×2, PUSH 10/9 ×1, INT 54/1 ×1 | 6 / 46 / 1 | 2 → 1.414213562373095 |
| 25 | FPOTIV | d, x, n | xⁿ, n entero con signo | `IABSV e, n`; elevar al cuadrado y multiplicar con `FMULV`; si n < 0, `FDIVV 1/r` | LOAD 14/9 ×25, STORE 15/9 ×20, PUSH 10/9 ×16, SUB 02/1 ×7, JZ 21/9 ×6, DIV 04/1 ×3, JMP 20/9 ×3, INT 54/1 ×3, ADD 01/1 ×1, MOD 05/1 ×1 | 85 / 645 / 3 | (1.5, −3) → 0.296296… |
| 26 | FMINV | d, x, y | mínimo (con NaN devuelve x) | `FCMPV c, x, y`; si c = MAYOR toma y | LOAD 14/9 ×7, STORE 15/9 ×6, PUSH 10/9 ×2, INT 54/1 ×1, SUB 02/1 ×1, JZ 21/9 ×1, JMP 20/9 ×1 | 19 / 155 / 1 | (2.5, −1) → −1 |
| 27 | FMAXV | d, x, y | máximo (con NaN devuelve x) | `FCMPV c, x, y`; si c = MENOR toma y | LOAD 14/9 ×7, STORE 15/9 ×6, PUSH 10/9 ×2, INT 54/1 ×1, SUB 02/1 ×1, JZ 21/9 ×1, JMP 20/9 ×1 | 19 / 155 / 1 | (2.5, −1) → 2.5 |
| 28 | FRECV | d, x | 1/x | `FDIVV d, MT_UNO, x` | LOAD 14/9 ×3, STORE 15/9 ×3, PUSH 10/9 ×1, INT 54/1 ×1 | 8 / 64 / 1 | 8 → 0.125 |
| 29 | FEXPV | d, x | eˣ | `_MOP1 V_MEXP, d, x` → subrutina `mt_rut_exp` (§3.3) | LOAD 14/9 ×2, STORE 15/9 ×2, PUSH 10/9 ×1, INT 54/1 ×1 | 6 / 46 / 1 | 1 → 2.718281828459045 |
| 30 | FLNV | d, x | ln x | `_MOP1 V_MLN, d, x` → subrutina `mt_rut_ln` (§3.3) | LOAD 14/9 ×2, STORE 15/9 ×2, PUSH 10/9 ×1, INT 54/1 ×1 | 6 / 46 / 1 | 10 → 2.302585092994046 |
| 31 | FPOTV | d, x, y | xʸ (x > 0) | `FLNV l, x` (subrutina); `FMULV l, l, y`; `FEXPV d, l` (subrutina) | LOAD 14/9 ×7, STORE 15/9 ×7, PUSH 10/9 ×3, INT 54/1 ×3 | 20 / 156 / 3 | (9, 0.5) → 3 |
| 32 | FSINV | d, x | sen x | `_MOP1 V_MSIN, d, x` → subrutina `mt_rut_sin` (§3.3) | LOAD 14/9 ×2, STORE 15/9 ×2, PUSH 10/9 ×1, INT 54/1 ×1 | 6 / 46 / 1 | 10 → −0.544021110889370 |
| 33 | FCOSV | d, x | cos x | `_MOP1 V_MCOS, d, x` → subrutina `mt_rut_cos` (§3.3) | LOAD 14/9 ×2, STORE 15/9 ×2, PUSH 10/9 ×1, INT 54/1 ×1 | 6 / 46 / 1 | 1 → 0.540302305868140 |
| 34 | FTANV | d, x | tan x | `FSINV s, x`; `FCOSV c, x` (subrutinas); `FDIVV d, s, c` | LOAD 14/9 ×7, STORE 15/9 ×7, PUSH 10/9 ×3, INT 54/1 ×3 | 20 / 156 / 3 | 0.5 → 0.546302489843790 |
| 35 | FPROMV | d, x, y | (x + y)/2 | `FADDV t, x, y`; `FMULV d, t, ½` | LOAD 14/9 ×6, STORE 15/9 ×6, PUSH 10/9 ×2, INT 54/1 ×2 | 16 / 128 / 2 | (1.5, 4) → 2.75 |
| 36 | FHIPOTV | d, x, y | √(x² + y²) | `FSQRV` ×2; `FADDV`; `FSQRTV` (subrutina) | LOAD 14/9 ×11, STORE 15/9 ×11, PUSH 10/9 ×4, INT 54/1 ×4 | 30 / 238 / 4 | (3, 4) → 5 |
| 37 | FCLAMPV | d, x, lo, hi | limita x al rango [lo, hi] | `FMAXV t, x, lo`; `FMINV d, t, hi` | LOAD 14/9 ×14, STORE 15/9 ×12, PUSH 10/9 ×4, INT 54/1 ×2, SUB 02/1 ×2, JZ 21/9 ×2, JMP 20/9 ×2 | 38 / 310 / 2 | (7.5, 0, 5) → 5 |
| 38 | FSGNV | d, x | −1.0, 1.0, o x si es ±0 o NaN | `FCMPV c, x, 0`; `MOV` de MT_MENOS1 / MT_UNO / x | LOAD 14/9 ×9, STORE 15/9 ×7, PUSH 10/9 ×3, SUB 02/1 ×2, JZ 21/9 ×2, JMP 20/9 ×2, INT 54/1 ×1 | 26 / 210 / 1 | −0.001 → −1 |
| 39 | FTRUNCV | d, x | parte entera hacia cero (double) | solo aritmética entera: e = campo exponente; e ≥ 1075 → x; e < 1023 → ±0; si no, k = 1075 − e, `CALL V_POW2` y d = (x // 2^k)·2^k | PUSH 10/9 ×14, LOAD 14/9 ×13, STORE 15/9 ×9, DIV 04/1 ×5, SUB 02/1 ×5, ADD 01/1 ×2, SWAP 13/1 ×2, JZ 21/9 ×2, MUL 03/1 ×2, MOD 05/1 ×1, JMP 20/9 ×1, INT 54/1 ×1 | 57 / 369 / 1 | −3.75 → −3 |
| 40 | FFLOORV | d, x | ⌊x⌋ (double) | `FTRUNCV t, x`; si x < 0 y t ≠ x: `FSUBV t, t, 1` | LOAD 14/9 ×21, PUSH 10/9 ×17, STORE 15/9 ×14, SUB 02/1 ×7, DIV 04/1 ×6, JZ 21/9 ×4, ADD 01/1 ×2, SWAP 13/1 ×2, MUL 03/1 ×2, INT 54/1 ×2, MOD 05/1 ×1, JMP 20/9 ×1 | 79 / 535 / 2 | −3.25 → −4 |

Una expansión de cada una de las 40 suma 10 049 bytes.

### 3.3 Subrutinas de la librería (emitidas una vez por `MATE_RUTINAS`)

| Etiqueta | Vector | Instr. | Bytes | Algoritmo |
|---|---|---|---|---|
| `mt_rut_sqrt` | 2 `V_MSQRT` | 112 | 776 | Herón. ±0, +inf y NaN se devuelven igual; x < 0 → NaN. Semilla `(bits>>1) + 0x1FF8…` (divide el exponente entre 2); ciclo `FDIVV`, `FADDV`, `FMULV ½` hasta que deja de decrecer (criterio de `heron.asm`, máx. 60) |
| `mt_rut_exp` | 3 `V_MEXP` | 154 | 1 194 | NaN pasa; \|x\| ≥ 710 → +inf / 0. a = \|x\| se divide entre 2 k veces hasta a ≤ ½; Taylor t ← t·a/n hasta que la suma no cambia; se eleva al cuadrado k veces; x < 0 → 1/eᵃ |
| `mt_rut_ln` | 4 `V_MLN` | 201 | 1 537 | ±0 → −inf, x < 0 → NaN, inf/NaN pasan; subnormal: ·2^52. E = e − 1023 y m = 1.f (con los bits); si m > √2: m/2, E+1. t = (m−1)/(m+1); s = t + t³/3 + t⁵/5 + …; resultado `I2FV(E)`·ln2 + 2s |
| `mt_rut_sin` / `mt_rut_cos` | 5 `V_MSIN`, 6 `V_MCOS` | 193 | 1 497 | código compartido (como `fpu_fsub`/`fpu_fadd`): inf/NaN → NaN; `_FRED2PI` reduce a [−π, π]; serie t ← −t·r²/((n+1)(n+2)) empezando en t = r, n = 1 (seno) o t = 1, n = 0 (coseno), hasta que la suma no cambia |
| `mt_rut_mcm` | 7 `V_MMCM` | 138 | 1 026 | \|a\| / MCD(\|a\|, \|b\|) · \|b\|; 0 si alguno es 0 |
| `MT_CERO` … | — | — | 1 000 | constantes double (`MT_UNO`, `MT_PI`, `MT_LN2`, …), `MT_A/MT_B/MT_R` y temporales `.VAR` |
| `MATE_INSTALL` | — | 42 | 378 | `FPU_INSTALL` + `VECTOR 2..7` (va en el código de inicio) |

**Costo fijo de la librería por programa: 7 408 bytes** (`MATE_RUTINAS` + `MATE_INSTALL`), sin contar
los ~14 KB de `fpu.asm`. Ese costo se paga aunque el programa no use las subrutinas.

### 3.4 Auxiliares (no cuentan entre las 40)

| Nombre | Operandos | Qué hace |
|---|---|---|
| `MATE_INSTALL` | — | instala el FPU y los vectores 2–7 |
| `MATE_RUTINAS` | — | emite subrutinas, constantes y temporales |
| `_MOP1` / `_MOP2` | vec, d, x[, y] | `MOV MT_A, x` [`MOV MT_B, y`] ; `CALL vec` ; `MOV d, MT_R` (como `FOP` del FPU) |
| `_JSLT` | a, b, L | salta a L si a < b con signo: si los signos difieren gana el negativo; si son iguales, a − b no desborda y su bit 63 da la respuesta |
| `_JSGE` | a, b, L | salta a L si a ≥ b con signo |
| `_FRED2PI` | r, x | r ← x − trunc(x/2π)·2π, llevado a [−π, π] (lo usa la subrutina de sen/cos) |
| `ISPRINTV` | x | imprime un entero con signo (`'-'` + `IPRINTV` de la magnitud) |

## 4. Ejemplos de expansión nativa completa

Así queda en la memoria cada una de estas macros. Los nombres `d`, `x`, `a` se reemplazan por
direcciones en el paso 2 del ensamblador. `__m1_cero` es una etiqueta local (`%%cero`).

**21. FABSV d, x**: 4 instrucciones, 28 bytes
```
PUSH (1<<63)    ; 10   9 B   TOS ← 2^63
LOAD x          ; 14   9 B   NOS ← 2^63 ; TOS ← x
MOD             ; 05   1 B   TOS ← x mod 2^63  (sin bit de signo)
STORE d         ; 15   9 B
```

**12. IPARV d, a**: 8 instrucciones, 56 bytes
```
PUSH (1<<1)     ; 10   9 B
LOAD a          ; 14   9 B
MOD             ; 05   1 B   TOS ← a mod 2  (bit 0)
STORE mt_pa_t   ; 15   9 B
PUSH 1          ; 10   9 B
LOAD mt_pa_t    ; 14   9 B
SUB             ; 02   1 B   TOS ← 1 − bit0
STORE d         ; 15   9 B
```

**2. INEGV d, a**: 15 instrucciones, 111 bytes
```
LOAD a          ; 14   9 B
PUSH 0          ; 10   9 B
SUB             ; 02   1 B   Z ← (a = 0)
JZ __m1_cero    ; 21   9 B
PUSH UNOS64     ; 10   9 B
LOAD a          ; 14   9 B
SUB             ; 02   1 B   TOS ← (2^64 − 1) − a   (complemento a uno)
STORE d         ; 15   9 B
LOAD d          ; 14   9 B
PUSH 1          ; 10   9 B
ADD             ; 01   1 B   + 1 → complemento a dos
STORE d         ; 15   9 B
JMP __m1_fin    ; 20   9 B
__m1_cero:
PUSH 0          ; 10   9 B
STORE d         ; 15   9 B
__m1_fin:
```

**23. FSQRV d, x**: llamada a un servicio del FPU (8 instrucciones, 64 bytes)
```
LOAD x          ; 14   9 B
STORE FA        ; 15   9 B
LOAD x          ; 14   9 B
STORE FB        ; 15   9 B
PUSH V_FMUL     ; 10   9 B   vector 18
INT             ; 54   1 B   apila PC+1 y PSW.I ; PC ← MEM[18·8] = fpu_fmul
LOAD FR         ; 14   9 B
STORE d         ; 15   9 B
```

**24. FSQRTV d, x**: llamada a una subrutina de la librería (6 instrucciones, 46 bytes)
```
LOAD x          ; 14   9 B
STORE MT_A      ; 15   9 B
PUSH V_MSQRT    ; 10   9 B   vector 2
INT             ; 54   1 B   PC ← MEM[2·8] = mt_rut_sqrt ; la rutina termina en IRET (55)
LOAD MT_R       ; 14   9 B
STORE d         ; 15   9 B
```

El listado completo de cualquier otra macro se obtiene con `py pruebas/mapeo_mate.py NOMBRE`, y
el del programa de prueba entero (subrutinas incluidas) queda en `bin/prueba_mate.lst` después de
ejecutarlo.

## 5. Limitaciones

- **Desbordamiento entero:** se trunca a 64 bits sin aviso. Rangos útiles: IFACTV n ≤ 20,
  IFIBV n ≤ 92; IPOTV, IMCMV y ICOMBV con resultados < 2^63. INEGV(−2^63) = −2^63.
  Precondiciones sin verificar: IFACTV, ICOMBV y IRAIZV esperan operandos ≥ 0.
- **División entre cero:** la instrucción nativa `DIV` detiene el núcleo con error de hardware; IDIVSV e IMODSV
  devuelven 0 si b = 0.
- **Impresión:** `IPRINTV` / `ISPRINTV` (rutina `PRINTU` del FPU) solo imprimen bien magnitudes < 10^18.
  El valor guardado es correcto; lo que sale mal es el texto impreso.
- **Precisión de exp, ln, sen, cos y potencias reales:** error relativo del orden de 1e−15 (no
  están correctamente redondeadas). FEXPV pierde unos k bits por elevar al cuadrado k veces.
  FPOTIV con |n| grande acumula un error ~|n|·ε (p. ej. 1.0000001^1000000 tiene error relativo de 5.6e−12).
  sen y cos pierden precisión para |x| grandes, porque la reducción usa 2π redondeado, y no sirven
  para |x| ≥ 2^63, donde `F2IV` devuelve el valor indefinido. FEXPV devuelve 0 para x ≤ −710 aunque el
  resultado exacto sería subnormal.
- **Subrutinas no reentrantes:** usan temporales fijos en memoria, igual que el FPU. Una rutina de
  interrupción que interrumpa una llamada a la librería no puede volver a llamar a la misma subrutina.
  Hoy la ISR de teclado del mini-SO es solo `IRET`, así que no hay conflicto.
- **`--verificar64`:** en `JEQ` sobre patrones con el bit 63 encendido (doubles negativos) y en sumas
  de enteros negativos, TOS queda un momento fuera del rango que vigila `ejecutar.py --verificar64`.
  El resultado guardado es correcto: `STORE` trunca a 64 bits y Z solo depende de si la resta es cero,
  como en una ALU de 64 bits que resta módulo 2^64. El FPU (`fpu.asm`) sí pasa esa verificación.
- **Tamaño:** `prueba_mate.asm` ocupa 41 538 bytes (0x1000–0xB241) y deja 15 806 bytes libres antes
  de la zona de pila (0xF000). Las macros que siguen en línea se repiten en cada uso; la más grande es
  IPOTV, con 545 bytes.
- `MATE_RUTINAS` se invoca una sola vez por programa: una segunda vez repetiría etiquetas.
- La expansión la hace hoy `ensamblador.py` (expresiones regulares en Python), no un analizador
  generado con lex. `mate.inc` fija la sintaxis que el preprocesador del Taller tendrá que aceptar:
  `.MACRO/.ENDM`, parámetros `\p`, etiquetas locales `%%x`, `.INCLUDE`, `.EQU`.

