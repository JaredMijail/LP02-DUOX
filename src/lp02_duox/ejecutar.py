"""
Ensambla y ejecuta un programa .asm en la máquina DUOS de la Tarea 10.

Usa el emulador ORIGINAL (emuladorDuos.py / instrucciones.py) sin modificarlo.
Lo único que hace este script es silenciar la traza que el emulador imprime en
cada ciclo (para que programas de millones de instrucciones terminen en un
tiempo razonable) y mostrar al final la salida de consola de la máquina.

Uso:
    python3 ejecutar.py asm/heron.asm            # ensambla, ejecuta y muestra la salida
    python3 ejecutar.py asm/heron.asm --traza    # con la traza original del emulador
    python3 ejecutar.py asm/heron.asm --verificar64
        # además comprueba en cada ciclo que TOS y NOS caben en 64 bits

El .hex generado en bin/ también se puede correr con el programa original:
    python3 main.py bin/heron.hex                (opción 2 y luego opción 4)
"""
from __future__ import annotations

import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import config                         # noqa: E402
import emuladorDuos                   # noqa: E402
import instrucciones                  # noqa: E402
from config import Global             # noqa: E402
from emuladorDuos import EmuladorDUOS  # noqa: E402
from ensamblador import ensamblar_archivo, a_hex, ErrorEnsamblador  # noqa: E402

MIN64, MAX64 = -(1 << 63), (1 << 64) - 1


def _silenciar(silencio: bool):
    nulo = (lambda *a, **k: None) if silencio else print
    emuladorDuos.print = nulo
    instrucciones.print = nulo


def nueva_maquina(codigo: bytes, silencio: bool = True) -> EmuladorDUOS:
    """Crea una máquina limpia, monta el mini-SO y carga el programa en 0x1000."""
    _silenciar(silencio)
    p_emu = dict(config.parametrosEmu)
    p_emu["ram"] = bytearray(Global.RAM_SIZE)
    p_emu["PSW"] = {"Z": 0, "N": 0, "I": 0}
    p_so = dict(config.parametrosSo)
    p_so["ram"] = bytearray(Global.RAM_SIZE)
    emu = EmuladorDUOS(p_emu)
    emu.cargar_SO(p_so)
    emu.cargar_programa(codigo.hex(), Global.PROGRAMA_BASE)
    return emu


def correr(emu: EmuladorDUOS, max_pasos: int = 10**9, verificar64: bool = False) -> int:
    """Ejecuta hasta HALT. Devuelve el número de instrucciones ejecutadas."""
    pasos = 0
    paso = emu.paso
    if verificar64:
        while pasos < max_pasos:
            if not paso():
                break
            pasos += 1
            if not (MIN64 <= emu.TOS <= MAX64 and MIN64 <= emu.NOS <= MAX64):
                raise OverflowError(
                    f"registro fuera de 64 bits en PC=0x{emu.PC:04X}: TOS={emu.TOS} NOS={emu.NOS}")
    else:
        while pasos < max_pasos and paso():
            pasos += 1
    if pasos >= max_pasos:
        raise RuntimeError("se alcanzó el máximo de pasos sin HALT")
    return pasos + 1  # cuenta el HALT


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    ruta = args[0]
    traza = "--traza" in sys.argv
    verif = "--verificar64" in sys.argv
    try:
        codigo, simbolos, ens = ensamblar_archivo(ruta)
    except ErrorEnsamblador as e:
        print(f"Error de ensamblado: {e}")
        sys.exit(2)
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    os.makedirs(os.path.join(AQUI, "bin"), exist_ok=True)
    raiz = os.path.join(AQUI, "bin", nombre)
    with open(raiz + ".hex", "w") as f:
        f.write(a_hex(codigo))
    with open(raiz + ".lst", "w", encoding="utf-8") as f:
        f.write(ens.listado(codigo) + "\n")
    print(f"[Ensamblador] {ruta}: {len(codigo)} bytes en 0x{Global.PROGRAMA_BASE:04X}-"
          f"0x{Global.PROGRAMA_BASE + len(codigo) - 1:04X} -> bin/{nombre}.hex")

    emu = nueva_maquina(bytes(codigo), silencio=not traza)
    t0 = time.time()
    pasos = correr(emu, verificar64=verif)
    dt = time.time() - t0
    print("=" * 72)
    print(emu.salida, end="" if emu.salida.endswith("\n") else "\n")
    print("=" * 72)
    print(f"[DUOS] HALT tras {pasos:,} instrucciones en {dt:.1f} s"
          + ("  (registros verificados en 64 bits)" if verif else ""))


if __name__ == "__main__":
    main()
