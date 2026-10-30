%{
/**
 * ============================================================================
 * COMPILADORES - TALLER #01: ANALIZADOR LÉXICO DEL COMPILADOR DUOXC
 * Arquitectura destino: Máquina DUOX / DUOS (pila de 64 bits)
 * Grupo F - LP02-DUOX
 * ============================================================================
 *
 * Archivo    : duoxc.l
 * Herramienta: FLEX (Fast Lexical Analyzer Generator)
 * Lenguaje   : C (generado) / FLEX (especificación)
 *
 * DESCRIPCIÓN GENERAL
 * -------------------
 * Este archivo es la especificación FLEX del analizador léxico (scanner)
 * para el COMPILADOR del lenguaje de alto nivel DUOXC, diseñado para compilar
 * a código de la máquina de pila DUOX / DUOS.
 *
 * La máquina DUOX es una arquitectura de pila (stack-based) de 64 bits con:
 *   - Registros: PC, TOS, NOS, SP, BP, PSW (flags: C, Z, N, V, I, LOCK, CORE_ID)
 *   - RAM: 64 KB (bus de 16 bits efectivos); palabras de 64 bits (8 bytes)
 *   - Base del programa de usuario: 0x1000
 *   - ISA: 48 instrucciones nativas (ver docs/ISA_CPU.md)
 *   - FPU de punto flotante IEEE 754 de doble precisión (via interrupciones)
 *   - Soporte de concurrencia con 2 núcleos (CORE_START, CORE_YIELD, LOCK/UNLOCK)
 *   - Soporte de red (NET_SEND, NET_RECV, NET_STAT) y puertos de E/S
 *
 * LENGUAJE DUOXC
 * --------------
 * Lenguaje imperativo con tipos de datos abstractos diseñado específicamente
 * para compilar a la máquina DUOX. Soporta:
 *   - Tipos primitivos: int (64 bits, complemento a dos), float (IEEE 754 double),
 *                       char (ASCII), bool
 *   - Tipos compuestos: struct (TDA), array[], matrix[][]
 *   - Estructuras de control: if/elif/else/fi, while/do/done, for/in
 *   - Funciones (func) con retorno y procedimientos (proc) sin retorno
 *   - Punto flotante completo usando el FPU de DUOX via interrupciones
 *   - Ensamblador inline para acceso de bajo nivel a la máquina DUOX
 *   - Gestión de interrupciones (interrupt handlers)
 *
 * VOCABULARIO LÉXICO RECONOCIDO
 * ------------------------------
 * Categorías Léxicas (ver Sección 3 - Reglas):
 *   1.  Palabras reservadas (keywords)    - 35 tokens
 *   2.  Identificadores                   - TOKEN_ID
 *   3.  Literales enteros (dec, hex, bin) - TOKEN_LIT_INT, TOKEN_LIT_HEX, TOKEN_LIT_BIN
 *   4.  Literales flotantes               - TOKEN_LIT_FLOAT
 *   5.  Literales de carácter             - TOKEN_LIT_CHAR
 *   6.  Literales de cadena               - TOKEN_LIT_STR
 *   7.  Booleanos (true, false)           - TOKEN_KW_TRUE, TOKEN_KW_FALSE
 *   8.  Operadores aritméticos            - 6 tokens
 *   9.  Operadores de comparación         - 6 tokens
 *   10. Operadores lógicos                - 3 tokens
 *   11. Operadores de asignación          - 6 tokens
 *   12. Operadores de bits                - 6 tokens
 *   13. Operadores de acceso              - 5 tokens
 *   14. Delimitadores y puntuación        - 10 tokens
 *   15. Mnemónicos ensamblador DUOX inline- 48 tokens específicos (ISA completa)
 *   16. Comentarios // y / * * /          - ignorados, conteo de líneas
 *   17. Espacios en blanco                - ignorados, conteo de líneas
 *   18. Token de error                    - TOKEN_ERROR
 *
 * COMPILACIÓN:
 *   flex duoxc.l
 *   gcc -Wall -std=c99 lex.yy.c -lfl -o duoxc_lex
 *   O bien: make   (usando el Makefile incluido)
 *
 * EJECUCIÓN:
 *   ./duoxc_lex test_programa.dx
 * ============================================================================
 */

/* Habilitamos extensiones POSIX para fileno() e isatty() en modo C99 */
#ifndef _POSIX_C_SOURCE
#  define _POSIX_C_SOURCE 200809L
#endif
#ifndef _DEFAULT_SOURCE
#  define _DEFAULT_SOURCE
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

/* ============================================================================
 * SECCIÓN 1: DEFINICIÓN DE TOKENS (CÓDIGOS NUMÉRICOS)
 *
 * Convención: iniciamos en 258 para compatibilidad con Bison/Yacc, que reserva
 * los valores 0-255 para caracteres ASCII literales y usa 256-257 internamente.
 * El token 0 (EOF) lo maneja FLEX automáticamente (yywrap).
 * ============================================================================
 */

/* --- 1.1 Palabras Reservadas del Lenguaje DUOXC --- */
/* Control de flujo */
#define TOKEN_KW_IF          258   /* Condicional: if cond do ... fi   */
#define TOKEN_KW_ELIF        259   /* Alternativa: elif cond do ... fi  */
#define TOKEN_KW_ELSE        260   /* Alternativa por defecto: else ... fi */
#define TOKEN_KW_FI          261   /* Cierre del bloque if/elif/else    */
#define TOKEN_KW_WHILE       262   /* Iteración pre-condición: while e do ... done */
#define TOKEN_KW_DO          263   /* Inicia cuerpo de while/for        */
#define TOKEN_KW_DONE        264   /* Cierra cuerpo de while/for        */
#define TOKEN_KW_FOR         265   /* Iteración sobre colección: for x in arr do ... done */
#define TOKEN_KW_IN          266   /* Separador de for: for x in ...    */
#define TOKEN_KW_BREAK       267   /* Ruptura de iteración              */
#define TOKEN_KW_CONTINUE    268   /* Próxima iteración                 */
#define TOKEN_KW_RETURN      269   /* Retorno de función con valor      */

/* Tipos de datos */
#define TOKEN_KW_INT         270   /* Entero con signo de 64 bits       */
#define TOKEN_KW_FLOAT       271   /* Flotante IEEE 754 double (64 bits)*/
#define TOKEN_KW_CHAR        272   /* Carácter ASCII (8 bits)           */
#define TOKEN_KW_BOOL        273   /* Booleano (true / false)           */
#define TOKEN_KW_STRING      274   /* Cadena de caracteres              */
#define TOKEN_KW_VOID        275   /* Sin tipo de retorno (procedimientos) */
#define TOKEN_KW_STRUCT      276   /* Tipo de dato abstracto estructurado  */
#define TOKEN_KW_ARRAY       277   /* Arreglo de tipo base              */
#define TOKEN_KW_MATRIX      278   /* Matriz bidimensional              */

/* Literales booleanos y null */
#define TOKEN_KW_TRUE        279   /* Literal booleano verdadero        */
#define TOKEN_KW_FALSE       280   /* Literal booleano falso            */
#define TOKEN_KW_NULL        281   /* Referencia nula                   */

/* Entrada / Salida */
#define TOKEN_KW_PRINT       282   /* Impresión sin salto de línea      */
#define TOKEN_KW_PRINTLN     283   /* Impresión con salto de línea      */
#define TOKEN_KW_INPUT       284   /* Lectura desde consola             */

/* Definición de subprogramas */
#define TOKEN_KW_FUNC        285   /* Función con tipo de retorno        */
#define TOKEN_KW_PROC        286   /* Procedimiento sin retorno (void)  */

/* Interfaz de bajo nivel / hardware */
#define TOKEN_KW_ASM         287   /* Bloque de ensamblador inline      */
#define TOKEN_KW_INTERRUPT   288   /* Definición de manejador de interrupción */
#define TOKEN_KW_HALT        289   /* Detiene la ejecución de la máquina   */

/* Operadores lógicos como palabras clave */
#define TOKEN_KW_AND         290   /* Conjunción lógica (alternativa a &&) */
#define TOKEN_KW_OR          291   /* Disyunción lógica (alternativa a ||) */
#define TOKEN_KW_NOT         292   /* Negación lógica (alternativa a !)    */

/* Gestión de memoria dinámica */
#define TOKEN_KW_NEW         293   /* Creación dinámica de instancia (heap) */
#define TOKEN_KW_FREE        294   /* Liberación de memoria dinámica        */
#define TOKEN_KW_SIZEOF      295   /* Tamaño en bytes de un tipo/variable   */

/* --- 1.2 Identificadores y Literales --- */
#define TOKEN_ID             300   /* Identificador: [a-zA-Z_][a-zA-Z0-9_]* */
#define TOKEN_LIT_INT        301   /* Literal entero decimal: 0, 42, -7      */
#define TOKEN_LIT_HEX        302   /* Literal entero hexadecimal: 0x1A3F     */
#define TOKEN_LIT_BIN        303   /* Literal entero binario: 0b1010         */
#define TOKEN_LIT_FLOAT      304   /* Literal flotante: 3.14, 2.5e-3, .5    */
#define TOKEN_LIT_CHAR       305   /* Literal de carácter: 'a', '\n', '\x41'*/
#define TOKEN_LIT_STR        306   /* Literal de cadena: "hola mundo\n"     */

/* --- 1.3 Operadores Aritméticos --- */
#define TOKEN_OP_PLUS        310   /* +   Suma entera o flotante            */
#define TOKEN_OP_MINUS       311   /* -   Resta entera o flotante           */
#define TOKEN_OP_MUL         312   /* *   Multiplicación                    */
#define TOKEN_OP_DIV         313   /* /   División (entera o flotante según tipos) */
#define TOKEN_OP_MOD         314   /* %   Módulo / residuo                  */
#define TOKEN_OP_POW         315   /* **  Potenciación (via FPU)            */

/* --- 1.4 Operadores de Comparación / Relación --- */
#define TOKEN_OP_EQ          320   /* ==  Igualdad                          */
#define TOKEN_OP_NEQ         321   /* !=  Desigualdad                       */
#define TOKEN_OP_LT          322   /* <   Menor que                         */
#define TOKEN_OP_GT          323   /* >   Mayor que                         */
#define TOKEN_OP_LE          324   /* <=  Menor o igual                     */
#define TOKEN_OP_GE          325   /* >=  Mayor o igual                     */

/* --- 1.5 Operadores Lógicos (símbolos) --- */
#define TOKEN_OP_LAND        330   /* &&  Conjunción lógica (cortocircuito) */
#define TOKEN_OP_LOR         331   /* ||  Disyunción lógica (cortocircuito) */
#define TOKEN_OP_LNOT        332   /* !   Negación lógica unaria            */

/* --- 1.6 Operadores de Bits --- */
#define TOKEN_OP_BAND        335   /* &   AND bit a bit                     */
#define TOKEN_OP_BOR         336   /* |   OR bit a bit                      */
#define TOKEN_OP_BXOR        337   /* ^   XOR bit a bit                     */
#define TOKEN_OP_BNOT        338   /* ~   NOT bit a bit (complemento a 64b) */
#define TOKEN_OP_SHL         339   /* <<  Desplazamiento a la izquierda     */
#define TOKEN_OP_SHR         340   /* >>  Desplazamiento a la derecha       */

/* --- 1.7 Operadores de Asignación --- */
#define TOKEN_OP_ASSIGN      345   /* =   Asignación simple                 */
#define TOKEN_OP_PLUS_EQ     346   /* +=  Asignación suma                   */
#define TOKEN_OP_MINUS_EQ    347   /* -=  Asignación resta                  */
#define TOKEN_OP_MUL_EQ      348   /* *=  Asignación multiplicación         */
#define TOKEN_OP_DIV_EQ      349   /* /=  Asignación división               */
#define TOKEN_OP_MOD_EQ      350   /* %=  Asignación módulo                 */

/* --- 1.8 Operadores de Acceso y Referencia --- */
#define TOKEN_OP_DOT         355   /* .   Acceso a miembro de struct        */
#define TOKEN_OP_ARROW       356   /* ->  Acceso a miembro via puntero      */
#define TOKEN_OP_LBRACKET    357   /* [   Apertura de indexación de arreglo */
#define TOKEN_OP_RBRACKET    358   /* ]   Cierre de indexación de arreglo   */
#define TOKEN_OP_AMP         359   /* &   Referencia/dirección de variable  */

/* --- 1.9 Delimitadores y Puntuación --- */
#define TOKEN_LPAREN         360   /* (   Apertura de paréntesis            */
#define TOKEN_RPAREN         361   /* )   Cierre de paréntesis              */
#define TOKEN_LBRACE         362   /* {   Apertura de bloque asm / struct   */
#define TOKEN_RBRACE         363   /* }   Cierre de bloque asm / struct     */
#define TOKEN_SEMI           364   /* ;   Punto y coma (fin de sentencia)   */
#define TOKEN_COMMA          365   /* ,   Coma (separador de argumentos)    */
#define TOKEN_COLON          366   /* :   Dos puntos (declaración de tipo)  */
#define TOKEN_DCOLON         367   /* ::  Resolución de ámbito (módulo::id) */
#define TOKEN_ARROW_FAT      368   /* =>  Mapeo / lambda / case branch      */
#define TOKEN_AT             369   /* @   Prefijo / anotación               */

/* --- 1.10 Mnemónicos de la ISA DUOX (ensamblador inline: @asm_MNEM) --- */
/* 48 instrucciones nativas según docs/ISA_CPU.md                          */
/* Aritmética y lógica (Tipo 0: 1 byte)                                    */
#define TOKEN_ASM_NOP        400   /* @asm_NOP       0x00 No operación      */
#define TOKEN_ASM_ADD        401   /* @asm_ADD       0x01 TOS <- TOS+NOS    */
#define TOKEN_ASM_SUB        402   /* @asm_SUB       0x02 TOS <- NOS-TOS    */
#define TOKEN_ASM_MUL        403   /* @asm_MUL       0x03 TOS <- TOS*NOS    */
#define TOKEN_ASM_DIV        404   /* @asm_DIV       0x04 TOS <- TOS//NOS   */
#define TOKEN_ASM_MOD        405   /* @asm_MOD       0x05 TOS <- TOS%NOS    */
#define TOKEN_ASM_AND        406   /* @asm_AND       0x06 TOS <- TOS&NOS    */
#define TOKEN_ASM_OR         407   /* @asm_OR        0x07 TOS <- TOS|NOS    */
#define TOKEN_ASM_XOR        408   /* @asm_XOR       0x08 TOS <- TOS^NOS    */
#define TOKEN_ASM_NOT        409   /* @asm_NOT       0x09 TOS <- ~TOS       */
#define TOKEN_ASM_SHL        410   /* @asm_SHL       0x0A TOS <- NOS<<TOS   */
#define TOKEN_ASM_SHR        411   /* @asm_SHR       0x0B TOS <- NOS>>TOS   */
/* Pila y memoria (Tipo 0 o Tipo 1)                                        */
#define TOKEN_ASM_PUSH       412   /* @asm_PUSH imm  0x10 NOS<-TOS; TOS<-v */
#define TOKEN_ASM_POP        413   /* @asm_POP       0x11 TOS <- NOS        */
#define TOKEN_ASM_DUP        414   /* @asm_DUP       0x12 NOS <- TOS        */
#define TOKEN_ASM_SWAP       415   /* @asm_SWAP      0x13 TOS <-> NOS       */
#define TOKEN_ASM_LOAD       416   /* @asm_LOAD dir  0x14 TOS <- MEM[dir]   */
#define TOKEN_ASM_STORE      417   /* @asm_STORE dir 0x15 MEM[dir] <- TOS   */
#define TOKEN_ASM_LOAD_OFF   418   /* @asm_LOAD_OFF  0x16 MEM[BP+offset]    */
#define TOKEN_ASM_STORE_OFF  419   /* @asm_STORE_OFF 0x17 MEM[BP+off]<-TOS  */
#define TOKEN_ASM_LOAD_IMM   420   /* @asm_LOAD_IMM  0x18 TOS <- imm (LDI) */
/* Control de flujo (Tipo 1: 9 bytes)                                      */
#define TOKEN_ASM_JMP        421   /* @asm_JMP dir   0x20 PC <- dir         */
#define TOKEN_ASM_JZ         422   /* @asm_JZ  dir   0x21 si Z: PC <- dir  */
#define TOKEN_ASM_JNZ        423   /* @asm_JNZ dir   0x22 si !Z: PC <- dir */
#define TOKEN_ASM_JGT        424   /* @asm_JGT dir   0x23 si Z=0,N=V: salta*/
#define TOKEN_ASM_JLT        425   /* @asm_JLT dir   0x24 si N!=V: salta   */
#define TOKEN_ASM_CALL       426   /* @asm_CALL dir  0x25 apila PC+9; salta */
#define TOKEN_ASM_RET        427   /* @asm_RET       0x26 PC <- pila mem    */
#define TOKEN_ASM_HALT       428   /* @asm_HALT      0x27 detiene el núcleo */
/* Concurrencia                                                             */
#define TOKEN_ASM_GET_CORE   429   /* @asm_GET_CORE  0x30 empuja CORE_ID    */
#define TOKEN_ASM_LOCK       430   /* @asm_LOCK      0x31 cerrojo de bus    */
#define TOKEN_ASM_UNLOCK     431   /* @asm_UNLOCK    0x32 libera cerrojo    */
#define TOKEN_ASM_CORE_START 432   /* @asm_CORE_START dir 0x33 arranca NC1 */
#define TOKEN_ASM_CORE_YIELD 433   /* @asm_CORE_YIELD 0x34 cede el turno   */
/* E/S y red                                                                */
#define TOKEN_ASM_IN_PORT    434   /* @asm_IN_PORT   0x40 lee un puerto     */
#define TOKEN_ASM_OUT_PORT   435   /* @asm_OUT_PORT  0x41 escribe un puerto */
#define TOKEN_ASM_NET_SEND   436   /* @asm_NET_SEND  0x42 envía por red     */
#define TOKEN_ASM_NET_RECV   437   /* @asm_NET_RECV  0x43 recibe por red    */
#define TOKEN_ASM_NET_STAT   438   /* @asm_NET_STAT  0x44 bytes pendientes  */
#define TOKEN_ASM_OUT        439   /* @asm_OUT       0x45 chr(TOS) a consola*/
/* Sistema                                                                  */
#define TOKEN_ASM_CACHE_FLUSH 440  /* @asm_CACHE_FLUSH 0x50 sin efecto     */
#define TOKEN_ASM_MEM_COPY   441   /* @asm_MEM_COPY  0x51 copia n palabras  */
#define TOKEN_ASM_SET_FLAGS  442   /* @asm_SET_FLAGS 0x52 actualiza PSW     */
#define TOKEN_ASM_GET_FLAGS  443   /* @asm_GET_FLAGS 0x53 empuja PSW        */
#define TOKEN_ASM_INT        444   /* @asm_INT       0x54 interrupción soft */
#define TOKEN_ASM_IRET       445   /* @asm_IRET      0x55 retorno de ISR    */
#define TOKEN_ASM_EI         446   /* @asm_EI        0x56 habilita INT      */
#define TOKEN_ASM_DI         447   /* @asm_DI        0x57 deshabilita INT   */

/* --- 1.11 Token de Error --- */
#define TOKEN_ERROR          500   /* Carácter o secuencia no reconocida   */

/* ============================================================================
 * VARIABLES GLOBALES DEL ANALIZADOR LÉXICO
 * ============================================================================ */
static int total_tokens  = 0;   /* Total de tokens reconocidos exitosamente */
static int total_errores = 0;   /* Total de errores léxicos encontrados      */

/* ============================================================================
 * PROTOTIPOS DE FUNCIONES AUXILIARES
 * ============================================================================ */
const char *token_nombre(int tok);
void        imprimir_token(int tok, const char *lexema);
void        reporte_error(const char *lexema, const char *razon);

%}

/* ============================================================================
 * OPCIONES DE FLEX
 * ============================================================================ */
%option noyywrap
%option yylineno
%option noinput
%option nounput

/* ============================================================================
 * CONDICIONES DE INICIO (Start Conditions)
 * ============================================================================ */
%x COMMENT_ML

/* ============================================================================
 * SECCIÓN 2: DEFINICIONES REGULARES (Patrones con nombre)
 * ============================================================================ */

/* --- 2.1 Caracteres básicos --- */
DIGIT        [0-9]
HEX_DIGIT    [0-9A-Fa-f]
BIN_DIGIT    [01]
LETTER       [a-zA-Z]
ALNUM        [a-zA-Z0-9]
UNDERSCORE   [_]
NEWLINE      [\n]
WHITESPACE   [ \t\r\f\v]

/* --- 2.2 Identificadores --- */
ID           ({LETTER}|{UNDERSCORE})({ALNUM}|{UNDERSCORE})*

/* --- 2.3 Literales Enteros --- */
INT_DEC      (0|([1-9]{DIGIT}*))
INT_HEX      0[xX]{HEX_DIGIT}+
INT_BIN      0[bB]{BIN_DIGIT}+

/* --- 2.4 Literales Flotantes --- */
EXP_PART     [eE][+-]?{DIGIT}+
FLOAT_NUM    ({DIGIT}+\.{DIGIT}*{EXP_PART}?|\.{DIGIT}+{EXP_PART}?|{DIGIT}+{EXP_PART})

/* --- 2.5 Secuencias de escape --- */
ESC_SEQ      \\([ntrfvab0\\'"]|x{HEX_DIGIT}{1,2})

/* --- 2.6 Literales de carácter --- */
CHAR_LIT     '({ESC_SEQ}|[^'\\\n])'

/* --- 2.7 Literales de cadena --- */
STR_LIT      \"({ESC_SEQ}|[^"\\\n])*\"

/* --- 2.8 Identificador de mnemónico ensamblador inline --- */
ASM_MNEM     @asm_({LETTER}|{UNDERSCORE})({ALNUM}|{UNDERSCORE})*

%%

    /* =======================================================================
     * SECCIÓN 3: REGLAS LÉXICAS Y ACCIONES SEMÁNTICAS
     * (Todos los comentarios aquí dentro llevan sangría para Flex)
     * ======================================================================= */

    /* --- 3.1 Comentarios --- */

"//"[^\n]*           { /* Comentario de línea: se descarta */ }

"/*"                 { BEGIN(COMMENT_ML); }
<COMMENT_ML>[^*\n]+  { /* Consume contenido del comentario multilínea */ }
<COMMENT_ML>"*"+[^*/\n]* { /* Consume '*' no seguido de '/' */ }
<COMMENT_ML>\n       { /* yylineno se actualiza automáticamente */ }
<COMMENT_ML>"*"+"/"  { BEGIN(INITIAL); }
<COMMENT_ML><<EOF>>  {
    reporte_error("/*", "comentario multilínea sin cerrar (falta */)");
    return TOKEN_ERROR;
}

    /* --- 3.2 Espacios en blanco --- */
{WHITESPACE}+  { /* Espacios horizontales: se ignoran */ }
{NEWLINE}+     { /* Saltos de línea: yylineno ya los cuenta */ }

    /* --- 3.3 Palabras reservadas (Keywords) --- */
"if"         { imprimir_token(TOKEN_KW_IF,       yytext); return TOKEN_KW_IF;       }
"elif"       { imprimir_token(TOKEN_KW_ELIF,     yytext); return TOKEN_KW_ELIF;     }
"else"       { imprimir_token(TOKEN_KW_ELSE,     yytext); return TOKEN_KW_ELSE;     }
"fi"         { imprimir_token(TOKEN_KW_FI,       yytext); return TOKEN_KW_FI;       }
"while"      { imprimir_token(TOKEN_KW_WHILE,    yytext); return TOKEN_KW_WHILE;    }
"do"         { imprimir_token(TOKEN_KW_DO,       yytext); return TOKEN_KW_DO;       }
"done"       { imprimir_token(TOKEN_KW_DONE,     yytext); return TOKEN_KW_DONE;     }
"for"        { imprimir_token(TOKEN_KW_FOR,      yytext); return TOKEN_KW_FOR;      }
"in"         { imprimir_token(TOKEN_KW_IN,       yytext); return TOKEN_KW_IN;       }
"break"      { imprimir_token(TOKEN_KW_BREAK,    yytext); return TOKEN_KW_BREAK;    }
"continue"   { imprimir_token(TOKEN_KW_CONTINUE, yytext); return TOKEN_KW_CONTINUE; }
"return"     { imprimir_token(TOKEN_KW_RETURN,   yytext); return TOKEN_KW_RETURN;   }

"int"        { imprimir_token(TOKEN_KW_INT,    yytext); return TOKEN_KW_INT;    }
"float"      { imprimir_token(TOKEN_KW_FLOAT,  yytext); return TOKEN_KW_FLOAT;  }
"char"       { imprimir_token(TOKEN_KW_CHAR,   yytext); return TOKEN_KW_CHAR;   }
"bool"       { imprimir_token(TOKEN_KW_BOOL,   yytext); return TOKEN_KW_BOOL;   }
"string"     { imprimir_token(TOKEN_KW_STRING, yytext); return TOKEN_KW_STRING; }
"void"       { imprimir_token(TOKEN_KW_VOID,   yytext); return TOKEN_KW_VOID;   }
"struct"     { imprimir_token(TOKEN_KW_STRUCT, yytext); return TOKEN_KW_STRUCT; }
"array"      { imprimir_token(TOKEN_KW_ARRAY,  yytext); return TOKEN_KW_ARRAY;  }
"matrix"     { imprimir_token(TOKEN_KW_MATRIX, yytext); return TOKEN_KW_MATRIX; }

"true"       { imprimir_token(TOKEN_KW_TRUE,  yytext); return TOKEN_KW_TRUE;  }
"false"      { imprimir_token(TOKEN_KW_FALSE, yytext); return TOKEN_KW_FALSE; }
"null"       { imprimir_token(TOKEN_KW_NULL,  yytext); return TOKEN_KW_NULL;  }

"print"      { imprimir_token(TOKEN_KW_PRINT,   yytext); return TOKEN_KW_PRINT;   }
"println"    { imprimir_token(TOKEN_KW_PRINTLN, yytext); return TOKEN_KW_PRINTLN; }
"input"      { imprimir_token(TOKEN_KW_INPUT,   yytext); return TOKEN_KW_INPUT;   }

"func"       { imprimir_token(TOKEN_KW_FUNC, yytext); return TOKEN_KW_FUNC; }
"proc"       { imprimir_token(TOKEN_KW_PROC, yytext); return TOKEN_KW_PROC; }

"asm"        { imprimir_token(TOKEN_KW_ASM,       yytext); return TOKEN_KW_ASM;       }
"interrupt"  { imprimir_token(TOKEN_KW_INTERRUPT, yytext); return TOKEN_KW_INTERRUPT; }
"halt"       { imprimir_token(TOKEN_KW_HALT,      yytext); return TOKEN_KW_HALT;      }

"and"        { imprimir_token(TOKEN_KW_AND, yytext); return TOKEN_KW_AND; }
"or"         { imprimir_token(TOKEN_KW_OR,  yytext); return TOKEN_KW_OR;  }
"not"        { imprimir_token(TOKEN_KW_NOT, yytext); return TOKEN_KW_NOT; }

"new"        { imprimir_token(TOKEN_KW_NEW,    yytext); return TOKEN_KW_NEW;    }
"free"       { imprimir_token(TOKEN_KW_FREE,   yytext); return TOKEN_KW_FREE;   }
"sizeof"     { imprimir_token(TOKEN_KW_SIZEOF, yytext); return TOKEN_KW_SIZEOF; }

    /* --- 3.4 Mnemónicos de Ensamblador Inline DUOX (48 Opcodes nativos) --- */
"@asm_NOP"        { imprimir_token(TOKEN_ASM_NOP, yytext); return TOKEN_ASM_NOP; }
"@asm_ADD"        { imprimir_token(TOKEN_ASM_ADD, yytext); return TOKEN_ASM_ADD; }
"@asm_SUB"        { imprimir_token(TOKEN_ASM_SUB, yytext); return TOKEN_ASM_SUB; }
"@asm_MUL"        { imprimir_token(TOKEN_ASM_MUL, yytext); return TOKEN_ASM_MUL; }
"@asm_DIV"        { imprimir_token(TOKEN_ASM_DIV, yytext); return TOKEN_ASM_DIV; }
"@asm_MOD"        { imprimir_token(TOKEN_ASM_MOD, yytext); return TOKEN_ASM_MOD; }
"@asm_AND"        { imprimir_token(TOKEN_ASM_AND, yytext); return TOKEN_ASM_AND; }
"@asm_OR"         { imprimir_token(TOKEN_ASM_OR,  yytext); return TOKEN_ASM_OR;  }
"@asm_XOR"        { imprimir_token(TOKEN_ASM_XOR, yytext); return TOKEN_ASM_XOR; }
"@asm_NOT"        { imprimir_token(TOKEN_ASM_NOT, yytext); return TOKEN_ASM_NOT; }
"@asm_SHL"        { imprimir_token(TOKEN_ASM_SHL, yytext); return TOKEN_ASM_SHL; }
"@asm_SHR"        { imprimir_token(TOKEN_ASM_SHR, yytext); return TOKEN_ASM_SHR; }

"@asm_PUSH"       { imprimir_token(TOKEN_ASM_PUSH,      yytext); return TOKEN_ASM_PUSH;      }
"@asm_POP"        { imprimir_token(TOKEN_ASM_POP,       yytext); return TOKEN_ASM_POP;       }
"@asm_DUP"        { imprimir_token(TOKEN_ASM_DUP,       yytext); return TOKEN_ASM_DUP;       }
"@asm_SWAP"       { imprimir_token(TOKEN_ASM_SWAP,      yytext); return TOKEN_ASM_SWAP;      }
"@asm_LOAD_OFF"   { imprimir_token(TOKEN_ASM_LOAD_OFF,  yytext); return TOKEN_ASM_LOAD_OFF;  }
"@asm_STORE_OFF"  { imprimir_token(TOKEN_ASM_STORE_OFF, yytext); return TOKEN_ASM_STORE_OFF; }
"@asm_LOAD_IMM"   { imprimir_token(TOKEN_ASM_LOAD_IMM,  yytext); return TOKEN_ASM_LOAD_IMM;  }
"@asm_LOAD"       { imprimir_token(TOKEN_ASM_LOAD,      yytext); return TOKEN_ASM_LOAD;      }
"@asm_STORE"      { imprimir_token(TOKEN_ASM_STORE,     yytext); return TOKEN_ASM_STORE;     }

"@asm_JMP"        { imprimir_token(TOKEN_ASM_JMP,  yytext); return TOKEN_ASM_JMP;  }
"@asm_JZ"         { imprimir_token(TOKEN_ASM_JZ,   yytext); return TOKEN_ASM_JZ;   }
"@asm_JNZ"        { imprimir_token(TOKEN_ASM_JNZ,  yytext); return TOKEN_ASM_JNZ;  }
"@asm_JGT"        { imprimir_token(TOKEN_ASM_JGT,  yytext); return TOKEN_ASM_JGT;  }
"@asm_JLT"        { imprimir_token(TOKEN_ASM_JLT,  yytext); return TOKEN_ASM_JLT;  }
"@asm_CALL"       { imprimir_token(TOKEN_ASM_CALL, yytext); return TOKEN_ASM_CALL; }
"@asm_RET"        { imprimir_token(TOKEN_ASM_RET,  yytext); return TOKEN_ASM_RET;  }
"@asm_HALT"       { imprimir_token(TOKEN_ASM_HALT, yytext); return TOKEN_ASM_HALT; }

"@asm_CORE_START" { imprimir_token(TOKEN_ASM_CORE_START, yytext); return TOKEN_ASM_CORE_START; }
"@asm_CORE_YIELD" { imprimir_token(TOKEN_ASM_CORE_YIELD, yytext); return TOKEN_ASM_CORE_YIELD; }
"@asm_GET_CORE"   { imprimir_token(TOKEN_ASM_GET_CORE,   yytext); return TOKEN_ASM_GET_CORE;   }
"@asm_LOCK"       { imprimir_token(TOKEN_ASM_LOCK,       yytext); return TOKEN_ASM_LOCK;       }
"@asm_UNLOCK"     { imprimir_token(TOKEN_ASM_UNLOCK,     yytext); return TOKEN_ASM_UNLOCK;     }

"@asm_IN_PORT"    { imprimir_token(TOKEN_ASM_IN_PORT,  yytext); return TOKEN_ASM_IN_PORT;  }
"@asm_OUT_PORT"   { imprimir_token(TOKEN_ASM_OUT_PORT, yytext); return TOKEN_ASM_OUT_PORT; }
"@asm_NET_SEND"   { imprimir_token(TOKEN_ASM_NET_SEND, yytext); return TOKEN_ASM_NET_SEND; }
"@asm_NET_RECV"   { imprimir_token(TOKEN_ASM_NET_RECV, yytext); return TOKEN_ASM_NET_RECV; }
"@asm_NET_STAT"   { imprimir_token(TOKEN_ASM_NET_STAT, yytext); return TOKEN_ASM_NET_STAT; }
"@asm_OUT"        { imprimir_token(TOKEN_ASM_OUT,      yytext); return TOKEN_ASM_OUT;      }

"@asm_CACHE_FLUSH" { imprimir_token(TOKEN_ASM_CACHE_FLUSH, yytext); return TOKEN_ASM_CACHE_FLUSH; }
"@asm_MEM_COPY"    { imprimir_token(TOKEN_ASM_MEM_COPY,    yytext); return TOKEN_ASM_MEM_COPY;    }
"@asm_SET_FLAGS"   { imprimir_token(TOKEN_ASM_SET_FLAGS,   yytext); return TOKEN_ASM_SET_FLAGS;   }
"@asm_GET_FLAGS"   { imprimir_token(TOKEN_ASM_GET_FLAGS,   yytext); return TOKEN_ASM_GET_FLAGS;   }
"@asm_INT"         { imprimir_token(TOKEN_ASM_INT,         yytext); return TOKEN_ASM_INT;         }
"@asm_IRET"        { imprimir_token(TOKEN_ASM_IRET,        yytext); return TOKEN_ASM_IRET;        }
"@asm_EI"          { imprimir_token(TOKEN_ASM_EI,          yytext); return TOKEN_ASM_EI;          }
"@asm_DI"          { imprimir_token(TOKEN_ASM_DI,          yytext); return TOKEN_ASM_DI;          }

    /* --- 3.5 Identificadores --- */
{ID}    { imprimir_token(TOKEN_ID, yytext); return TOKEN_ID; }

    /* --- 3.6 Literales Numéricos --- */
{FLOAT_NUM}    { imprimir_token(TOKEN_LIT_FLOAT, yytext); return TOKEN_LIT_FLOAT; }
{INT_BIN}      { imprimir_token(TOKEN_LIT_BIN,   yytext); return TOKEN_LIT_BIN;   }
{INT_HEX}      { imprimir_token(TOKEN_LIT_HEX,   yytext); return TOKEN_LIT_HEX;   }
{INT_DEC}      { imprimir_token(TOKEN_LIT_INT,   yytext); return TOKEN_LIT_INT;   }

    /* --- 3.7 Literales de Carácter --- */
{CHAR_LIT}    { imprimir_token(TOKEN_LIT_CHAR, yytext); return TOKEN_LIT_CHAR; }

'({ESC_SEQ}|[^'\\\n])*\n {
    reporte_error(yytext, "literal de carácter sin cerrar (falta comilla simple)");
    return TOKEN_ERROR;
}

    /* --- 3.8 Literales de Cadena --- */
{STR_LIT}     { imprimir_token(TOKEN_LIT_STR, yytext); return TOKEN_LIT_STR; }

\"({ESC_SEQ}|[^"\\\n])*\n {
    reporte_error(yytext, "cadena de texto sin cerrar (falta comilla doble)");
    return TOKEN_ERROR;
}

    /* --- 3.9 Operadores --- */
"+="    { imprimir_token(TOKEN_OP_PLUS_EQ,  yytext); return TOKEN_OP_PLUS_EQ;  }
"-="    { imprimir_token(TOKEN_OP_MINUS_EQ, yytext); return TOKEN_OP_MINUS_EQ; }
"*="    { imprimir_token(TOKEN_OP_MUL_EQ,   yytext); return TOKEN_OP_MUL_EQ;   }
"/="    { imprimir_token(TOKEN_OP_DIV_EQ,   yytext); return TOKEN_OP_DIV_EQ;   }
"%="    { imprimir_token(TOKEN_OP_MOD_EQ,   yytext); return TOKEN_OP_MOD_EQ;   }

"=="    { imprimir_token(TOKEN_OP_EQ,  yytext); return TOKEN_OP_EQ;  }
"!="    { imprimir_token(TOKEN_OP_NEQ, yytext); return TOKEN_OP_NEQ; }
"<="    { imprimir_token(TOKEN_OP_LE,  yytext); return TOKEN_OP_LE;  }
">="    { imprimir_token(TOKEN_OP_GE,  yytext); return TOKEN_OP_GE;  }

"&&"    { imprimir_token(TOKEN_OP_LAND, yytext); return TOKEN_OP_LAND; }
"||"    { imprimir_token(TOKEN_OP_LOR,  yytext); return TOKEN_OP_LOR;  }

"<<"    { imprimir_token(TOKEN_OP_SHL, yytext); return TOKEN_OP_SHL; }
">>"    { imprimir_token(TOKEN_OP_SHR, yytext); return TOKEN_OP_SHR; }

"**"    { imprimir_token(TOKEN_OP_POW, yytext); return TOKEN_OP_POW; }
"->"    { imprimir_token(TOKEN_OP_ARROW, yytext); return TOKEN_OP_ARROW; }
"=>"    { imprimir_token(TOKEN_ARROW_FAT, yytext); return TOKEN_ARROW_FAT; }

"<"     { imprimir_token(TOKEN_OP_LT, yytext); return TOKEN_OP_LT; }
">"     { imprimir_token(TOKEN_OP_GT, yytext); return TOKEN_OP_GT; }
"="     { imprimir_token(TOKEN_OP_ASSIGN, yytext); return TOKEN_OP_ASSIGN; }

"+"     { imprimir_token(TOKEN_OP_PLUS,  yytext); return TOKEN_OP_PLUS;  }
"-"     { imprimir_token(TOKEN_OP_MINUS, yytext); return TOKEN_OP_MINUS; }
"*"     { imprimir_token(TOKEN_OP_MUL,   yytext); return TOKEN_OP_MUL;   }
"/"     { imprimir_token(TOKEN_OP_DIV,   yytext); return TOKEN_OP_DIV;   }
"%"     { imprimir_token(TOKEN_OP_MOD,   yytext); return TOKEN_OP_MOD;   }

"&"     { imprimir_token(TOKEN_OP_BAND, yytext); return TOKEN_OP_BAND; }
"|"     { imprimir_token(TOKEN_OP_BOR,  yytext); return TOKEN_OP_BOR;  }
"^"     { imprimir_token(TOKEN_OP_BXOR, yytext); return TOKEN_OP_BXOR; }
"~"     { imprimir_token(TOKEN_OP_BNOT, yytext); return TOKEN_OP_BNOT; }
"!"     { imprimir_token(TOKEN_OP_LNOT, yytext); return TOKEN_OP_LNOT; }

    /* --- 3.10 Delimitadores y Puntuación --- */
"("     { imprimir_token(TOKEN_LPAREN,    yytext); return TOKEN_LPAREN;    }
")"     { imprimir_token(TOKEN_RPAREN,    yytext); return TOKEN_RPAREN;    }
"{"     { imprimir_token(TOKEN_LBRACE,    yytext); return TOKEN_LBRACE;    }
"}"     { imprimir_token(TOKEN_RBRACE,    yytext); return TOKEN_RBRACE;    }
"["     { imprimir_token(TOKEN_OP_LBRACKET, yytext); return TOKEN_OP_LBRACKET; }
"]"     { imprimir_token(TOKEN_OP_RBRACKET, yytext); return TOKEN_OP_RBRACKET; }
";"     { imprimir_token(TOKEN_SEMI,      yytext); return TOKEN_SEMI;      }
","     { imprimir_token(TOKEN_COMMA,     yytext); return TOKEN_COMMA;     }
"::"    { imprimir_token(TOKEN_DCOLON,    yytext); return TOKEN_DCOLON;    }
":"     { imprimir_token(TOKEN_COLON,     yytext); return TOKEN_COLON;     }
"."     { imprimir_token(TOKEN_OP_DOT,    yytext); return TOKEN_OP_DOT;    }
"@"     { imprimir_token(TOKEN_AT,        yytext); return TOKEN_AT;        }

    /* --- 3.11 Regla de Error (Catch-all) --- */
.   {
    reporte_error(yytext, "carácter no reconocido en el vocabulario de DUOXC");
    return TOKEN_ERROR;
}

%%

/* ============================================================================
 * SECCIÓN 4: CÓDIGO C AUXILIAR
 * ============================================================================ */

const char *token_nombre(int tok) {
    switch (tok) {
        /* Palabras reservadas - Control de flujo */
        case TOKEN_KW_IF:          return "KW_IF";
        case TOKEN_KW_ELIF:        return "KW_ELIF";
        case TOKEN_KW_ELSE:        return "KW_ELSE";
        case TOKEN_KW_FI:          return "KW_FI";
        case TOKEN_KW_WHILE:       return "KW_WHILE";
        case TOKEN_KW_DO:          return "KW_DO";
        case TOKEN_KW_DONE:        return "KW_DONE";
        case TOKEN_KW_FOR:         return "KW_FOR";
        case TOKEN_KW_IN:          return "KW_IN";
        case TOKEN_KW_BREAK:       return "KW_BREAK";
        case TOKEN_KW_CONTINUE:    return "KW_CONTINUE";
        case TOKEN_KW_RETURN:      return "KW_RETURN";
        /* Palabras reservadas - Tipos */
        case TOKEN_KW_INT:         return "KW_INT";
        case TOKEN_KW_FLOAT:       return "KW_FLOAT";
        case TOKEN_KW_CHAR:        return "KW_CHAR";
        case TOKEN_KW_BOOL:        return "KW_BOOL";
        case TOKEN_KW_STRING:      return "KW_STRING";
        case TOKEN_KW_VOID:        return "KW_VOID";
        case TOKEN_KW_STRUCT:      return "KW_STRUCT";
        case TOKEN_KW_ARRAY:       return "KW_ARRAY";
        case TOKEN_KW_MATRIX:      return "KW_MATRIX";
        /* Palabras reservadas - Literales booleanos */
        case TOKEN_KW_TRUE:        return "KW_TRUE";
        case TOKEN_KW_FALSE:       return "KW_FALSE";
        case TOKEN_KW_NULL:        return "KW_NULL";
        /* Palabras reservadas - E/S */
        case TOKEN_KW_PRINT:       return "KW_PRINT";
        case TOKEN_KW_PRINTLN:     return "KW_PRINTLN";
        case TOKEN_KW_INPUT:       return "KW_INPUT";
        /* Palabras reservadas - Subprogramas */
        case TOKEN_KW_FUNC:        return "KW_FUNC";
        case TOKEN_KW_PROC:        return "KW_PROC";
        /* Palabras reservadas - Hardware */
        case TOKEN_KW_ASM:         return "KW_ASM";
        case TOKEN_KW_INTERRUPT:   return "KW_INTERRUPT";
        case TOKEN_KW_HALT:        return "KW_HALT";
        /* Palabras reservadas - Lógicos */
        case TOKEN_KW_AND:         return "KW_AND";
        case TOKEN_KW_OR:          return "KW_OR";
        case TOKEN_KW_NOT:         return "KW_NOT";
        /* Palabras reservadas - Memoria dinámica */
        case TOKEN_KW_NEW:         return "KW_NEW";
        case TOKEN_KW_FREE:        return "KW_FREE";
        case TOKEN_KW_SIZEOF:      return "KW_SIZEOF";
        /* Identificadores y literales */
        case TOKEN_ID:             return "IDENTIFICADOR";
        case TOKEN_LIT_INT:        return "LIT_ENTERO_DEC";
        case TOKEN_LIT_HEX:        return "LIT_ENTERO_HEX";
        case TOKEN_LIT_BIN:        return "LIT_ENTERO_BIN";
        case TOKEN_LIT_FLOAT:      return "LIT_FLOTANTE";
        case TOKEN_LIT_CHAR:       return "LIT_CARACTER";
        case TOKEN_LIT_STR:        return "LIT_CADENA";
        /* Operadores aritméticos */
        case TOKEN_OP_PLUS:        return "OP_SUMA";
        case TOKEN_OP_MINUS:       return "OP_RESTA";
        case TOKEN_OP_MUL:         return "OP_MULTIPLICACION";
        case TOKEN_OP_DIV:         return "OP_DIVISION";
        case TOKEN_OP_MOD:         return "OP_MODULO";
        case TOKEN_OP_POW:         return "OP_POTENCIA";
        /* Operadores de comparación */
        case TOKEN_OP_EQ:          return "OP_IGUAL";
        case TOKEN_OP_NEQ:         return "OP_DIFERENTE";
        case TOKEN_OP_LT:          return "OP_MENOR";
        case TOKEN_OP_GT:          return "OP_MAYOR";
        case TOKEN_OP_LE:          return "OP_MENOR_IGUAL";
        case TOKEN_OP_GE:          return "OP_MAYOR_IGUAL";
        /* Operadores lógicos */
        case TOKEN_OP_LAND:        return "OP_Y_LOGICO";
        case TOKEN_OP_LOR:         return "OP_O_LOGICO";
        case TOKEN_OP_LNOT:        return "OP_NO_LOGICO";
        /* Operadores de bits */
        case TOKEN_OP_BAND:        return "OP_AND_BITS";
        case TOKEN_OP_BOR:         return "OP_OR_BITS";
        case TOKEN_OP_BXOR:        return "OP_XOR_BITS";
        case TOKEN_OP_BNOT:        return "OP_NOT_BITS";
        case TOKEN_OP_SHL:         return "OP_DESP_IZQ";
        case TOKEN_OP_SHR:         return "OP_DESP_DER";
        /* Operadores de asignación */
        case TOKEN_OP_ASSIGN:      return "OP_ASIGNACION";
        case TOKEN_OP_PLUS_EQ:     return "OP_ASIG_SUMA";
        case TOKEN_OP_MINUS_EQ:    return "OP_ASIG_RESTA";
        case TOKEN_OP_MUL_EQ:      return "OP_ASIG_MUL";
        case TOKEN_OP_DIV_EQ:      return "OP_ASIG_DIV";
        case TOKEN_OP_MOD_EQ:      return "OP_ASIG_MOD";
        /* Acceso */
        case TOKEN_OP_DOT:         return "OP_PUNTO";
        case TOKEN_OP_ARROW:       return "OP_FLECHA";
        case TOKEN_OP_LBRACKET:    return "DELIM_CORCHETE_ABR";
        case TOKEN_OP_RBRACKET:    return "DELIM_CORCHETE_CIE";
        case TOKEN_OP_AMP:         return "OP_AMPERSAND";
        /* Delimitadores */
        case TOKEN_LPAREN:         return "DELIM_PAREN_ABR";
        case TOKEN_RPAREN:         return "DELIM_PAREN_CIE";
        case TOKEN_LBRACE:         return "DELIM_LLAVE_ABR";
        case TOKEN_RBRACE:         return "DELIM_LLAVE_CIE";
        case TOKEN_SEMI:           return "DELIM_PUNTO_COMA";
        case TOKEN_COMMA:          return "DELIM_COMA";
        case TOKEN_COLON:          return "DELIM_DOS_PUNTOS";
        case TOKEN_DCOLON:         return "DELIM_AMBITO";
        case TOKEN_ARROW_FAT:      return "DELIM_FLECHA_FAT";
        case TOKEN_AT:             return "DELIM_ARROBA";
        /* Mnemónicos ISA DUOX */
        case TOKEN_ASM_NOP:        return "ASM_NOP";
        case TOKEN_ASM_ADD:        return "ASM_ADD";
        case TOKEN_ASM_SUB:        return "ASM_SUB";
        case TOKEN_ASM_MUL:        return "ASM_MUL";
        case TOKEN_ASM_DIV:        return "ASM_DIV";
        case TOKEN_ASM_MOD:        return "ASM_MOD";
        case TOKEN_ASM_AND:        return "ASM_AND";
        case TOKEN_ASM_OR:         return "ASM_OR";
        case TOKEN_ASM_XOR:        return "ASM_XOR";
        case TOKEN_ASM_NOT:        return "ASM_NOT";
        case TOKEN_ASM_SHL:        return "ASM_SHL";
        case TOKEN_ASM_SHR:        return "ASM_SHR";
        case TOKEN_ASM_PUSH:       return "ASM_PUSH";
        case TOKEN_ASM_POP:        return "ASM_POP";
        case TOKEN_ASM_DUP:        return "ASM_DUP";
        case TOKEN_ASM_SWAP:       return "ASM_SWAP";
        case TOKEN_ASM_LOAD:       return "ASM_LOAD";
        case TOKEN_ASM_STORE:      return "ASM_STORE";
        case TOKEN_ASM_LOAD_OFF:   return "ASM_LOAD_OFF";
        case TOKEN_ASM_STORE_OFF:  return "ASM_STORE_OFF";
        case TOKEN_ASM_LOAD_IMM:   return "ASM_LOAD_IMM";
        case TOKEN_ASM_JMP:        return "ASM_JMP";
        case TOKEN_ASM_JZ:         return "ASM_JZ";
        case TOKEN_ASM_JNZ:        return "ASM_JNZ";
        case TOKEN_ASM_JGT:        return "ASM_JGT";
        case TOKEN_ASM_JLT:        return "ASM_JLT";
        case TOKEN_ASM_CALL:       return "ASM_CALL";
        case TOKEN_ASM_RET:        return "ASM_RET";
        case TOKEN_ASM_HALT:       return "ASM_HALT";
        case TOKEN_ASM_GET_CORE:   return "ASM_GET_CORE";
        case TOKEN_ASM_LOCK:       return "ASM_LOCK";
        case TOKEN_ASM_UNLOCK:     return "ASM_UNLOCK";
        case TOKEN_ASM_CORE_START: return "ASM_CORE_START";
        case TOKEN_ASM_CORE_YIELD: return "ASM_CORE_YIELD";
        case TOKEN_ASM_IN_PORT:    return "ASM_IN_PORT";
        case TOKEN_ASM_OUT_PORT:   return "ASM_OUT_PORT";
        case TOKEN_ASM_NET_SEND:   return "ASM_NET_SEND";
        case TOKEN_ASM_NET_RECV:   return "ASM_NET_RECV";
        case TOKEN_ASM_NET_STAT:   return "ASM_NET_STAT";
        case TOKEN_ASM_OUT:        return "ASM_OUT";
        case TOKEN_ASM_CACHE_FLUSH: return "ASM_CACHE_FLUSH";
        case TOKEN_ASM_MEM_COPY:   return "ASM_MEM_COPY";
        case TOKEN_ASM_SET_FLAGS:  return "ASM_SET_FLAGS";
        case TOKEN_ASM_GET_FLAGS:  return "ASM_GET_FLAGS";
        case TOKEN_ASM_INT:        return "ASM_INT";
        case TOKEN_ASM_IRET:       return "ASM_IRET";
        case TOKEN_ASM_EI:         return "ASM_EI";
        case TOKEN_ASM_DI:         return "ASM_DI";
        /* Error */
        case TOKEN_ERROR:          return "ERROR_LEXICO";
        default:                   return "DESCONOCIDO";
    }
}

void imprimir_token(int tok, const char *lexema) {
    total_tokens++;
    printf("[L%4d] [ID %3d] [%-22s] \"%s\"\n",
           yylineno,
           tok,
           token_nombre(tok),
           lexema);
}

void reporte_error(const char *lexema, const char *razon) {
    total_errores++;
    fprintf(stderr,
            "[ERROR LÉXICO] Línea %d: %s --> \"%s\"\n",
            yylineno, razon, lexema);
}

int main(int argc, char *argv[]) {
    FILE *archivo = NULL;

    printf("=================================================================\n");
    printf("  ANALIZADOR LÉXICO - COMPILADOR DUOXC\n");
    printf("  Máquina destino: DUOX / DUOS (pila 64 bits) - Grupo F\n");
    printf("  Taller #01 - LP02-DUOX\n");
    printf("=================================================================\n");

    if (argc >= 2) {
        archivo = fopen(argv[1], "r");
        if (!archivo) {
            fprintf(stderr, "[ERROR] No se puede abrir el archivo: %s\n", argv[1]);
            return EXIT_FAILURE;
        }
        printf("  Archivo fuente: %s\n", argv[1]);
        yyin = archivo;
    } else {
        printf("  Fuente: stdin (escribe código DUOXC, Ctrl+D para terminar)\n");
        yyin = stdin;
    }

    printf("-----------------------------------------------------------------\n");
    printf("  %-6s  %-5s  %-24s  %s\n", "LÍNEA", "ID", "CATEGORÍA", "LEXEMA");
    printf("-----------------------------------------------------------------\n");

    int tok;
    while ((tok = yylex()) != 0) {
        if (tok == TOKEN_ERROR) {
            /* Error ya reportado */
        }
    }

    printf("=================================================================\n");
    printf("  RESUMEN DEL ANÁLISIS LÉXICO\n");
    printf("-----------------------------------------------------------------\n");
    printf("  Tokens reconocidos correctamente : %d\n", total_tokens);
    printf("  Líneas procesadas               : %d\n", yylineno);
    printf("  Errores léxicos detectados      : %d\n", total_errores);
    printf("=================================================================\n");

    if (archivo) fclose(archivo);
    return (total_errores == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
