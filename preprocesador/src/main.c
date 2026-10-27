/* main.c - interfaz de línea de comandos del preprocesador DUOS. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pp.h"

extern FILE *yyout;
int yylex(void);

static void uso(FILE *f) {
    fprintf(f,
            "uso: pp [opciones] archivo\n"
            "  -o salida        escribe el resultado en 'salida' (por defecto stdout)\n"
            "  -I dir           agrega 'dir' a la búsqueda de #include <...>\n"
            "  -D NOMBRE[=val]  define una macro antes de procesar\n");
}

int main(int argc, char **argv) {
    const char *entrada = NULL, *salida = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            salida = argv[++i];
        } else if (strcmp(argv[i], "-I") == 0 && i + 1 < argc) {
            pp_agregar_ruta(argv[++i]);
        } else if (strcmp(argv[i], "-D") == 0 && i + 1 < argc) {
            if (!pp_definir_cli(argv[++i])) {
                fprintf(stderr, "pp: no se pudo definir \"%s\"\n", argv[i]);
                return 2;
            }
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            uso(stdout);
            return 0;
        } else if (argv[i][0] == '-') {
            fprintf(stderr, "pp: opción desconocida %s\n", argv[i]);
            uso(stderr);
            return 2;
        } else if (entrada) {
            fprintf(stderr, "pp: solo se procesa un archivo de entrada\n");
            return 2;
        } else {
            entrada = argv[i];
        }
    }
    if (!entrada) {
        uso(stderr);
        return 2;
    }

    FILE *out = salida ? fopen(salida, "w") : stdout;
    if (!out) {
        fprintf(stderr, "pp: no se puede crear \"%s\"\n", salida);
        return 2;
    }
    yyout = out;

    if (!pp_iniciar(entrada))
        return 1;
    yylex();

    if (out != stdout)
        fclose(out);
    if (pp_fallos)
        fprintf(stderr, "pp: %d error(es)\n", pp_fallos);
    macro_liberar();
    return pp_fallos ? 1 : 0;
}
