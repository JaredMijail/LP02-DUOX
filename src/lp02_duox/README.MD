Emulador DUOS. Grupo F

Integrantes: Sara Isabel Ospina Valderrama, Sebastian Steeven Rodríguez Ortiz,
Juan Manuel Cristancho Alvarez, Jared Mijail Ramirez Escalante,
Gonzalo Rodriguez Bohorquez, David Felipe Lancheros Ramirez,
Jorge Andrés Hernández Garcia.

Para iniciar el programar ejecutar el siguiente comando:

python3 main.py

---------------------------------------------------------------------------

# Emulador DUOS con FPU IEEE 754 (doble precisión)

La máquina implementa el ISA completo de [`docs/ISA_CPU.md`](../../docs/ISA_CPU.md)
(48 instrucciones, dos núcleos, E/S y NIC). El FPU, la librería `mate.inc` y los
programas de ejemplo están escritos en el ensamblador de la máquina y usan solo
ese repertorio.

## Archivos

| Archivo | Qué es |
|---|---|
| `config.py` | Constantes de la máquina (RAM, pilas, vectores, mapa de memoria). |
| `instrucciones.py` | Enum `Op` y semántica de cada instrucción. |
| `emuladorDuos.py` | Núcleos, memoria, E/S, NIC, interrupciones y ciclo fetch-decode-execute. |
| `ensamblador.py` | Ensamblador DUOS: mnemónicos → código de máquina (`.hex`), listado (`.lst`) y símbolos (`.sym`). Macros, etiquetas, `.EQU`, `.WORD`, `.DOUBLE`, `.VAR`, `.INCLUDE`. |
| `ejecutar.py` | Ensambla y corre un `.asm` en el emulador, silenciando la traza por ciclo. |
| `asm/macros.inc` | Macros (memoria a memoria, desplazamientos, comparaciones, CALL por vector). Se expanden solo a instrucciones nativas. |
| `asm/fpu.asm` | **El emulador del FPU**: FADD, FSUB, FMUL, FDIV, FCMP, FI2F, FF2I, FPRINT, FHEX. |
| `asm/mate.inc` | Librería de 40 instrucciones matemáticas (enteras y de punto flotante). |
| `asm/prueba_mate.asm` | Prueba de las 40 instrucciones de `mate.inc`. |
| `asm/heron.asm` | Parte 2: raíz cuadrada por el método de Herón (Peña, p. 26). |
| `asm/brun.asm` | Parte 3: estimación de la constante de Brun. |
| `asm/demo_fpu.asm` | Demostración del formato y de los casos especiales. |
| `bin/*.hex` | Programas ya ensamblados (sirven con `main.py`). |
| `pruebas/prueba_isa.py` | Una prueba por instrucción y coherencia ISA ↔ emulador ↔ ensamblador ↔ doc. |
| `pruebas/pruebas_fpu.py` | Pruebas diferenciales del FPU contra la aritmética IEEE real. |
| `pruebas/referencia.py` | Herón y Brun en Python; compara bit a bit con la salida de DUOS. |
| `pruebas/mapeo_mate.py` | Mide las expansiones de `mate.inc` (tablas de `docs/mapeo_ensamblador.md`). |

## Cómo correrlo (Python 3.10+, sin librerías externas)

```bash
python3 pruebas/prueba_isa.py               # ISA completo (< 1 s)
python3 ejecutar.py asm/demo_fpu.asm        # formato y casos especiales (< 1 s)
python3 ejecutar.py asm/heron.asm           # método de Herón (< 1 s)
python3 ejecutar.py asm/brun.asm            # constante de Brun hasta 10^5 (~35 s)

python3 pruebas/pruebas_fpu.py 2000         # pruebas del FPU (~20 s)
python3 pruebas/referencia.py               # Herón y Brun contra Python

# Con la interfaz original (imprime la traza de cada ciclo):
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
software (`PUSH n` + `INT`) y de la que se sale con `IRET`, porque la librería se
despacha con la tabla de vectores. Vectores: 16 FADD, 17 FSUB, 18 FMUL, 19 FDIV,
20 FCMP, 21 FI2F, 22 FF2I, 23 FPRINT, 24 FHEX, 25 PRINTU, 26–29 de uso interno;
2–15, 30 y 31 quedan libres para el programa.

## Observaciones sobre la máquina

* Formatos: tipo 0 = 1 byte, tipo 1 = 9 (opcode + operando de 64 bits), tipo 2 = 17
  (`MEM_COPY`). Los saltos usan direcciones absolutas.
* `SUB` calcula `NOS - TOS`, pero `DIV` y `MOD` calculan `TOS // NOS` y `TOS % NOS`.
* `PSW` tiene `C Z N V I LOCK CORE_ID`. `Z`/`N` se actualizan en toda operación
  aritmética o lógica; `C`/`V` solo en `ADD`/`SUB`; las usan `JZ/JNZ/JGT/JLT`.
* Los dos núcleos se turnan un ciclo por vez y `HALT` detiene solo el núcleo actual.
  No hay caché modelada (`CACHE_FLUSH` no hace nada) y el NIC es loopback.
* La aritmética de registros no se recorta a 64 bits (las banderas sí se calculan
  módulo 2^64); el FPU nunca se apoya en eso.
* Los programas grandes cubren la dirección 0x2000 (buffer de la llamada `INT 1`),
  así que aquí se imprime con `OUT` directamente.
