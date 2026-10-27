# Preprocesador del SPL de DUOS (Taller 1, punto a)

Traductor escrito con **FLEX + C** que resuelve las macros de incluir y definir
sobre el fuente del SPL. Trabaja en texto: lo que sale es el fuente que consume
el siguiente módulo de la cadena (analizador léxico del compilador o ensamblador).

## Uso

```bash
make                      # genera build/lex.yy.c y el ejecutable pp
./pp fuente.spl           # resultado por stdout
./pp fuente.spl -o fuente.i
./pp fuente.spl -I include -D DEPURA=1
make test                 # pruebas/pruebas/ejecutar.py
```

Código de salida: 0 si no hubo errores, 1 si hubo diagnósticos, 2 si el uso es
incorrecto.

## Directivas

| Directiva | Efecto |
| --- | --- |
| `#include "archivo"` / `.INCLUDE "archivo"` | inserta el archivo (relativo al que incluye y luego a los `-I`) |
| `#include <archivo>` | busca solo en los directorios `-I` |
| `#define NOMBRE cuerpo` | macro objeto; el cuerpo llega hasta el fin de línea (`\` continúa) |
| `#define NOMBRE(a, b) cuerpo` | macro con parámetros; el `(` debe seguir al nombre |
| `#undef NOMBRE` | elimina la macro |
| `#ifdef` / `#ifndef` / `#else` / `#endif` | compilación condicional, anidable |
| `#error mensaje` | error con el mensaje |

Las directivas se reconocen al inicio de línea (con blancos delante) y no se
emiten. Las macros se expanden en el texto, pero no dentro de cadenas, caracteres
ni comentarios (`;`, `//`, `/* */`), que se copian tal cual.

## Diseño

* **Análisis léxico (`src/pp.l`).** Las directivas son expresiones regulares
  ancladas a inicio de línea; el resto del fuente se reparte en identificadores,
  cadenas, caracteres y comentarios. Un identificador se busca en la tabla de
  macros y, si es macro objeto, su cuerpo se inyecta como un buffer nuevo de
  FLEX (`yy_scan_string` + `yy_switch_to_buffer`).
* **Macros con parámetros.** Tras el nombre y el `(`, los argumentos se leen del
  flujo con `input()` contando paréntesis y respetando cadenas; se separan por
  comas de nivel 1, se recortan y se sustituyen por nombre entero en el cuerpo.
  El resultado se reescanea, así que las macros del cuerpo y de los argumentos
  se expanden solas.
* **Pila de fuentes.** Archivos incluidos y expansiones comparten una pila de
  frames (`Fuente`), cada uno con su buffer, archivo, directorio, línea y
  profundidad de condicionales. La regla `<<EOF>>` desapila y devuelve el control
  al frame anterior; ahí se apoyan los includes anidados y las expansiones dentro
  de expansiones.
* **Recursión.** Una macro que ya está en expansión no se expande otra vez
  (`#define A A` termina dejando `A`). Límites: 32 includes encadenados y 64
  expansiones activas.
* **Condicionales.** Pila de bloques con `padre`, `rama` y `visto_else`; el texto
  inactivo no se emite ni se expande, pero las directivas se siguen leyendo para
  respetar el anidamiento. Un bloque abierto al final del archivo se reporta.
* **Diagnósticos.** `archivo:línea: error: mensaje` por stderr, con la línea del
  frame en curso (la del archivo incluido, no la del que lo incluye).

## Estructura

```
preprocesador/
├── Makefile
├── src/pp.l        analizador FLEX: directivas, pila de fuentes y expansión
├── src/macros.c    tabla de macros (búsqueda, definición, #undef)
├── src/main.c      línea de comandos (-o, -I, -D)
├── src/pp.h        interfaz común
└── pruebas/        casos, salidas esperadas y ejecutar.py
```

`pruebas/ejecutar.py` compara cada caso con su `.out` (o su `.err`) y al final
encadena preprocesador → ensamblador → emulador con `pruebas/casos/integracion`.

## Limitaciones

* No hay `#if`/`#elif` con expresiones (solo `#ifdef`/`#ifndef`), ni `#`, `##`,
  ni macros variádicas.
* La sustitución es perezosa: los argumentos se insertan sin pre-expandir y el
  cuerpo completo se reescanea. Basta para el ensamblador; no reproduce la
  precedencia exacta de C en expresiones con efectos laterales.
* No se expande una macro usada como argumento de `#include`.
* La tabla de macros es una lista enlazada: suficiente para el tamaño de estos
  fuentes (no hay límite práctico, pero la búsqueda es lineal).

El bosquejo en PLY (`preprocesador/preprocesador.py`) queda fuera de uso: esta
es la versión FLEX del punto a.
