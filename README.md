# Sistema de Procesamiento del Lenguaje (SPL) — Máquina DUOX / DUOS
## Taller #01 — Compiladores y Lenguajes de Programación
### Grupo F — LP02-DUOX

**Integrantes:**
* Sara Isabel Ospina Valderrama
* Sebastian Steeven Rodríguez Ortiz
* Juan Manuel Cristancho Álvarez
* Jared Mijail Ramírez Escalante
* Gonzalo Rodríguez Bohórquez
* David Felipe Lancheros Ramírez
* Jorge Andrés Hernández García

---

## 1. Descripción General del Proyecto

Este repositorio contiene la implementación integral del **Sistema de Procesamiento del Lenguaje (SPL)** para la computadora académica basada en pila **DUOX / DUOS** (diseñada y construida por el Grupo F en las Tareas #09 y #10).

El objetivo del SPL es proporcionar una cadena completa de herramientas de software que permita traducir programas desde un lenguaje estructurado de alto nivel con Tipos Abstractos de Datos (TDA) o desde lenguaje ensamblador, hasta su ejecución en el procesador virtual con aritmética entera y de punto flotante de 64 bits (IEEE 754).

---

## 2. Arquitectura del Pipeline del SPL (Flujo de Datos)

El procesamiento de un programa en el sistema sigue una cadena secuencial de transformación:

```
[ Código Fuente DUOXC (.dx) ]             [ Código Ensamblador (.asm) ]
             |                                          |
             +--------------------+---------------------+
                                  |
                                  v
                    +---------------------------+
                    |     1. PREPROCESADOR      |  (FLEX + C)
                    |     (preprocesador/)      |
                    |  - Inclusión de archivos  |  #include, .INCLUDE
                    |  - Expansión de macros    |  #define, #undef
                    |  - Compilación condic.    |  #ifdef, #ifndef
                    +---------------------------+
                                  |
                                  v  [Texto limpio / sin directivas]
                    +---------------------------+
                    |  2. COMPILADOR DUOXC      |
                    |  (AnalizadorLexico/)      |
                    |  - Análisis Léxico (FLEX) |  --> Genera 760+ tokens [Taller 1, d]
                    |  - Análisis Sintáctico    |  --> Árbol Sintaxis AST [Taller 2]
                    |  - Generador de Código    |  --> Emite código ensamblador DUOX
                    +---------------------------+
                                  |
                                  v  [Código Ensamblador .asm]
                    +---------------------------+
                    |      3. ENSAMBLADOR       |  (Python / PLY)
                    | (src/lp02_duox/ensambl.)  |  - Resuelve etiquetas (LABEL:)
                    |                           |  - Genera código máquina (.hex)
                    +---------------------------+  - Emite listados (.lst)
                                  |
                                  v  [Código Máquina Hexadecimal .hex]
                    +---------------------------+
                    |  4. ENLAZADOR / CARGADOR  |  (Python)
                    |  (src/lp02_duox/cargador) |  - Relocaliza segmentos
                    |                           |  - Monta binario en RAM (0x1000)
                    +---------------------------+
                                  |
                                  v  [RAM inicializada en 0x1000]
                    +---------------------------+
                    | 5. EMULADOR HARDWARE CPU  |  (Python)
                    | (src/lp02_duox/emulador)  |  - Ciclo Fetch-Decode-Execute
                    |                           |  - Registros: PC, TOS, NOS, SP, BP, PSW
                    |  - FPU IEEE 754 (fpu.asm) |  - 2 Núcleos concurrentes
                    |  - E/S y Red Loopback     |  - 48 Instrucciones nativas
                    +---------------------------+
                                  |
                                  v
                        [ Salida por Consola ]
```

---

## 3. Estructura de Directorios del Repositorio

El proyecto se encuentra modularizado de acuerdo con las especificaciones del Taller:

```
LP02-DUOX/
├── docs/
│   ├── ISA_CPU.md               # Especificación formal del hardware y de las 48 instrucciones nativas
│   └── mapeo_ensamblador.md     # Mapeo de la librería mate.inc (40 operaciones) a nativas y al FPU
│
├── Enunciados/
│   └── Taller 1.md              # Requerimientos formales del proyecto
│
├── preprocesador/               # [PUNTO A] Módulo de Preprocesamiento
│   ├── src/
│   │   ├── pp.l                 # Especificación FLEX del preprocesador
│   │   ├── macros.c             # Tabla de símbolos y expansión de macros
│   │   ├── main.c               # Interfaz de línea de comandos (-o, -I, -D)
│   │   └── pp.h                 # Encabezados y definiciones comunes
│   ├── pruebas/                 # Batería automatizada de pruebas y casos de prueba
│   ├── Makefile                 # Automatización de compilación con GCC + Flex
│   └── README.md                # Documentación del módulo preprocesador
│
├── AnalizadorLexico/            # [PUNTO D] Módulo de Análisis Léxico del Compilador DUOXC
│   ├── duoxc.l                  # Especificación formal en FLEX del analizador léxico
│   ├── test_programa.dx         # Programa de prueba exhaustivo (274 líneas, todos los tokens)
│   ├── Makefile                 # Automatización (make, make test, make clean)
│   └── README.md                # Informe técnico académico con vocabulario y expresiones regulares
│
└── src/lp02_duox/               # [PUNTOS B, C y EMULADOR] Entorno de Ejecución DUOX
    ├── config.py                # Constantes globales: RAM (64KB), pilas, vectores de interrupción
    ├── instrucciones.py         # Mapeo de microinstrucciones y semántica por opcode
    ├── emuladorDuos.py          # Emulador de CPU (dos núcleos, registros, memoria, interrupciones)
    ├── ensamblador.py           # [PUNTO B] Ensamblador DUOX (etiquetas, macros, generación .hex)
    ├── LexerAssembler.py        # Tokenizador del ensamblador con PLY
    ├── cargador.py              # [PUNTO C] Cargador en memoria RAM a partir de 0x1000
    ├── LinkerLoader.py          # Enlazador y cargador modular
    ├── ejecutar.py              # Script integrador: ensambla y ejecuta un .asm en el emulador
    ├── asm/
    │   ├── macros.inc           # Macros estándar (movimiento memoria a memoria, saltos, CALL)
    │   ├── fpu.asm              # Emulador FPU IEEE 754 completo (FADD, FSUB, FMUL, FDIV, FCMP...)
    │   ├── mate.inc             # Librería matemática con 40 funciones (sqrt, exp, ln, sin, cos...)
    │   ├── heron.asm            # Algoritmo de raíz cuadrada de Herón sobre el FPU
    │   ├── brun.asm             # Estimación de la constante de Brun (primos gemelos y FPU)
    │   └── demo_fpu.asm         # Demostración interactiva de operaciones flotantes
    ├── bin/                     # Binarios pre-ensamblados en formato hexadecimal (.hex)
    └── pruebas/                 # Pruebas unitarias de la ISA, del FPU y de equivalencia con Python
```

---

## 4. Descripción de los Componentes (Taller #01)

### 4.1 Preprocesador (`preprocesador/`) — Inciso a
* **Herramientas:** FLEX + Lenguaje C (C99).
* **Propósito:** Primer filtro de la cadena de compilación. Resuelve directivas textuales ancladas a inicio de línea:
  * Inclusión de archivos: `#include "archivo"` o `.INCLUDE "archivo"`.
  * Definición y sustitución de macros de objeto y con parámetros: `#define SUMA(x, y) ((x) + (y))`.
  * Compilación condicional anidable: `#ifdef`, `#ifndef`, `#else`, `#endif`.
  * Eliminación de directivas e inserción limpia de texto para el siguiente módulo.

### 4.2 Analizador Léxico del Compilador (`AnalizadorLexico/`) — Inciso d
* **Herramientas:** FLEX + Lenguaje C (C99).
* **Propósito:** Puerta de entrada del compilador para el lenguaje estructurado de alto nivel **DUOXC**.
* **Capacidades Léxicas:**
  * **35 Palabras Reservadas:** Control de flujo (`if-elif-else-fi`, `while-do-done`, `for-in`), tipos de datos (`int`, `float`, `char`, `bool`, `string`, `void`, `struct`, `array`, `matrix`), funciones (`func`, `proc`, `interrupt`), gestión de memoria (`new`, `free`, `sizeof`) y control de CPU (`asm`, `halt`).
  * **Literales Multibase:** Decimales (`42`), hexadecimales (`0x1000`), binarios (`0b1010`), flotantes estándar y científicos (`3.14`, `2.5e-10`), caracteres con escape (`'\n'`, `'\x41'`) y cadenas.
  * **Operadores:** Aritméticos con potencia (`+`, `-`, `*`, `/`, `%`, `**`), relacionales, lógicos en cortocircuito (`&&`, `||`, `!`), operaciones a nivel de bits (`&`, `|`, `^`, `~`, `<<`, `>>`) y asignación compuesta (`+=`, `-=`, etc.).
  * **48 Mnemónicos Inline de DUOX:** Permite insertar microinstrucciones de hardware en bloques `asm { @asm_LOAD_IMM ... }`.
  * **Compatibilidad Futura:** Códigos numéricos de tokens iniciados en `258` para engranar de forma directa con el analizador sintáctico de Bison/Yacc en el Taller #02.

### 4.3 Ensamblador (`src/lp02_duox/ensamblador.py`) — Inciso b
* **Propósito:** Traduce programas escritos en lenguaje ensamblador con mnemónicos hacia las palabras binarias/hexadecimales de la máquina DUOX.
* **Capacidades:**
  * Resolución de etiquetas simbólicas a direcciones absolutas en memoria.
  * Expansión de directivas de definición de datos (`.WORD`, `.DOUBLE`, `.VAR`, `.EQU`).
  * Emisión de archivos ejecutables hexadecimales (`.hex`) y listados de ensamble con offsets (`.lst`).

### 4.4 Enlazador y Cargador (`src/lp02_duox/cargador.py` / `LinkerLoader.py`) — Inciso c
* **Propósito:** Toma el código máquina generado y lo sitúa en el espacio de direccionamiento de la RAM emulada.
* **Comportamiento:**
  * Escribe el código en la memoria a partir de `0x1000` (`Global.PROGRAMA_BASE`).
  * Inicializa el puntero de instrucción `PC = 0x1000` y la pila `SP = 0xFFFF`.

### 4.5 Emulador Hardware DUOX (`src/lp02_duox/emuladorDuos.py`)
* **Arquitectura:** Máquina de pila (stack-based) con palabras de 64 bits y memoria direccionable de 64 KB.
* **Registros Principales:**
  * `TOS` (Top of Stack) y `NOS` (Next on Stack): Registros rápidos de trabajo para operaciones aritmético-lógicas.
  * `PC` (Program Counter) y `SP` (Stack Pointer).
  * `BP` (Base Pointer): Registro base para marcos de pila locales (`LOAD_OFF` / `STORE_OFF`).
  * `PSW` (Program Status Word): Banderas de estado `C` (acarreo), `Z` (cero), `N` (negativo), `V` (overflow), `I` (interrupciones), `LOCK` (bus) y `CORE_ID` (núcleo 0 o 1).
* **FPU IEEE 754:** Procesador matemático emulado en software mediante vectores de interrupción (vectores 16 a 29) con soporte para sumas, restas, productos, cocientes, conversiones entero-flotante e impresiones decimales.

---

## 5. Guía Rápida de Compilación y Ejecución

### 5.1 Probar el Analizador Léxico (Inciso d)
```bash
# Entrar a la carpeta del analizador léxico
cd AnalizadorLexico

# Compilar con make
make

# Ejecutar la prueba automática (analiza test_programa.dx)
make test

# Limpiar archivos temporales
make clean
```

### 5.2 Probar el Preprocesador (Inciso a)
```bash
# Entrar a la carpeta del preprocesador
cd preprocesador

# Compilar con make
make

# Ejecutar casos de prueba automatizados
make test
```

### 5.3 Ejecutar Programas Ensamblador en el Emulador DUOX (Incisos b y c)
```bash
# Situarse en la raíz del repositorio
cd src/lp02_duox

# 1. Ejecutar las pruebas completas de la ISA (48 instrucciones)
python3 pruebas/prueba_isa.py

# 2. Ensamblar y correr una demo del FPU
python3 ejecutar.py asm/demo_fpu.asm

# 3. Ensamblar y correr el cálculo de la constante de Brun
python3 ejecutar.py asm/brun.asm

# 4. Probar la librería matemática mate.inc (40 de 40 operaciones correctas)
python3 ejecutar.py asm/prueba_mate.asm
```

---

## 6. Hoja de Ruta hacia el Taller #02

1. **Analizador Sintáctico (Parser Bison):** Creación de `duoxc.y` para procesar el flujo de tokens provisto por `duoxc.l` y validar la gramática libre de contexto (GLC).
2. **Generación del AST:** Construcción del árbol de sintaxis abstracta para representar expresiones, declaraciones de funciones y Tipos Abstractos de Datos.
3. **Generación de Código Intermedio / Ensamblador:** Traducción del AST hacia instrucciones ensamblador DUOX (`.asm`), cerrando el ciclo completo desde el lenguaje de alto nivel hasta la CPU de 64 bits.
