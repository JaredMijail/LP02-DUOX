"""
Mapeo de las 40 instrucciones de asm/mate.inc a instrucciones nativas DUOS.

Expande cada macro por separado con el mismo expansor de ensamblador.py (sin
modificarlo) y cuenta las instrucciones nativas que genera: mnemónico, opcode,
bytes, y cuántas son llamadas a subrutinas (PUSH n ; INT). También mide las
subrutinas y los datos que emite MATE_RUTINAS (se pagan una sola vez por
programa) y la macro de instalación MATE_INSTALL. Los resultados alimentan las
tablas de docs/mapeo_ensamblador.md.

Uso (desde src/lp02_duox):
    py pruebas/mapeo_mate.py              # tablas resumen
    py pruebas/mapeo_mate.py FABSV IPARV  # listado nativo completo de esas macros
"""
from __future__ import annotations

import os
import sys
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

from ensamblador import Ensamblador, Linea, ISA, _dividir_args  # noqa: E402

MATE = os.path.join(RAIZ, "asm", "mate.inc")

# número, macro y una llamada de ejemplo (los operandos son nombres de variables)
LLAMADAS = [
    (1, "IABSV", "d, a"), (2, "INEGV", "d, a"), (3, "ISGNV", "d, a"),
    (4, "IMINV", "d, a, b"), (5, "IMAXV", "d, a, b"), (6, "ICLAMPV", "d, a, lo, hi"),
    (7, "IPOTV", "d, b, e"), (8, "IFACTV", "d, n"), (9, "IMCDV", "d, a, b"),
    (10, "IMCMV", "d, a, b"), (11, "IRAIZV", "d, a"), (12, "IPARV", "d, a"),
    (13, "IPROMV", "d, a, b"), (14, "IDIVSV", "d, a, b"), (15, "IMODSV", "d, a, b"),
    (16, "IDISTV", "d, a, b"), (17, "IPRIMOV", "d, n"), (18, "ICOMBV", "d, n, k"),
    (19, "ILOG2V", "d, a"), (20, "IFIBV", "d, n"),
    (21, "FABSV", "d, x"), (22, "FNEGV", "d, x"), (23, "FSQRV", "d, x"),
    (24, "FSQRTV", "d, x"), (25, "FPOTIV", "d, x, n"), (26, "FMINV", "d, x, y"),
    (27, "FMAXV", "d, x, y"), (28, "FRECV", "d, x"), (29, "FEXPV", "d, x"),
    (30, "FLNV", "d, x"), (31, "FPOTV", "d, x, y"), (32, "FSINV", "d, x"),
    (33, "FCOSV", "d, x"), (34, "FTANV", "d, x"), (35, "FPROMV", "d, x, y"),
    (36, "FHIPOTV", "d, x, y"), (37, "FCLAMPV", "d, x, lo, hi"), (38, "FSGNV", "d, x"),
    (39, "FTRUNCV", "d, x"), (40, "FFLOORV", "d, x"),
]

# primera etiqueta de cada bloque de MATE_RUTINAS -> (vector(es), descripción)
BLOQUES = {
    "mt_rut_sqrt": ("2 V_MSQRT", "raiz cuadrada (Heron)"),
    "mt_rut_exp": ("3 V_MEXP", "e^x (Taylor + reduccion)"),
    "mt_rut_ln": ("4 V_MLN", "ln x (serie de atanh)"),
    "mt_rut_sin": ("5 V_MSIN, 6 V_MCOS", "sen / cos (codigo compartido)"),
    "mt_rut_mcm": ("7 V_MMCM", "MCM"),
    "MT_CERO": ("-", "constantes y temporales (.DOUBLE/.WORD/.VAR)"),
}


def _lineas(llamada: str) -> list:
    """Textos ya expandidos de una llamada (instrucciones, etiquetas y directivas)."""
    ens = Ensamblador()
    ens.incluidos.add(os.path.abspath(MATE))
    ens._expandir(ens._leer(MATE))                 # solo para definir las macros
    return [ln.texto.strip() for ln in ens._expandir([Linea(llamada, MATE, 0)])]


def _es_etiqueta(txt: str) -> bool:
    return txt.endswith(":") and " " not in txt


def expandir(llamada: str) -> list:
    """Devuelve las instrucciones nativas (mnemónico, texto) de una llamada."""
    return [(t.split(None, 1)[0].upper(), t) for t in _lineas(llamada) if not _es_etiqueta(t)]


def resumen(nativas: list) -> tuple:
    cuenta = Counter(m for m, _ in nativas)
    total = sum(ISA[m][1] * n for m, n in cuenta.items())
    detalle = ", ".join(f"{m} {ISA[m][0]:02X}/{ISA[m][1]} x{n}"
                        for m, n in sorted(cuenta.items(), key=lambda x: -x[1]))
    return len(nativas), total, cuenta["INT"], detalle


def bloques_rutinas() -> list:
    """Mide cada bloque de MATE_RUTINAS: [(etiqueta, instrucciones, bytes)]."""
    filas, actual = [], None
    for txt in _lineas("MATE_RUTINAS"):
        if _es_etiqueta(txt):
            if txt[:-1] in BLOQUES:
                actual = [txt[:-1], 0, 0]
                filas.append(actual)
            continue
        op, _, resto = txt.partition(" ")
        op = op.upper()
        if op in (".WORD", ".DOUBLE", ".VAR"):
            actual[2] += 8 * len(_dividir_args(resto))
        elif op != ".EQU":
            actual[1] += 1
            actual[2] += ISA[op][1]
    return filas


def main():
    pedidas = [a.upper() for a in sys.argv[1:]]
    if pedidas:
        for num, nombre, ops in LLAMADAS:
            if nombre not in pedidas:
                continue
            nativas = expandir(f"{nombre} {ops}")
            print(f"; {num}. {nombre} {ops}")
            for m, txt in nativas:
                op, tam, _ = ISA[m]
                print(f"    {txt:<36} ; {op:02X}  {tam:>2} B")
            n, total, _, _ = resumen(nativas)
            print(f"; {n} instrucciones, {total} bytes\n")
        return

    print("| # | Macro | Instr. | Bytes | Llamadas INT | Detalle (mnemonico opcode/bytes xveces) |")
    print("|---|---|---|---|---|---|")
    suma = 0
    for num, nombre, ops in LLAMADAS:
        n, total, ints, detalle = resumen(expandir(f"{nombre} {ops}"))
        suma += total
        print(f"| {num} | {nombre} | {n} | {total} | {ints} | {detalle} |")
    print(f"\nUna expansion de cada una de las 40: {suma} bytes\n")

    print("| Bloque de MATE_RUTINAS | Vector(es) | Contenido | Instr. | Bytes |")
    print("|---|---|---|---|---|")
    fijo = 0
    for etiqueta, n, total in bloques_rutinas():
        vec, desc = BLOQUES[etiqueta]
        fijo += total
        print(f"| {etiqueta} | {vec} | {desc} | {n} | {total} |")
    n, total, _, _ = resumen(expandir("MATE_INSTALL"))
    print(f"| MATE_INSTALL | - | instala vectores 2-7 y 16-29 (incluye FPU_INSTALL) | {n} | {total} |")
    print(f"\nCosto fijo de la libreria por programa (MATE_RUTINAS + MATE_INSTALL): "
          f"{fijo + total} bytes (sin contar fpu.asm)")


if __name__ == "__main__":
    main()
