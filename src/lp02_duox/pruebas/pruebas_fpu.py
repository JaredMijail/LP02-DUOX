"""
Pruebas diferenciales del FPU emulado contra la aritmética IEEE 754 de la CPU
real (los float de Python son binary64 con redondeo al par más cercano).

Para cada caso se escribe FA, FB y el número de servicio en la RAM de la
máquina DUOS, se ejecuta el programa driver.asm en el emulador ORIGINAL de la
Tarea 10 y se compara FR bit a bit con el resultado esperado. En cada ciclo se
verifica además que TOS y NOS caben en 64 bits.

Uso:  python3 pruebas/pruebas_fpu.py [casos_aleatorios_por_operacion]
"""
import math
import os
import random
import struct
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

from ejecutar import nueva_maquina, correr          # noqa: E402
from ensamblador import ensamblar_archivo           # noqa: E402

M64 = (1 << 64) - 1


def b2f(b):
    return struct.unpack(">d", struct.pack(">Q", b))[0]


def f2b(f):
    return struct.unpack(">Q", struct.pack(">d", f))[0]


def es_nan(b):
    return (b >> 52) & 0x7FF == 0x7FF and b & ((1 << 52) - 1) != 0


# ------------------------------------------------------------- referencia
def ref_binaria(op):
    def f(a, b):
        x, y = b2f(a), b2f(b)
        try:
            if op == "add":
                r = x + y
            elif op == "sub":
                r = x - y
            elif op == "mul":
                r = x * y
            elif op == "div":
                if y == 0.0:
                    if math.isnan(x) or x == 0.0:
                        return f2b(math.nan)
                    signo = (math.copysign(1, x) * math.copysign(1, y)) < 0
                    return f2b(-math.inf if signo else math.inf)
                r = x / y
        except OverflowError:
            raise
        return f2b(r)
    return f


def ref_cmp(a, b):
    x, y = b2f(a), b2f(b)
    if math.isnan(x) or math.isnan(y):
        return 3
    return 0 if x == y else (1 if x < y else 2)


def ref_i2f(a, _):
    v = a - (1 << 64) if a >> 63 else a
    return f2b(float(v))


def ref_f2i(a, _):
    x = b2f(a)
    if math.isnan(x) or math.isinf(x) or abs(x) >= 2.0 ** 63:
        return 1 << 63
    return int(x) & M64


# ------------------------------------------------------------- generadores
ESPECIALES = [0, 1 << 63, 0x7FF0000000000000, 0xFFF0000000000000,
              0x7FF8000000000000, 0x7FF0000000000001, 0xFFF8000000000123,
              1, 0x000FFFFFFFFFFFFF, 0x0010000000000000, 0x7FEFFFFFFFFFFFFF,
              f2b(1.0), f2b(-1.0), f2b(0.1), f2b(0.2), f2b(0.3), f2b(2.0), f2b(0.5),
              f2b(3.0), f2b(1 / 3), f2b(1e308), f2b(1e-308), f2b(5e-324),
              f2b(2.0 ** 52), f2b(2.0 ** 53), f2b(2.0 ** 63), f2b(-2.0 ** 63),
              f2b(1 + 2 ** -52), f2b(2 ** -53), f2b(125.0), f2b(10.0)]


def aleatorio(rnd):
    t = rnd.random()
    if t < 0.15:
        return rnd.choice(ESPECIALES) ^ (rnd.getrandbits(1) << 63)
    if t < 0.30:   # subnormales y cerca del límite
        return (rnd.getrandbits(1) << 63) | rnd.getrandbits(rnd.randint(1, 54)) & ((1 << 54) - 1)
    if t < 0.45:   # exponentes extremos
        e = rnd.choice([rnd.randint(1, 60), rnd.randint(1980, 2046)])
        return (rnd.getrandbits(1) << 63) | (e << 52) | rnd.getrandbits(52)
    if t < 0.75:   # rango "normal" moderado
        e = rnd.randint(1023 - 40, 1023 + 40)
        return (rnd.getrandbits(1) << 63) | (e << 52) | rnd.getrandbits(52)
    return rnd.getrandbits(64)


def par_cercano(rnd):
    """Pares con exponentes parecidos (cancelación) o empates de redondeo."""
    a = aleatorio(rnd)
    t = rnd.random()
    if t < 0.4:
        return a, a ^ (1 << 63) ^ rnd.getrandbits(rnd.randint(0, 6))
    if t < 0.7:
        e = (a >> 52) & 0x7FF
        d = rnd.randint(0, 60)
        e2 = max(0, min(2046, e - d))
        return a, (rnd.getrandbits(1) << 63) | (e2 << 52) | rnd.getrandbits(52)
    # empates exactos: 1 + 2^-53, (1 + 2^-52) + 2^-53, etc.
    base = rnd.randint(1, 2045)
    m = rnd.getrandbits(52)
    a = (base << 52) | m
    b = ((base - 53) << 52) if base > 53 else 1
    return a, b | (rnd.getrandbits(1) << 63) if rnd.random() < 0.3 else b


def enteros(rnd):
    t = rnd.random()
    if t < 0.3:
        return rnd.choice([0, 1, M64, 1 << 63, (1 << 63) - 1, (1 << 53) + 1,
                           (1 << 53) - 1, (1 << 54) + 2, 125, 10])
    return rnd.getrandbits(rnd.randint(1, 64))


# ------------------------------------------------------------- ejecución
class Banco:
    def __init__(self):
        ruta = os.path.join(AQUI, "driver.asm")
        codigo, self.sim, _ = ensamblar_archivo(ruta)
        self.codigo = bytes(codigo)
        self.emu = nueva_maquina(self.codigo)
        self.ram0 = bytearray(self.emu.ram)
        self.instr = 0

    def ejecutar(self, vec, a, b):
        emu = self.emu
        emu.ram[:] = self.ram0
        emu.PC, emu.SP, emu.halt, emu.TOS, emu.NOS = 0x1000, 0xFFFF, False, 0, 0
        emu.escribir_mem(self.sim["FA"], a)
        emu.escribir_mem(self.sim["FB"], b)
        emu.escribir_mem(self.sim["OPV"], vec)
        self.instr += correr(emu, max_pasos=200000, verificar64=True)
        return emu.leer_mem(self.sim["FR"])


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    rnd = random.Random(754)
    banco = Banco()
    ops = [("FADD", 16, ref_binaria("add"), "f"), ("FSUB", 17, ref_binaria("sub"), "f"),
           ("FMUL", 18, ref_binaria("mul"), "f"), ("FDIV", 19, ref_binaria("div"), "f"),
           ("FCMP", 20, ref_cmp, "c"), ("FI2F", 21, ref_i2f, "i"), ("FF2I", 22, ref_f2i, "c")]
    fallos_totales = 0
    t0 = time.time()
    for nombre, vec, ref, tipo in ops:
        casos = []
        if nombre in ("FI2F",):
            casos = [(enteros(rnd), 0) for _ in range(n)]
        elif nombre == "FF2I":
            casos = [(aleatorio(rnd), 0) for _ in range(n)]
        else:
            casos = [(x, y) for x in ESPECIALES[:12] for y in ESPECIALES[:12]]
            casos += [(aleatorio(rnd), aleatorio(rnd)) for _ in range(n)]
            casos += [par_cercano(rnd) for _ in range(n // 2)]
        fallos = 0
        i0 = banco.instr
        for a, b in casos:
            esperado = ref(a, b)
            obtenido = banco.ejecutar(vec, a, b)
            ok = (es_nan(esperado) and es_nan(obtenido)) if tipo == "f" and es_nan(esperado) \
                else obtenido == esperado
            if not ok:
                fallos += 1
                if fallos <= 5:
                    print(f"  FALLO {nombre} a={a:016X} b={b:016X} "
                          f"esperado={esperado:016X} obtenido={obtenido:016X}")
        prom = (banco.instr - i0) / len(casos)
        print(f"{nombre}: {len(casos) - fallos}/{len(casos)} correctos "
              f"(promedio {prom:.0f} instrucciones DUOS por operación)")
        fallos_totales += fallos
    # FPRINT: conversión a decimal (notación fija) frente al formateo de Python
    fallos = 0
    m = max(200, n // 4)
    for _ in range(m):
        x = rnd.choice([rnd.uniform(-1e6, 1e6), rnd.uniform(0, 10),
                        rnd.uniform(2 ** -7, 1) * rnd.choice([1, -1]),
                        rnd.choice([0.5, 2.5, 0.125, 125.0, 0.1, 1 / 3, 0.0])])
        if x != 0.0 and not (2 ** -7 <= abs(x) < 2 ** 50):
            x = 0.5 + abs(x)          # fuera del rango de notación fija
        banco.emu.salida = ""
        banco.ejecutar(23, f2b(x), 0)
        if banco.emu.salida != f"{x:.15f}":
            fallos += 1
            if fallos <= 5:
                print(f"  FALLO FPRINT {x!r}: {banco.emu.salida} vs {x:.15f}")
    print(f"FPRINT: {m - fallos}/{m} correctos (comparado con el formato '%.15f' de Python)")
    fallos_totales += fallos

    print(f"\nTotal de fallos: {fallos_totales}   ({time.time() - t0:.0f} s, "
          f"{banco.instr:,} instrucciones, ningún registro excedió 64 bits)")
    sys.exit(1 if fallos_totales else 0)


if __name__ == "__main__":
    main()
