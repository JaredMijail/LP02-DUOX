Emulador DUOS. Grupo F

Integrantes: Sara Isabel Ospina Valderrama, Sebastian Steeven Rodríguez Ortiz,
Juan Manuel Cristancho Alvarez, Jared Mijail Ramirez Escalante,
Gonzalo Rodriguez Bohorquez, David Felipe Lancheros Ramirez,
Jorge Andrés Hernández Garcia.

Para iniciar el programar ejecutar el siguiente comando:

python3 main.py

---------------------------------------------------------------------------

# Emulador de FPU IEEE 754 (doble precisión) para la máquina DUOS

La máquina de la Tarea 10 **no se modificó**: `config.py`, `emuladorDuos.py`,
`instrucciones.py`, `cargador.py`, `interfaz.py` y `main.py` son los originales.
Todo lo nuevo está escrito en el ensamblador de la máquina y usa solo su
repertorio de instrucciones.

## Archivos nuevos

| Archivo | Qué es |
|---|---|
| `ensamblador.py` | Ensamblador DUOS: mnemónicos → código de máquina (`.hex`), listado (`.lst`) y símbolos (`.sym`). Macros, etiquetas, `.EQU`, `.WORD`, `.DOUBLE`, `.VAR`, `.INCLUDE`. |
| `ejecutar.py` | Ensambla y corre un `.asm` en el emulador original, silenciando la traza por ciclo. |
| `asm/macros.inc` | Macros (memoria a memoria, desplazamientos, comparaciones, CALL/RET por INT). Se expanden solo a instrucciones nativas. |
| `asm/fpu.asm` | **El emulador del FPU**: FADD, FSUB, FMUL, FDIV, FCMP, FI2F, FF2I, FPRINT, FHEX. |
| `asm/heron.asm` | Parte 2: raíz cuadrada por el método de Herón (Peña, p. 26). |
| `asm/brun.asm` | Parte 3: estimación de la constante de Brun. |
| `asm/demo_fpu.asm` | Demostración del formato y de los casos especiales. |
| `bin/*.hex` | Programas ya ensamblados (sirven con `main.py`). |
| `pruebas/pruebas_fpu.py` | Pruebas diferenciales del FPU contra la aritmética IEEE real. |
| `pruebas/referencia.py` | Herón y Brun en Python; compara bit a bit con la salida de DUOS. |

## Cómo correrlo (Python 3.10+, sin librerías externas)

```bash
python3 ejecutar.py asm/demo_fpu.asm        # formato y casos especiales (< 1 s)
python3 ejecutar.py asm/heron.asm           # método de Herón (< 1 s)
python3 ejecutar.py asm/brun.asm            # constante de Brun hasta 10^5 (~35 s)
python3 ejecutar.py asm/heron.asm --verificar64   # comprueba que TOS/NOS caben en 64 bits

python3 pruebas/pruebas_fpu.py 2000         # pruebas del FPU (~20 s)
python3 pruebas/referencia.py               # Herón y Brun contra Python

# Con la interfaz original de la Tarea 10 (imprime la traza de cada ciclo):
python3 main.py bin/heron.hex               # opción 2 (ejecutar todo) y luego 4 (salida)
```

## Cómo se usa el FPU desde ensamblador

```asm
.INCLUDE "macros.inc"
    FPU_INSTALL              ; instala los vectores de interrupción del FPU
    FDIVV r, uno, tres       ; r <- 1.0 / 3.0   (MOV FA,..; MOV FB,..; CALL V_FDIV; MOV r,FR)
    FPRINTV r                ; 0.333333333333333
    HALT
uno:  .DOUBLE 1.0
tres: .DOUBLE 3.0
.VAR r
.INCLUDE "fpu.asm"
```

Cada servicio del FPU es una rutina a la que se entra con una interrupción de
software (`PUSH n` + `INT`) y de la que se sale con `IRET`, porque la máquina no
tiene CALL/RET. Vectores: 16 FADD, 17 FSUB, 18 FMUL, 19 FDIV, 20 FCMP, 21 FI2F,
22 FF2I, 23 FPRINT, 24 FHEX, 25 PRINTU, 26–29 de uso interno; 2–15, 30 y 31
quedan libres para el programa.

## Observaciones sobre la máquina de la Tarea 10

* `DUP` (0x12) está en `Op` pero no en la tabla de despacho: el ensamblador lo rechaza.
* `POP` avanza 9 bytes, `LOAD`/`STORE` 12 (opcode + dirección de 8 bytes + 3 de relleno).
* `SUB` calcula `NOS - TOS`, pero `DIV` y `MOD` calculan `TOS // NOS` y `TOS % NOS`.
* La aritmética de registros no se recorta a 64 bits; el FPU nunca se apoya en eso.
* Los programas grandes cubren la dirección 0x2000 (buffer de la llamada `INT 1`),
  así que aquí se imprime con `OUT` directamente.
