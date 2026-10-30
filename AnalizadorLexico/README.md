# Taller #01: Analizador Léxico para el Lenguaje DUOXC (DX)
## Compilador Orientado a la Arquitectura Basada en Pila DUOX / DUOS (64 bits)

**Asignatura:** Compiladores y Lenguajes de Programación  
**Equipo:** Grupo F - LP02-DUOX  
**Entorno de Construcción:** Linux / WSL2 / GCC & Flex  
**Ubicación del Módulo:** `S:\Tareas Trivino\LP02-DUOX\AnalizadorLexico\`

---

## 1. Introducción y Marco Teórico

El análisis léxico (o *scanning*) constituye la primera fase de la cadena de traducción de un compilador. Su función primordial consiste en transformar el flujo continuo de caracteres del código fuente de alto nivel en una secuencia lineal de unidades léxicas atómicas con significado sintáctico denominadas **tokens** (componentes léxicos), suprimiendo al mismo tiempo elementos no significativos como espacios en blanco, tabulaciones y comentarios.

Cada token identificado transporta:
1. **Tipo de Componente Léxico (Token ID):** Código entero unívoco que clasifica la unidad (e.g., `TOKEN_KW_WHILE`, `TOKEN_LIT_INT`, `TOKEN_ASM_ADD`).
2. **Lexema:** La cadena exacta de caracteres del archivo fuente que satisfizo el patrón definido por la expresión regular correspondiente.
3. **Atributos Contextuales:** Información adicional para el compilador, tales como el número de línea (`yylineno`) para diagnóstico y depuración de errores.

```
                  +----------------------------------------------+
                  |         Código Fuente DUOXC (.dx)            |
                  +----------------------------------------------+
                                          |
                                          v  [Flujo de Caracteres]
                  +----------------------------------------------+
                  |           ANALIZADOR LÉXICO (FLEX)           |
                  |  - Autómata Finito Determinista (AFD)        |
                  |  - Control de líneas atómico (yylineno)      |
                  |  - Supresión de comentarios // y /* ... */   |
                  |  - Detección y reporte de errores léxicos    |
                  +----------------------------------------------+
                                          |
                                          v  [Flujo de Tokens: (ID, Lexema, Línea)]
                  +----------------------------------------------+
                  |            ANALIZADOR SINTÁCTICO             |
                  |          (Bison / Yacc - Taller #02)         |
                  +----------------------------------------------+
                                          |
                                          v
                  +----------------------------------------------+
                  |     GENERADOR DE CÓDIGO DUOX (64 bits)       |
                  |     - Código máquina para máquina DUOX       |
                  |     - Instrucciones nativas + FPU IEEE 754   |
                  +----------------------------------------------+
```

Este proyecto implementa el analizador léxico para el lenguaje **DUOXC** (abreviado **DX**), un lenguaje de programación imperativo estructurado con soporte de Tipos Abstractos de Datos (ADTs), arreglos, matrices, punto flotante IEEE 754 de 64 bits y directivas de control de hardware de bajo nivel para la máquina de pila **DUOX / DUOS**.

---

## 2. Arquitectura de la Máquina DUOX y Conexión con DUOXC

El diseño léxico de DUOXC está estrechamente vinculado con las características del computador **DUOX** (documentado en `docs/ISA_CPU.md` y `docs/mapeo_ensamblador.md`):

### 2.1 Especificaciones de Hardware de DUOX
* **Tamaño de Palabra (Word Size):** 64 bits (8 bytes por celda de memoria y registro).
* **Memoria Principal (RAM):** 64 KB (65,536 bytes direccionables), rango `0x0000` a `0xFFFF`.
* **Dirección Base del Programa de Usuario:** `0x1000` (4096 dec).
* **Pilas de Memoria:**
  - Núcleo 0: Inicia en `0xFFFF` (crece hacia direcciones menores).
  - Núcleo 1: Inicia en `0xF800`.
* **Concurrencia:** Dos núcleos independientes con turno rotativo, sincronizados mediante cerrojos de bus (`LOCK` / `UNLOCK`) y controlados con `CORE_START` y `CORE_YIELD`.
* **Red y E/S:** Interfaz de red de tipo loopback (`NET_SEND`, `NET_RECV`, `NET_STAT`) y puertos de 64 bits (`IN_PORT`, `OUT_PORT`).

### 2.2 Banco de Registros y Banderas
1. **PC (Program Counter):** Puntero de 64 bits a la siguiente instrucción a ejecutar.
2. **SP (Stack Pointer):** Puntero de 64 bits al tope de la pila de memoria (usado por `CALL`, `RET`, `INT`, `IRET`).
3. **BP (Base Pointer):** Registro base de marco de pila, utilizado por `LOAD_OFF` y `STORE_OFF`.
4. **TOS (Top of Stack):** Registro acelerador que almacena el elemento superior de la pila de trabajo.
5. **NOS (Next of Stack):** Registro que contiene el segundo elemento de la pila de trabajo.
6. **PSW (Program Status Word):** Registro de estado de 64 bits que empaqueta:
   - Bit 0: `C` (Acarreo / Préstamo en `ADD` y `SUB`).
   - Bit 1: `Z` (Cero: activo cuando el resultado de una operación es 0).
   - Bit 2: `N` (Negativo: bit 63 del resultado en 1).
   - Bit 3: `V` (Desbordamiento con signo en `ADD` y `SUB`).
   - Bit 4: `LOCK` (Estado del cerrojo del bus de memoria).
   - Bits 8-15: `CORE_ID` (Identificador del núcleo actual: 0 o 1, solo lectura).
   - Bit de interrupción: `I` (Habilitación de interrupciones, modificado por `EI`, `DI`, `IRET`).

### 2.3 Repertorio Completo de la ISA DUOX (48 Instrucciones Nativas)
El lenguaje DUOXC ofrece integración nativa con las 48 instrucciones de la máquina DUOX a través del ensamblador inline (`@asm_OPCODE`):

| Categoría | Mnemónicos Nativo DUOX | Tokens Léxicos DUOXC Inline | Formato / Opcode |
|:----------|:-----------------------|:----------------------------|:-----------------|
| **Aritmética y Lógica** | `NOP`, `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `AND`, `OR`, `XOR`, `NOT`, `SHL`, `SHR` | `@asm_NOP`, `@asm_ADD`, `@asm_SUB`, `@asm_MUL`, `@asm_DIV`, `@asm_MOD`, `@asm_AND`, `@asm_OR`, `@asm_XOR`, `@asm_NOT`, `@asm_SHL`, `@asm_SHR` | Tipo 0 (1 byte): `0x00` a `0x0B` |
| **Pila y Memoria** | `PUSH`, `POP`, `DUP`, `SWAP`, `LOAD`, `STORE`, `LOAD_OFF`, `STORE_OFF`, `LOAD_IMM` | `@asm_PUSH`, `@asm_POP`, `@asm_DUP`, `@asm_SWAP`, `@asm_LOAD`, `@asm_STORE`, `@asm_LOAD_OFF`, `@asm_STORE_OFF`, `@asm_LOAD_IMM` | Tipos 0 y 1: `0x10` a `0x18` |
| **Control de Flujo** | `JMP`, `JZ`, `JNZ`, `JGT`, `JLT`, `CALL`, `RET`, `HALT` | `@asm_JMP`, `@asm_JZ`, `@asm_JNZ`, `@asm_JGT`, `@asm_JLT`, `@asm_CALL`, `@asm_RET`, `@asm_HALT` | Tipos 0 y 1: `0x20` a `0x27` |
| **Concurrencia** | `GET_CORE`, `LOCK`, `UNLOCK`, `CORE_START`, `CORE_YIELD` | `@asm_GET_CORE`, `@asm_LOCK`, `@asm_UNLOCK`, `@asm_CORE_START`, `@asm_CORE_YIELD` | Tipos 0 y 1: `0x30` a `0x34` |
| **E/S y Red** | `IN_PORT`, `OUT_PORT`, `NET_SEND`, `NET_RECV`, `NET_STAT`, `OUT` | `@asm_IN_PORT`, `@asm_OUT_PORT`, `@asm_NET_SEND`, `@asm_NET_RECV`, `@asm_NET_STAT`, `@asm_OUT` | Tipo 0: `0x40` a `0x45` |
| **Sistema y Control** | `CACHE_FLUSH`, `MEM_COPY`, `SET_FLAGS`, `GET_FLAGS`, `INT`, `IRET`, `EI`, `DI` | `@asm_CACHE_FLUSH`, `@asm_MEM_COPY`, `@asm_SET_FLAGS`, `@asm_GET_FLAGS`, `@asm_INT`, `@asm_IRET`, `@asm_EI`, `@asm_DI` | Tipos 0 y 2: `0x50` a `0x57` |

### 2.4 FPU IEEE 754 de Doble Precisión
DUOX dispone de un procesador de punto flotante emulado que opera mediante vectores de interrupción de software:
- Vectores `16` a `29`: Servicios del FPU (`fpu_fadd`, `fpu_fsub`, `fpu_fmul`, `fpu_fdiv`, `fpu_fcmp`, `fpu_fi2f`, `fpu_ff2i`, `fpu_fprint`, etc.).
- Vectores `2` a `7`: Subrutinas de funciones matemáticas (`mate.inc`: `sqrt`, `exp`, `ln`, `sin`, `cos`, `mcm`).
En DUOXC, el tipo `float` y los operadores aritméticos (`+`, `-`, `*`, `/`, `**`) se traducen a llamadas de estos servicios.

---

## 3. Inciso d.i: Vocabulario Completo del Compilador

El vocabulario léxico de DUOXC comprende todos los símbolos terminales admitidos por el compilador, agrupados en categorías semánticas:

### 3.1 Palabras Reservadas (35 Keywords)
| Token | ID | Lexema | Rol Semántico |
|:------|:--:|:------:|:--------------|
| `TOKEN_KW_IF` | 258 | `if` | Apertura de bifurcación condicional |
| `TOKEN_KW_ELIF` | 259 | `elif` | Rama condicional intermedia encadenada |
| `TOKEN_KW_ELSE` | 260 | `else` | Rama condicional alternativa por defecto |
| `TOKEN_KW_FI` | 261 | `fi` | Cierre explícito de bloque `if` |
| `TOKEN_KW_WHILE` | 262 | `while` | Bucle de iteración indeterminada |
| `TOKEN_KW_DO` | 263 | `do` | Inicio del cuerpo del bucle `while` / `for` |
| `TOKEN_KW_DONE` | 264 | `done` | Fin del cuerpo del bucle |
| `TOKEN_KW_FOR` | 265 | `for` | Bucle de iteración sobre colecciones / rangos |
| `TOKEN_KW_IN` | 266 | `in` | Cláusula de pertenencia en iteraciones `for` |
| `TOKEN_KW_BREAK` | 267 | `break` | Ruptura inmediata del bucle activo |
| `TOKEN_KW_CONTINUE`| 268 | `continue` | Salto a la próxima iteración del bucle |
| `TOKEN_KW_RETURN` | 269 | `return` | Retorno de valor desde una función |
| `TOKEN_KW_INT` | 270 | `int` | Entero con signo de 64 bits (complemento a 2) |
| `TOKEN_KW_FLOAT` | 271 | `float` | Punto flotante IEEE 754 doble precisión (64 bits) |
| `TOKEN_KW_CHAR` | 272 | `char` | Carácter ASCII de 8 bits |
| `TOKEN_KW_BOOL` | 273 | `bool` | Valor booleano de 1 bit (`true` o `false`) |
| `TOKEN_KW_STRING` | 274 | `string` | Cadena de caracteres terminada en nulo |
| `TOKEN_KW_VOID` | 275 | `void` | Ausencia de tipo de retorno en subprogramas |
| `TOKEN_KW_STRUCT` | 276 | `struct` | Definición de Tipos Abstractos de Datos (TDAs) |
| `TOKEN_KW_ARRAY` | 277 | `array` | Declaración de arreglos unidimensionales |
| `TOKEN_KW_MATRIX` | 278 | `matrix` | Declaración de matrices bidimensionales |
| `TOKEN_KW_TRUE` | 279 | `true` | Constante lógica verdadera |
| `TOKEN_KW_FALSE` | 280 | `false` | Constante lógica falsa |
| `TOKEN_KW_NULL` | 281 | `null` | Puntero a dirección nula (`0x0000`) |
| `TOKEN_KW_PRINT` | 282 | `print` | Emisión a consola sin salto de línea |
| `TOKEN_KW_PRINTLN` | 283 | `println`| Emisión a consola con salto de línea |
| `TOKEN_KW_INPUT` | 284 | `input` | Lectura de valores desde consola |
| `TOKEN_KW_FUNC` | 285 | `func` | Declaración de función (con valor de retorno) |
| `TOKEN_KW_PROC` | 286 | `proc` | Declaración de procedimiento (sin valor de retorno) |
| `TOKEN_KW_ASM` | 287 | `asm` | Bloque contenedor de ensamblador inline |
| `TOKEN_KW_INTERRUPT`| 288| `interrupt`| Calificador de manejador de interrupción (ISR) |
| `TOKEN_KW_HALT` | 289 | `halt` | Detención de la máquina (`0x27` en DUOX) |
| `TOKEN_KW_AND` | 290 | `and` | Operador lógico conjuntivo en palabra |
| `TOKEN_KW_OR` | 291 | `or` | Operador lógico disyuntivo en palabra |
| `TOKEN_KW_NOT` | 292 | `not` | Operador lógico de negación en palabra |
| `TOKEN_KW_NEW` | 293 | `new` | Reserva dinámica de memoria en el heap |
| `TOKEN_KW_FREE` | 294 | `free` | Liberación de memoria dinámica |
| `TOKEN_KW_SIZEOF` | 295 | `sizeof` | Consulta de tamaño en bytes de un tipo/TDA |

### 3.2 Identificadores y Literales
| Token | ID | Ejemplo de Lexema | Descripción |
|:------|:--:|:------------------|:------------|
| `TOKEN_ID` | 300 | `factorial`, `_temp`, `Punto2D` | Nombres de variables, funciones, TDAs |
| `TOKEN_LIT_INT` | 301 | `0`, `42`, `1000` | Enteros decimales de 64 bits |
| `TOKEN_LIT_HEX` | 302 | `0x1000`, `0xFFFF` | Enteros en base 16 (hexadecimal) |
| `TOKEN_LIT_BIN` | 303 | `0b1010`, `0b110011` | Enteros en base 2 (binario) |
| `TOKEN_LIT_FLOAT` | 304 | `3.14159`, `2.5e-3`, `.5`, `1.` | Flotantes IEEE 754 de 64 bits |
| `TOKEN_LIT_CHAR` | 305 | `'a'`, `'\n'`, `'\x41'` | Constantes de carácter con escape |
| `TOKEN_LIT_STR` | 306 | `"Hola DUOX\n"`, `""` | Cadenas literales entre comillas |

### 3.3 Operadores Aritméticos, Relacionales, Lógicos y de Asignación
| Categoría | Token | ID | Lexema | Semántica |
|:----------|:------|:--:|:------:|:----------|
| **Aritméticos** | `TOKEN_OP_PLUS` | 310 | `+` | Suma entera o flotante |
| | `TOKEN_OP_MINUS` | 311 | `-` | Resta entera o flotante |
| | `TOKEN_OP_MUL` | 312 | `*` | Multiplicación entera o flotante |
| | `TOKEN_OP_DIV` | 313 | `/` | División entera o flotante |
| | `TOKEN_OP_MOD` | 314 | `%` | Módulo / Residuo entero |
| | `TOKEN_OP_POW` | 315 | `**` | Potencia (vía FPU `mate.inc`) |
| **Relacionales** | `TOKEN_OP_EQ` | 320 | `==` | Igualdad |
| | `TOKEN_OP_NEQ` | 321 | `!=` | Desigualdad |
| | `TOKEN_OP_LT` | 322 | `<` | Menor estricto |
| | `TOKEN_OP_GT` | 323 | `>` | Mayor estricto |
| | `TOKEN_OP_LE` | 324 | `<=` | Menor o igual |
| | `TOKEN_OP_GE` | 325 | `>=` | Mayor o igual |
| **Lógicos** | `TOKEN_OP_LAND` | 330 | `&&` | Conjunción lógica en cortocircuito |
| | `TOKEN_OP_LOR` | 331 | `\|\|` | Disyunción lógica en cortocircuito |
| | `TOKEN_OP_LNOT` | 332 | `!` | Negación lógica |
| **Bits** | `TOKEN_OP_BAND` | 335 | `&` | AND a nivel de bits |
| | `TOKEN_OP_BOR` | 336 | `\|` | OR a nivel de bits |
| | `TOKEN_OP_BXOR` | 337 | `^` | XOR a nivel de bits |
| | `TOKEN_OP_BNOT` | 338 | `~` | Complemento a 64 bits |
| | `TOKEN_OP_SHL` | 339 | `<<` | Desplazamiento a la izquierda |
| | `TOKEN_OP_SHR` | 340 | `>>` | Desplazamiento a la derecha |
| **Asignación** | `TOKEN_OP_ASSIGN` | 345 | `=` | Asignación simple |
| | `TOKEN_OP_PLUS_EQ` | 346 | `+=` | Suma y asignación |
| | `TOKEN_OP_MINUS_EQ` | 347 | `-=` | Resta y asignación |
| | `TOKEN_OP_MUL_EQ` | 348 | `*=` | Multiplicación y asignación |
| | `TOKEN_OP_DIV_EQ` | 349 | `/=` | División y asignación |
| | `TOKEN_OP_MOD_EQ` | 350 | `%=` | Módulo y asignación |
| **Acceso** | `TOKEN_OP_DOT` | 355 | `.` | Acceso a miembro de TDA / struct |
| | `TOKEN_OP_ARROW` | 356 | `->` | Acceso a miembro por puntero |
| | `TOKEN_OP_LBRACKET` | 357 | `[` | Apertura de índice de arreglo o matriz |
| | `TOKEN_OP_RBRACKET` | 358 | `]` | Cierre de índice de arreglo o matriz |
| | `TOKEN_OP_AMP` | 359 | `&` | Dirección de memoria (Address-of) |

### 3.4 Delimitadores y Puntuación
| Token | ID | Lexema | Uso Sintáctico |
|:------|:--:|:------:|:---------------|
| `TOKEN_LPAREN` | 360 | `(` | Apertura de parámetros y agrupamiento |
| `TOKEN_RPAREN` | 361 | `)` | Cierre de parámetros y agrupamiento |
| `TOKEN_LBRACE` | 362 | `{` | Apertura de cuerpo de función, TDA o bloque `asm` |
| `TOKEN_RBRACE` | 363 | `}` | Cierre de cuerpo de función, TDA o bloque `asm` |
| `TOKEN_SEMI` | 364 | `;` | Terminador de sentencias |
| `TOKEN_COMMA` | 365 | `,` | Separador de argumentos y campos |
| `TOKEN_COLON` | 366 | `:` | Declaración de tipos (`func f(x: int) : int`) |
| `TOKEN_DCOLON` | 367 | `::` | Resolución de ámbito de constantes y namespaces |
| `TOKEN_ARROW_FAT` | 368 | `=>` | Mapeo funcional y bifurcación `case` |
| `TOKEN_AT` | 369 | `@` | Prefijo de anotaciones y ensamblador inline |

---

## 4. Inciso d.ii: Categorías Gramaticales del Compilador

Para la construcción del analizador sintáctico en el Taller #02, los tokens definidos se clasifican en las siguientes **categorías gramaticales**:

1. **`Terminales_Palabras_Clave`**: Subdivididas en:
   - *Control de Flujo*: `{ if, elif, else, fi, while, do, done, for, in, break, continue, return }`
   - *Especificadores de Tipo*: `{ int, float, char, bool, string, void, struct, array, matrix }`
   - *Subprogramas*: `{ func, proc, interrupt }`
   - *Entrada/Salida*: `{ print, println, input }`
   - *Gestión de Memoria*: `{ new, free, sizeof }`
   - *Control de CPU*: `{ asm, halt }`
   - *Constantes literales especiales*: `{ true, false, null }`
2. **`Terminal_Identificador`**: `{ IDENTIFICADOR }` (nombres definidos por el usuario para variables, TDAs, procedimientos y campos).
3. **`Terminales_Literales`**: Constantes numéricas y alfanuméricas:
   - `{ LIT_ENTERO_DEC, LIT_ENTERO_HEX, LIT_ENTERO_BIN, LIT_FLOTANTE, LIT_CARACTER, LIT_CADENA }`
4. **`Terminales_Operadores`**:
   - *Aritméticos*: `{ +, -, *, /, %, ** }`
   - *Comparación/Relacionales*: `{ ==, !=, <, >, <=, >= }`
   - *Lógicos*: `{ &&, ||, !, and, or, not }`
   - *A nivel de bits*: `{ &, |, ^, ~, <<, >> }`
   - *Asignación*: `{ =, +=, -=, *=, /=, %= }`
   - *Acceso y Punteros*: `{ ., ->, [, ], & }`
5. **`Terminales_Delimitadores`**: `{ (, ), {, }, ;, ,, :, ::, =>, @ }`
6. **`Terminales_Ensamblador_Inline`**: 48 tokens específicos `{ @asm_NOP, ..., @asm_DI }` para emitir microinstrucciones de DUOX dentro de bloques `asm { ... }`.
7. **`Elementos_No_Gramaticales`** (eliminados por el lexer): Espacios en blanco (`[ \t\r\f\v]+`), saltos de línea (`\n`), comentarios de una línea (`//...`) y comentarios multilínea (`/* ... */`).

---

## 5. Inciso d.iii: Especificación de Patrones y Expresiones Regulares

A continuación se presentan las definiciones regulares y extensiones formales empleadas en `duoxc.l`:

### 5.1 Definiciones Regulares Base
```lex
DIGIT        [0-9]
HEX_DIGIT    [0-9A-Fa-f]
BIN_DIGIT    [01]
LETTER       [a-zA-Z]
ALNUM        [a-zA-Z0-9]
UNDERSCORE   [_]
NEWLINE      [\n]
WHITESPACE   [ \t\r\f\v]
```

### 5.2 Expresiones Regulares para Identificadores y Literales
* **Identificadores (`ID`):**
  $$\text{ID} = (\text{LETTER} \mid \text{UNDERSCORE})(\text{ALNUM} \mid \text{UNDERSCORE})^*$$
  *Flex:* `({LETTER}|{UNDERSCORE})({ALNUM}|{UNDERSCORE})*`
* **Enteros Decimales (`INT_DEC`):**
  $$\text{INT\_DEC} = 0 \mid [1-9][0-9]^*$$
  *Flex:* `(0|([1-9]{DIGIT}*))`
* **Enteros Hexadecimales (`INT_HEX`):**
  $$\text{INT\_HEX} = 0[xX][0-9A-Fa-f]^+$$
  *Flex:* `0[xX]{HEX_DIGIT}+`
* **Enteros Binarios (`INT_BIN`):**
  $$\text{INT\_BIN} = 0[bB][01]^+$$
  *Flex:* `0[bB]{BIN_DIGIT}+`
* **Flotantes con Notación Científica (`FLOAT_NUM`):**
  $$\text{EXP\_PART} = [eE][+-]?[0-9]^+$$
  $$\text{FLOAT\_NUM} = [0-9]^+\.[0-9]^*(\text{EXP\_PART})? \mid \.[0-9]^+(\text{EXP\_PART})? \mid [0-9]^+(\text{EXP\_PART})$$
  *Flex:* `({DIGIT}+\.{DIGIT}*{EXP_PART}?|\.{DIGIT}+{EXP_PART}?|{DIGIT}+{EXP_PART})`
* **Secuencias de Escape (`ESC_SEQ`):**
  $$\text{ESC\_SEQ} = \backslash([ntrfvab0\backslash'"] \mid x[0-9A-Fa-f]^{1,2})$$
  *Flex:* `\\([ntrfvab0\\'"]|x{HEX_DIGIT}{1,2})`
* **Literales de Carácter (`CHAR_LIT`):**
  $$\text{CHAR\_LIT} = '(\text{ESC\_SEQ} \mid [^'\backslash\backslash\n])'$$
  *Flex:* `'({ESC_SEQ}|[^'\\\n])'`
* **Literales de Cadena (`STR_LIT`):**
  $$\text{STR\_LIT} = "(\text{ESC\_SEQ} \mid [^"\backslash\backslash\n])*"$$
  *Flex:* `\"({ESC_SEQ}|[^"\\\n])*\"`

### 5.3 Máquina de Estados para Comentarios Multilínea
Para evitar expresiones regulares no deterministas o desbordamiento en comentarios extensos, se emplea la condición de inicio exclusiva `%x COMMENT_ML`:
- Transición a `COMMENT_ML` al detectar `"/*"`.
- Consumo de caracteres hasta encontrar `"*"+"/"`, regresando a `INITIAL`.
- Emisión de error léxico si se alcanza `<<EOF>>` antes de cerrar el bloque.

---

## 6. Estructura de Archivos y Guía de Construcción

```
S:\Tareas Trivino\LP02-DUOX\AnalizadorLexico\
├── duoxc.l             # Archivo de especificación léxica en Flex
├── Makefile            # Automatizador de compilación GCC + Flex
├── test_programa.dx    # Programa de prueba que ejercita todos los tokens
└── README.md           # Este informe técnico y académico
```

### 6.1 Compilación
```bash
cd "/mnt/s/Tareas Trivino/LP02-DUOX/AnalizadorLexico"
make
```

### 6.2 Ejecución de Pruebas
```bash
make test
```

### 6.3 Limpieza
```bash
make clean
```

---

## 7. Resultados Experimentales

El programa de prueba `test_programa.dx` (274 líneas) cubre de manera exhaustiva:
- Estructuras `if / elif / else / fi` y bucles `while / do / done` y `for / in`.
- Funciones recursivas (`factorial`), iterativas (`potencia`) y con flotantes (`distancia`).
- Tipos abstractos de datos (`struct Punto2D`, `struct ProcesoDUOX`).
- Arreglos y matrices (`array int fib[10]`, `matrix float m[4][4]`).
- Acceso por campos (`.` y `->`) y resolución de ámbito (`DUOX::PROGRAMA_BASE`).
- Aritmética de punto flotante de 64 bits con FPU (`**`, notación `2.5e-10`, `.5`, `1.`).
- Bloques de ensamblador inline (`asm { @asm_LOAD_IMM ... }`) con instrucciones de concurrencia (`@asm_CORE_START`, `@asm_LOCK`), red (`@asm_NET_SEND`) y sistema (`@asm_SET_FLAGS`, `@asm_EI`).

### Resumen del Análisis Léxico
```
=================================================================
  RESUMEN DEL ANÁLISIS LÉXICO
-----------------------------------------------------------------
  Tokens reconocidos correctamente : 760
  Líneas procesadas               : 274
  Errores léxicos detectados      : 0
=================================================================
```

---

## 8. Conclusiones

1. **Cumplimiento Integral de los Requerimientos:** El analizador léxico satisface a cabalidad los incisos **d.i**, **d.ii** y **d.iii**, proveyendo un vocabulario riguroso, una taxonomía gramatical completa y expresiones regulares optimizadas.
2. **Coherencia con la Arquitectura DUOX:** Integra la totalidad de las 48 instrucciones nativas de la CPU, los registros (`PC`, `TOS`, `NOS`, `SP`, `BP`, `PSW`), los vectores del FPU (`mate.inc` y `fpu.asm`) y los mecanismos de concurrencia de la máquina diseñada en las Tareas #09 y #10.
3. **Preparación para la Fase Sintáctica:** Los códigos numéricos de los tokens inician en `258` y se organizan con nombres estándar, garantizando una transición directa a la gramática libre de contexto de Bison/Yacc en el Taller #02.
