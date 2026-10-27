/* macros.c - tabla de macros: búsqueda, definición, borrado y liberación. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pp.h"

static Macro *tabla = NULL;

Macro *macro_buscar(const char *nombre) {
    for (Macro *m = tabla; m; m = m->sig)
        if (strcmp(m->nombre, nombre) == 0)
            return m;
    return NULL;
}

static void liberar(Macro *m) {
    free(m->nombre);
    free(m->cuerpo);
    for (int i = 0; i < m->nparams; i++)
        free(m->params[i]);
    free(m);
}

/* Devuelve 0 si es nueva, 1 si redefine igual, 2 si redefine distinto, -1 sin memoria. */
int macro_definir(const char *nombre, char **params, int nparams, const char *cuerpo) {
    Macro *nueva = calloc(1, sizeof *nueva);
    if (!nueva)
        return -1;
    nueva->nombre = strdup(nombre);
    nueva->cuerpo = strdup(cuerpo);
    nueva->nparams = nparams;
    for (int i = 0; i < nparams; i++)
        nueva->params[i] = strdup(params[i]);
    if (!nueva->nombre || !nueva->cuerpo)
        return -1;

    Macro *vieja = macro_buscar(nombre);
    if (!vieja) {
        nueva->sig = tabla;
        tabla = nueva;
        return 0;
    }

    int igual = vieja->nparams == nparams && strcmp(vieja->cuerpo, cuerpo) == 0;
    for (int i = 0; igual && i < nparams; i++)
        igual = strcmp(vieja->params[i], params[i]) == 0;
    if (igual) {
        liberar(nueva);
        return 1;
    }

    char *nombre_viejo = vieja->nombre;
    free(vieja->cuerpo);
    for (int i = 0; i < vieja->nparams; i++)
        free(vieja->params[i]);
    *vieja = *nueva;
    vieja->nombre = nombre_viejo;
    free(nueva);
    return 2;
}

int macro_borrar(const char *nombre) {
    for (Macro **p = &tabla; *p; p = &(*p)->sig) {
        if (strcmp((*p)->nombre, nombre) == 0) {
            Macro *m = *p;
            *p = m->sig;
            liberar(m);
            return 1;
        }
    }
    return 0;
}

void macro_liberar(void) {
    while (tabla) {
        Macro *m = tabla;
        tabla = m->sig;
        liberar(m);
    }
}
