"""
Referencia en Python (float = IEEE 754 binary64 del hardware real) de los
programas heron.asm y brun.asm. Hace exactamente las mismas operaciones en el
mismo orden, de modo que los resultados deben coincidir BIT A BIT con los que
calcula el FPU emulado en la máquina DUOS.

Uso:  python3 pruebas/referencia.py            (compara con la salida de DUOS)
"""
import math
import os
import re
import struct
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)


def hexf(x):
    return "0x%016X" % struct.unpack(">Q", struct.pack(">d", x))[0]


def heron(x, y):
    filas = []
    i = 0
    while True:
        i += 1
        n = ((x / y) + y) * 0.5
        filas.append(hexf(n))
        if i >= 2 and not (n < y):
            break
        y = n
        if i >= 60:
            break
    return filas, y


def ln(x):
    m, k = math.frexp(x)          # x = m * 2^k, m en [0.5, 1)
    m, k = m * 2, k - 1           # m en [1, 2)
    kf = float(k + 1023) - 1023.0
    t = (m - 1.0) / (m + 1.0)
    t2 = t * t
    pot, s, den = t, 0.0, 1.0
    for _ in range(24):
        s = s + pot / den
        pot = pot * t2
        den = den + 2.0
    s = s + s
    return kf * 0.6931471805599453 + s


def es_primo(n):
    d = 5
    while d * d <= n:
        if n % d == 0 or n % (d + 2) == 0:
            return False
        d += 6
    return True


def brun(nmax):
    s = 1.0 / 3.0
    s = s + 1.0 / 5.0
    pares, k, cp = 1, 1, 100
    c4 = 4.0 * 0.6601618158468696
    filas = []
    while True:
        p, q = 6 * k - 1, 6 * k + 1
        terminar = False
        while q > cp:
            filas.append((cp, pares, s, s + c4 / ln(float(cp))))
            if cp >= nmax:
                terminar = True
                break
            cp *= 10
        if terminar:
            break
        if es_primo(p) and es_primo(q):
            t = 1.0 / float(p)
            u = 1.0 / float(q)
            s = s + (t + u)
            pares += 1
        k += 1
    return filas


def main():
    print("== Herón: referencia en Python vs. salida de la máquina DUOS ==")
    salida = subprocess.run([sys.executable, os.path.join(RAIZ, "ejecutar.py"),
                             os.path.join(RAIZ, "asm", "heron.asm")],
                            capture_output=True, text=True).stdout
    hex_duos = re.findall(r"0x[0-9A-F]{16}", salida)
    hex_ref = []
    for x, y in [(125.0, 10.0), (2.0, 1.0), (3.0, 1.0), (0.5, 0.5), (12345.678, 100.0)]:
        filas, r = heron(x, y)
        hex_ref += filas
        ulp = (struct.unpack(">q", struct.pack(">d", r))[0]
               - struct.unpack(">q", struct.pack(">d", math.sqrt(x)))[0])
        print(f"  x={x:<10} sqrt Herón={r!r:<22} math.sqrt={math.sqrt(x)!r:<22} "
              f"{'idéntico' if ulp == 0 else f'difiere en {ulp:+d} ulp'}")
    ok_h = hex_duos == hex_ref
    print(f"  {len(hex_ref)} iteraciones comparadas bit a bit: {'OK' if ok_h else 'DIFERENCIAS'}")

    print("\n== Brun: referencia en Python vs. salida de la máquina DUOS ==")
    nmax = int(re.search(r"\.EQU NMAX,\s*(\d+)",
                         open(os.path.join(RAIZ, "asm", "brun.asm")).read()).group(1))
    salida = subprocess.run([sys.executable, os.path.join(RAIZ, "ejecutar.py"),
                             os.path.join(RAIZ, "asm", "brun.asm")],
                            capture_output=True, text=True).stdout
    duos = re.findall(r"10\^(\d+)\t(\d+)\t([\d.]+)\t([\d.]+)", salida)
    ok_b = len(duos) == len(brun(nmax))
    for (cp, pares, s, e), d in zip(brun(nmax), duos):
        fila = (str(len(str(cp)) - 1), str(pares), f"{s:.15f}", f"{e:.15f}")
        igual = fila == d
        ok_b &= igual
        print(f"  N=10^{fila[0]} pares={pares:<5} B2(N)={s:.15f} est={e:.15f} "
              f"{'= DUOS' if igual else '!= DUOS ' + str(d)}")
    print(f"\nResultado: Herón {'OK' if ok_h else 'FALLA'}, Brun {'OK' if ok_b else 'FALLA'}")
    sys.exit(0 if ok_h and ok_b else 1)


if __name__ == "__main__":
    main()
