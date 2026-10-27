/* pp.l - preprocesador del SPL de DUOS (FLEX).
 *
 * Reconoce, al inicio de línea, las macros de incluir y definir, las
 * condicionales y el resto de directivas; expande las macros en el texto y
 * copia sin tocar cadenas, caracteres y comentarios. La pila de buffers de
 * FLEX es la que resuelve #include y las expansiones anidadas.
 */
%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include "pp.h"

#define MAX_PILA    256
#define MAX_COND    128
#define MAX_RUTAS    16
#define MAX_ANIDAR   32
#define MAX_ACTIVAS  64

typedef enum { F_ARCHIVO, F_EXPANSION } TipoFuente;

typedef struct {
    struct yy_buffer_state *buf;
    FILE *archivo;
    TipoFuente tipo;
    char *nombre;
    char *dir;
    const char *activa;
    int linea;
    int cond_al_entrar;
} Fuente;

static Fuente pila[MAX_PILA];
static int tope = -1;
static const char *activas[MAX_ACTIVAS];
static int nactivas = 0;
static char *rutas[MAX_RUTAS];
static int nrutas = 0;
static struct { int padre, rama, visto_else, linea; } cond[MAX_COND];
static int ncond = 0;
static int anidados = 0;

int pp_fallos = 0;

#define ACTIVO (ncond == 0 || (cond[ncond - 1].padre && cond[ncond - 1].rama))

static void emitir(void);
static void contar(const char *);
static void errorf(const char *, ...);
static void aviso(const char *, ...);
static void empujar(struct yy_buffer_state *, TipoFuente, char *, char *, const char *, FILE *, int);
static void desempujar(void);
static void expandir(const char *, const char *);
static int  activa(const char *);
static void incluir(const char *, int);
static char *dir_de(const char *);
static void dir_include(const char *);
static void dir_define(const char *);
static void dir_undef(const char *);
static void dir_cond(const char *, int, int);
static void dir_else(void);
static void dir_endif(void);
static void dir_error(const char *);
static void identificador(const char *);
static void llamada(const char *, size_t);
static int  leer_argumentos(char *, size_t);
static int  separar_args(char *, char **, int);
static char *sustituir(const Macro *, char **, int);
static char *recortar(const char *, const char *);
static char *sin_continuaciones(const char *);
%}

%option noyywrap nodefault nounput 8bit

ESP      [ \t]
NL       \r?\n
NOMBRE   [A-Za-z_][A-Za-z0-9_]*
CADENA   \"[^\"\n]*\"
ANGULO   "<"[^>\n]*">"
COMENT   ({ESP}*(";"|\/\/)[^\n]*)?
CUERPO   ([^\\\n]|\\{NL}|\\[^\n])*
PARAMS   \({ESP}*({NOMBRE}{ESP}*(,{ESP}*{NOMBRE}{ESP}*)*)?\)

INCLUDE  [Ii][Nn][Cc][Ll][Uu][Dd][Ee]
DEFINE   [Dd][Ee][Ff][Ii][Nn][Ee]
UNDEF    [Uu][Nn][Dd][Ee][Ff]
IFDEF    [Ii][Ff][Dd][Ee][Ff]
IFNDEF   [Ii][Ff][Nn][Dd][Ee][Ff]
ELSE     [Ee][Ll][Ss][Ee]
ENDIF    [Ee][Nn][Dd][Ii][Ff]
ERROR    [Ee][Rr][Rr][Oo][Rr]

%%
^{ESP}*"#"{ESP}*{INCLUDE}{ESP}+({CADENA}|{ANGULO}){COMENT}{ESP}*{NL}?   { contar(yytext); dir_include(yytext); }
^{ESP}*"."{ESP}*{INCLUDE}{ESP}+({CADENA}|{ANGULO}){COMENT}{ESP}*{NL}?   { contar(yytext); dir_include(yytext); }
^{ESP}*"#"{ESP}*{DEFINE}{ESP}+{NOMBRE}{PARAMS}?([ \t]+{CUERPO})?{NL}?   { dir_define(yytext); contar(yytext); }
^{ESP}*"#"{ESP}*{UNDEF}{ESP}+{NOMBRE}{COMENT}{ESP}*{NL}?                { dir_undef(yytext); contar(yytext); }
^{ESP}*"#"{ESP}*{IFDEF}{ESP}+{NOMBRE}{COMENT}{ESP}*{NL}?                { dir_cond(yytext, 5, 0); contar(yytext); }
^{ESP}*"#"{ESP}*{IFNDEF}{ESP}+{NOMBRE}{COMENT}{ESP}*{NL}?               { dir_cond(yytext, 6, 1); contar(yytext); }
^{ESP}*"#"{ESP}*{ELSE}{COMENT}{ESP}*{NL}?                               { dir_else(); contar(yytext); }
^{ESP}*"#"{ESP}*{ENDIF}{COMENT}{ESP}*{NL}?                              { dir_endif(); contar(yytext); }
^{ESP}*"#"{ESP}*{ERROR}{ESP}+[^\n]*{NL}?                                { dir_error(yytext); contar(yytext); }
^{ESP}*"#"{ESP}*{NOMBRE}[^\n]*{NL}?                                     { if (ACTIVO) errorf("directiva no soportada: %.*s", (int)strcspn(yytext, "\r\n"), yytext); contar(yytext); }
^{ESP}*"."[A-Za-z_][A-Za-z0-9_]*                                        { emitir(); }

{NOMBRE}{ESP}*"("   { llamada(yytext, (size_t)(strcspn(yytext, " \t("))); }
{NOMBRE}            { identificador(yytext); }
{CADENA}            { emitir(); }
"'"([^'\\\n]|\\.)*"'"   { emitir(); }
";"[^\n]*           { emitir(); }
"//"[^\n]*          { emitir(); }
"/*"([^*]|\*+[^*/])*\*+"/"  { emitir(); contar(yytext); }
{NL}                { emitir(); contar(yytext); }
[ \t\r]+            { emitir(); }
.                   { emitir(); }
<<EOF>>             { if (tope <= 0) { if (ncond) errorf("faltó #endif (el #if de la línea %d quedó abierto)", cond[ncond - 1].linea); yyterminate(); } desempujar(); if (tope < 0) yyterminate(); }

%%
/* ------------------------------------------------------------- utilidades */

static void contar(const char *s) {
    if (tope < 0)
        return;
    for (; *s; s++)
        if (*s == '\n')
            pila[tope].linea++;
}

static void errorf(const char *fmt, ...) {
    va_list ap;
    if (tope >= 0)
        fprintf(stderr, "%s:%d: error: ", pila[tope].nombre, pila[tope].linea);
    else
        fprintf(stderr, "pp: error: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
    pp_fallos++;
}

static void aviso(const char *fmt, ...) {
    va_list ap;
    if (tope >= 0)
        fprintf(stderr, "%s:%d: aviso: ", pila[tope].nombre, pila[tope].linea);
    else
        fprintf(stderr, "pp: aviso: ");
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

static void emitir(void) {
    if (ACTIVO)
        fputs(yytext, yyout);
}

static void empujar(struct yy_buffer_state *buf, TipoFuente tipo, char *nombre, char *dir,
                    const char *act, FILE *archivo, int linea) {
    if (tope + 1 >= MAX_PILA) {
        errorf("demasiados niveles de inclusión o expansión");
        return;
    }
    tope++;
    pila[tope].buf = buf;
    pila[tope].archivo = archivo;
    pila[tope].tipo = tipo;
    pila[tope].nombre = nombre;
    pila[tope].dir = dir;
    pila[tope].activa = act;
    pila[tope].linea = linea;
    pila[tope].cond_al_entrar = ncond;
    yy_switch_to_buffer(buf);
}

static void desempujar(void) {
    Fuente *f = &pila[tope];
    if (ncond != f->cond_al_entrar) {
        errorf("%s terminó con %d bloque(s) condicional(es) sin cerrar",
               f->nombre, ncond - f->cond_al_entrar);
        ncond = f->cond_al_entrar;
    }
    if (f->tipo == F_ARCHIVO) {
        if (f->archivo)
            fclose(f->archivo);
        anidados--;
    } else if (nactivas > 0) {
        nactivas--;
    }
    yy_delete_buffer(f->buf);
    free(f->nombre);
    free(f->dir);
    tope--;
    if (tope >= 0)
        yy_switch_to_buffer(pila[tope].buf);
}

static int activa(const char *nombre) {
    for (int i = 0; i < nactivas; i++)
        if (strcmp(activas[i], nombre) == 0)
            return 1;
    return 0;
}

static void expandir(const char *texto, const char *macro) {
    if (nactivas >= MAX_ACTIVAS || tope + 1 >= MAX_PILA) {
        errorf("expansión de %s demasiado profunda", macro);
        return;
    }
    char *nombre = malloc(strlen(macro) + 16);
    if (!nombre) {
        errorf("sin memoria");
        return;
    }
    sprintf(nombre, "expansión de %s", macro);
    struct yy_buffer_state *b = yy_scan_string(texto);
    empujar(b, F_EXPANSION, nombre, strdup(tope >= 0 ? pila[tope].dir : "."), macro,
            NULL, tope >= 0 ? pila[tope].linea : 1);
    activas[nactivas++] = macro;
}

static char *dir_de(const char *ruta) {
    const char *barra = strrchr(ruta, '/');
    if (!barra)
        return strdup(".");
    size_t n = (size_t)(barra - ruta);
    if (n == 0)
        n = 1;
    char *d = malloc(n + 1);
    if (!d)
        return NULL;
    memcpy(d, ruta, n);
    d[n] = 0;
    return d;
}

static char *unir(const char *dir, const char *nombre) {
    size_t n = strlen(dir) + strlen(nombre) + 2;
    char *r = malloc(n);
    if (r)
        snprintf(r, n, "%s/%s", dir, nombre);
    return r;
}

static FILE *buscar(const char *dir, const char *pedido, char **resuelto) {
    char *ruta = unir(dir, pedido);
    if (!ruta)
        return NULL;
    FILE *f = fopen(ruta, "r");
    if (f)
        *resuelto = ruta;
    else
        free(ruta);
    return f;
}

static void incluir(const char *pedido, int angular) {
    if (anidados >= MAX_ANIDAR) {
        errorf("profundidad de #include excedida (%d)", MAX_ANIDAR);
        return;
    }
    char *resuelto = NULL;
    FILE *f = NULL;

    if (!angular && pedido[0] == '/') {
        f = fopen(pedido, "r");
        if (f)
            resuelto = strdup(pedido);
    }
    if (!f && !angular && tope >= 0)
        f = buscar(pila[tope].dir, pedido, &resuelto);
    for (int i = 0; !f && i < nrutas; i++)
        f = buscar(rutas[i], pedido, &resuelto);
    if (!f && !angular) {
        f = fopen(pedido, "r");
        if (f)
            resuelto = strdup(pedido);
    }
    if (!f) {
        errorf("no se encontró el archivo incluido \"%s\"", pedido);
        return;
    }
    struct yy_buffer_state *b = yy_create_buffer(f, YY_BUF_SIZE);
    empujar(b, F_ARCHIVO, resuelto, dir_de(resuelto), NULL, f, 1);
    anidados++;
}

/* ------------------------------------------------------------- directivas */

static const char *salta_blancos(const char *p) {
    while (*p == ' ' || *p == '\t')
        p++;
    return p;
}

static int lee_nombre(const char *p, char *destino, size_t max) {
    size_t n = 0;
    while ((isalnum((unsigned char)*p) || *p == '_') && n + 1 < max)
        destino[n++] = *p++;
    destino[n] = 0;
    return (int)n;
}

static void dir_include(const char *linea) {
    if (!ACTIVO)
        return;
    const char *p = strchr(linea, '"');
    char cierra = '"';
    int angular = 0;
    if (!p) {
        p = strchr(linea, '<');
        cierra = '>';
        angular = 1;
    }
    if (!p) {
        errorf("falta el nombre del archivo en #include");
        return;
    }
    const char *q = strchr(p + 1, cierra);
    if (!q) {
        errorf("falta '%c' en #include", cierra);
        return;
    }
    size_t n = (size_t)(q - p - 1);
    char pedido[1024];
    if (n >= sizeof pedido) {
        errorf("nombre de archivo demasiado largo");
        return;
    }
    memcpy(pedido, p + 1, n);
    pedido[n] = 0;
    incluir(pedido, angular);
}

static void dir_define(const char *linea) {
    if (!ACTIVO)
        return;
    const char *p = salta_blancos(linea);
    p = salta_blancos(p + 1);          /* '#', '.', etc. */
    p += 6;                            /* "define" */
    p = salta_blancos(p);

    char nombre[128];
    if (!lee_nombre(p, nombre, sizeof nombre)) {
        errorf("falta el nombre en #define");
        return;
    }
    p += strlen(nombre);

    char *params[PP_MAX_PARAMS];
    int nparams = -1;
    for (int i = 0; i < PP_MAX_PARAMS; i++)
        params[i] = NULL;

    if (*p == '(') {
        nparams = 0;
        p++;
        for (;;) {
            p = salta_blancos(p);
            if (*p == ')') {
                p++;
                break;
            }
            if (*p == ',') {
                p++;
                continue;
            }
            if (!*p) {
                errorf("falta ')' en los parámetros de %s", nombre);
                return;
            }
            const char *ini = p;
            while (isalnum((unsigned char)*p) || *p == '_')
                p++;
            if (p == ini) {
                errorf("parámetro inválido en %s", nombre);
                return;
            }
            if (nparams >= PP_MAX_PARAMS) {
                errorf("%s tiene demasiados parámetros", nombre);
                return;
            }
            for (int i = 0; i < nparams; i++)
                if (strlen(params[i]) == (size_t)(p - ini)
                    && strncmp(params[i], ini, (size_t)(p - ini)) == 0) {
                    errorf("parámetro repetido %.*s en %s", (int)(p - ini), ini, nombre);
                    return;
                }
            params[nparams++] = recortar(ini, p);
        }
    }
    p = salta_blancos(p);
    char *cuerpo = sin_continuaciones(p);
    if (!cuerpo) {
        errorf("sin memoria");
        return;
    }

    int r = macro_definir(nombre, params, nparams, cuerpo);
    for (int i = 0; i < nparams; i++)
        free(params[i]);
    free(cuerpo);
    if (r < 0)
        errorf("sin memoria al definir %s", nombre);
    else if (r == 2)
        aviso("%s redefinida con otro cuerpo", nombre);
}

static void dir_undef(const char *linea) {
    if (!ACTIVO)
        return;
    const char *p = salta_blancos(linea);
    p = salta_blancos(p + 1);
    p += 5;                            /* "undef" */
    p = salta_blancos(p);
    char nombre[128];
    if (!lee_nombre(p, nombre, sizeof nombre)) {
        errorf("falta el nombre en #undef");
        return;
    }
    macro_borrar(nombre);
}

static void dir_cond(const char *linea, int largo_kw, int negar) {
    const char *p = salta_blancos(linea);
    p = salta_blancos(p + 1);
    p += largo_kw;
    p = salta_blancos(p);
    char nombre[128];
    if (!lee_nombre(p, nombre, sizeof nombre)) {
        errorf("falta el nombre en #ifdef/#ifndef");
        return;
    }
    int existe = macro_buscar(nombre) != NULL;
    if (ncond >= MAX_COND) {
        errorf("demasiados bloques condicionales anidados");
        return;
    }
    cond[ncond].padre = ACTIVO;
    cond[ncond].rama = negar ? !existe : existe;
    cond[ncond].visto_else = 0;
    cond[ncond].linea = pila[tope].linea;
    ncond++;
}

static void dir_else(void) {
    if (ncond == 0) {
        errorf("#else sin #if");
        return;
    }
    if (cond[ncond - 1].visto_else) {
        errorf("#else repetido");
        return;
    }
    cond[ncond - 1].visto_else = 1;
    cond[ncond - 1].rama = !cond[ncond - 1].rama;
}

static void dir_endif(void) {
    if (ncond == 0) {
        errorf("#endif sin #if");
        return;
    }
    ncond--;
}

static void dir_error(const char *linea) {
    if (!ACTIVO)
        return;
    const char *p = salta_blancos(linea);
    p = salta_blancos(p + 1);
    p += 5;                            /* "error" */
    char *msg = recortar(p, p + strlen(p));
    errorf("%s", msg ? msg : "");
    free(msg);
}

/* ------------------------------------------------------------- expansión */

static void identificador(const char *nombre) {
    if (!ACTIVO)
        return;
    Macro *m = macro_buscar(nombre);
    if (!m || m->nparams >= 0 || activa(nombre)) {
        fputs(yytext, yyout);
        return;
    }
    expandir(m->cuerpo, m->nombre);
}

static void llamada(const char *texto, size_t largo) {
    if (!ACTIVO)
        return;
    char nombre[128];
    size_t n = largo < sizeof nombre - 1 ? largo : sizeof nombre - 1;
    memcpy(nombre, texto, n);
    nombre[n] = 0;

    Macro *m = macro_buscar(nombre);
    if (!m || activa(nombre)) {
        fputs(yytext, yyout);
        return;
    }
    if (m->nparams < 0) {
        /* macro objeto seguida de '(': se expande y se reinyecta el paréntesis */
        const char *cola = texto + largo;
        size_t cap = strlen(m->cuerpo) + strlen(cola) + 1;
        char *todo = malloc(cap);
        if (!todo) {
            errorf("sin memoria");
            return;
        }
        snprintf(todo, cap, "%s%s", m->cuerpo, cola);
        expandir(todo, m->nombre);
        free(todo);
        return;
    }

    char args_texto[PP_MAX_TEXTO];
    if (leer_argumentos(args_texto, sizeof args_texto) < 0)
        return;
    char *args[PP_MAX_PARAMS];
    int nargs = separar_args(args_texto, args, PP_MAX_PARAMS);
    if (nargs < 0) {
        errorf("demasiados argumentos en %s", nombre);
        return;
    }
    if (nargs != m->nparams) {
        errorf("%s espera %d argumento(s) y recibió %d", nombre, m->nparams, nargs);
        return;
    }
    char *res = sustituir(m, args, nargs);
    if (!res) {
        errorf("sin memoria al expandir %s", nombre);
        return;
    }
    expandir(res, m->nombre);
    free(res);
}

static int leer_argumentos(char *buf, size_t max) {
    int prof = 1, i = 0, c, en_cad = 0, esc = 0;
    while ((c = input()) != 0 && c != EOF) {
        if (c == '\n' && tope >= 0)
            pila[tope].linea++;
        if ((size_t)i + 2 >= max) {
            errorf("argumentos demasiado largos");
            return -1;
        }
        if (en_cad) {
            buf[i++] = (char)c;
            if (esc)
                esc = 0;
            else if (c == '\\')
                esc = 1;
            else if (c == '"')
                en_cad = 0;
            continue;
        }
        if (c == '"') {
            en_cad = 1;
            buf[i++] = (char)c;
            continue;
        }
        if (c == '(') {
            prof++;
        } else if (c == ')') {
            if (--prof == 0) {
                buf[i] = 0;
                return 0;
            }
        }
        buf[i++] = (char)c;
    }
    errorf("falta ')' en la llamada a la macro");
    return -1;
}

static int separar_args(char *texto, char **args, int max) {
    char *p = texto;
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')
        p++;
    if (!*p)
        return 0;

    int n = 0, prof = 0, en_cad = 0, esc = 0;
    char *ini = texto;
    for (p = texto;; p++) {
        char c = *p;
        if (en_cad) {
            if (esc)
                esc = 0;
            else if (c == '\\')
                esc = 1;
            else if (c == '"')
                en_cad = 0;
            continue;
        }
        if (c == '"') {
            en_cad = 1;
            continue;
        }
        if (c == '(') {
            prof++;
        } else if (c == ')' && prof > 0) {
            prof--;
        } else if ((c == ',' && prof == 0) || c == 0) {
            if (n >= max)
                return -1;
            args[n] = recortar(ini, p);
            if (!args[n])
                return -1;
            n++;
            ini = p + 1;
            if (c == 0)
                break;
        }
    }
    return n;
}

static char *sustituir(const Macro *m, char **args, int nargs) {
    size_t cap = strlen(m->cuerpo) + 32, len = 0;
    char *res = malloc(cap);
    if (!res)
        return NULL;
    for (const char *p = m->cuerpo; *p;) {
        size_t n;
        const char *txt = p;
        int k = -1;
        if (isalpha((unsigned char)*p) || *p == '_') {
            const char *q = p;
            while (isalnum((unsigned char)*q) || *q == '_')
                q++;
            for (int i = 0; i < nargs && i < m->nparams; i++)
                if (strlen(m->params[i]) == (size_t)(q - p)
                    && strncmp(m->params[i], p, (size_t)(q - p)) == 0) {
                    k = i;
                    break;
                }
            n = (size_t)(q - p);
            if (k >= 0) {
                txt = args[k];
                n = strlen(args[k]);
            }
            p = q;
        } else {
            n = 1;
            p++;
        }
        if (len + n + 1 > cap) {
            cap = (len + n + 1) * 2;
            char *nuevo = realloc(res, cap);
            if (!nuevo) {
                free(res);
                return NULL;
            }
            res = nuevo;
        }
        memcpy(res + len, txt, n);
        len += n;
    }
    res[len] = 0;
    return res;
}

static char *recortar(const char *ini, const char *fin) {
    while (ini < fin && isspace((unsigned char)*ini))
        ini++;
    while (fin > ini && isspace((unsigned char)fin[-1]))
        fin--;
    size_t n = (size_t)(fin - ini);
    char *s = malloc(n + 1);
    if (!s)
        return NULL;
    memcpy(s, ini, n);
    s[n] = 0;
    return s;
}

static char *sin_continuaciones(const char *s) {
    size_t n = strlen(s), len = 0;
    char *r = malloc(n + 1);
    if (!r)
        return NULL;
    for (size_t i = 0; i < n; i++) {
        if (s[i] == '\\' && s[i + 1] == '\n') {
            i++;
            continue;
        }
        if (s[i] == '\\' && s[i + 1] == '\r' && s[i + 2] == '\n') {
            i += 2;
            continue;
        }
        r[len++] = s[i];
    }
    while (len && isspace((unsigned char)r[len - 1]))
        len--;
    r[len] = 0;
    return r;
}

/* ---------------------------------------------------------------- arranque */

void pp_agregar_ruta(const char *dir) {
    if (nrutas < MAX_RUTAS)
        rutas[nrutas++] = strdup(dir);
}

int pp_definir_cli(const char *definicion) {
    char *copia = strdup(definicion);
    if (!copia)
        return 0;
    char *igual = strchr(copia, '=');
    if (igual)
        *igual++ = 0;
    int r = macro_definir(copia, NULL, -1, igual ? igual : "1");
    free(copia);
    return r >= 0;
}

int pp_iniciar(const char *ruta) {
    FILE *f = fopen(ruta, "r");
    if (!f) {
        fprintf(stderr, "pp: no se puede abrir \"%s\"\n", ruta);
        pp_fallos++;
        return 0;
    }
    struct yy_buffer_state *b = yy_create_buffer(f, YY_BUF_SIZE);
    empujar(b, F_ARCHIVO, strdup(ruta), dir_de(ruta), NULL, f, 1);
    anidados++;
    return 1;
}
