/* pp.h - interfaz del preprocesador DUOS: tabla de macros y arranque. */
#ifndef PP_H
#define PP_H

#include <stddef.h>

#define PP_MAX_PARAMS  16
#define PP_MAX_TEXTO   8192

typedef struct Macro {
    char  *nombre;
    int    nparams;                  /* -1 = macro objeto; >= 0 = con parámetros */
    char  *params[PP_MAX_PARAMS];
    char  *cuerpo;
    struct Macro *sig;
} Macro;

extern int pp_fallos;

Macro *macro_buscar(const char *nombre);
int    macro_definir(const char *nombre, char **params, int nparams, const char *cuerpo);
int    macro_borrar(const char *nombre);
void   macro_liberar(void);

void   pp_agregar_ruta(const char *dir);
int    pp_definir_cli(const char *definicion);
int    pp_iniciar(const char *ruta);

#endif
