"""
Pruebas del ISA de DUOS: una prueba funcional por instrucción y la coherencia
entre el enum Op, la tabla de despacho del emulador, la tabla ISA del
ensamblador y la tabla de docs/ISA_CPU.md.

Uso (desde src/lp02_duox):
    python3 pruebas/prueba_isa.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)

import config                                    # noqa: E402
from config import Global                        # noqa: E402
from ejecutar import correr, nueva_maquina       # noqa: E402
from ensamblador import ISA, ErrorEnsamblador, ensamblar_archivo   # noqa: E402
from emuladorDuos import EmuladorDUOS            # noqa: E402
from instrucciones import Op                     # noqa: E402

MASK64 = (1 << 64) - 1
DOC = os.path.join(os.path.dirname(os.path.dirname(RAIZ)), "docs", "ISA_CPU.md")
ALIAS = {"LDI": "LOAD_IMM"}

fallos = 0
cubiertas: set = set()


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    global fallos
    if not ok:
        fallos += 1
        print(f"  FALLO {nombre}" + (f": {detalle}" if detalle else ""))


def ensamblar(fuente: str):
    with tempfile.NamedTemporaryFile("w", suffix=".asm", delete=False) as f:
        f.write(fuente)
        ruta = f.name
    try:
        return ensamblar_archivo(ruta)
    finally:
        os.unlink(ruta)


def caso(mnem: str, fuente: str, preparar=None, max_pasos: int = 100000):
    """Ensambla y ejecuta `fuente` (que debe contener la instrucción `mnem`)."""
    alias = [k for k, v in ALIAS.items() if v == mnem]
    if not re.search(rf"\b({'|'.join([mnem] + alias)})\b", fuente):
        raise AssertionError(f"el caso de {mnem} no usa la instrucción")
    codigo, sim, ens = ensamblar(fuente)
    for el in ens.elementos:
        if el.tipo == "instr":
            cubiertas.add(ALIAS.get(el.mnem, el.mnem))
    emu = nueva_maquina(bytes(codigo))
    if preparar:
        preparar(emu)
    correr(emu, max_pasos=max_pasos)
    return emu, sim, codigo


# ------------------------------------------------------------- coherencia
def t_tablas() -> None:
    print("Tablas: enum Op, despacho, ensamblador y documentación")
    emu = EmuladorDUOS(dict(config.parametrosEmu))

    opcodes = [o.value for o in Op]
    check("opcodes únicos", len(set(opcodes)) == len(opcodes))
    check("despacho completo", set(emu._dispatch) == set(Op),
          f"faltan {sorted(o.name for o in set(Op) - set(emu._dispatch))}")
    for o in Op:
        check(f"{o.name} en el despacho", o in emu._dispatch)

    tamano = {None: 1, "imm": 9, "dir": 9, "addr": 9, "bloque": 17}
    for mnem, (opcode, tam, tipo) in ISA.items():
        nombre = ALIAS.get(mnem, mnem)
        check(f"{mnem} del ensamblador existe en Op", nombre in Op.__members__)
        if nombre in Op.__members__:
            check(f"{mnem} mismo opcode", opcode == Op[nombre].value,
                  f"ensamblador 0x{opcode:02X} emulador 0x{Op[nombre].value:02X}")
        check(f"{mnem} tamaño del formato", tam == tamano[tipo], f"{tam} != {tamano[tipo]}")
    check("alias LDI", ISA["LDI"][0] == ISA["LOAD_IMM"][0] == Op.LOAD_IMM)

    filas = {}
    for linea in open(DOC, encoding="utf-8"):
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) < 5:
            continue
        mnem, opcode = celdas[1].strip("`"), celdas[2].strip("`")
        if re.fullmatch(r"[A-Z_]+", mnem) and re.fullmatch(r"0x[0-9A-F]{2}", opcode):
            filas[mnem] = int(opcode, 16)
    check("la doc lista todas las instrucciones", set(filas) == set(Op.__members__),
          f"sobran {sorted(set(filas) - set(Op.__members__))}, "
          f"faltan {sorted(set(Op.__members__) - set(filas))}")
    for mnem, opcode in filas.items():
        check(f"{mnem} coincide con la doc", opcode == Op[mnem].value,
              f"doc 0x{opcode:02X} emulador 0x{Op[mnem].value:02X}")


# ------------------------------------------------------------- aritmética
def t_aritmetica() -> None:
    print("Aritmética y lógica")
    casos = [
        ("ADD", "PUSH 7\nPUSH 5\nADD\nHALT", 12),
        ("SUB", "PUSH 20\nPUSH 7\nSUB\nHALT", 13),
        ("MUL", "PUSH 6\nPUSH 7\nMUL\nHALT", 42),
        ("DIV", "PUSH 2\nPUSH 84\nDIV\nHALT", 42),
        ("MOD", "PUSH 5\nPUSH 17\nMOD\nHALT", 2),
        ("AND", "PUSH 0b1100\nPUSH 0b1010\nAND\nHALT", 0b1000),
        ("OR", "PUSH 0b1100\nPUSH 0b1010\nOR\nHALT", 0b1110),
        ("XOR", "PUSH 0b1100\nPUSH 0b1010\nXOR\nHALT", 0b0110),
        ("NOT", "PUSH 0\nNOT\nHALT", MASK64),
        ("SHL", "PUSH 3\nPUSH 4\nSHL\nHALT", 48),
        ("SHR", "PUSH 0xF0\nPUSH 4\nSHR\nHALT", 15),
    ]
    for mnem, fuente, esperado in casos:
        emu, _, _ = caso(mnem, fuente)
        check(mnem, emu.TOS == esperado, f"{emu.TOS} != {esperado}")

    emu, _, _ = caso("SUB", "PUSH 5\nPUSH 5\nSUB\nHALT")
    check("Z al restar iguales", emu.PSW["Z"] == 1)
    emu, _, _ = caso("SUB", "PUSH 7\nPUSH 9\nSUB\nHALT")
    check("N al restar negativo", emu.PSW["N"] == 1 and emu.TOS == -2)
    emu, _, _ = caso("SUB", "PUSH 1\nPUSH 2\nSUB\nHALT")
    check("C al pedir prestado", emu.PSW["C"] == 1)
    emu, _, _ = caso("ADD", f"PUSH {MASK64}\nPUSH 1\nADD\nHALT")
    check("C al desbordar sin signo", emu.PSW["C"] == 1)
    emu, _, _ = caso("XOR", "PUSH 1\nPUSH 1\nXOR\nHALT")
    check("Z en resultado cero", emu.PSW["Z"] == 1)

    emu, _, _ = caso("DIV", "PUSH 0\nPUSH 9\nDIV\nHALT")
    check("DIV por cero detiene", emu.halt and emu.TOS == 9)


# ------------------------------------------------------------ pila/memoria
def t_pila_memoria() -> None:
    print("Pila y memoria")
    emu, _, _ = caso("DUP", "PUSH 9\nDUP\nHALT")
    check("DUP", emu.TOS == 9 and emu.NOS == 9)
    emu, _, _ = caso("SWAP", "PUSH 1\nPUSH 2\nSWAP\nHALT")
    check("SWAP", emu.TOS == 1 and emu.NOS == 2)
    emu, _, _ = caso("POP", "PUSH 1\nPUSH 2\nPOP\nHALT")
    check("POP", emu.TOS == 1 and emu.NOS == 0)
    emu, _, _ = caso("LOAD_IMM", "LDI 1234\nHALT")
    check("LOAD_IMM", emu.TOS == 1234)
    emu, _, _ = caso("STORE", "PUSH 77\nSTORE v\nLOAD v\nHALT\n.VAR v")
    check("STORE/LOAD", emu.TOS == 77)

    fuente = "PUSH 55\nPUSH 8\nSTORE_OFF\nPUSH 8\nLOAD_OFF\nHALT"
    emu, _, _ = caso("STORE_OFF", fuente, preparar=lambda m: setattr(m, "BP", 0x3000))
    check("STORE_OFF/LOAD_OFF", emu.TOS == 55 and emu.leer_mem(0x3008) == 55)


# ----------------------------------------------------------------- saltos
def t_saltos() -> None:
    print("Control de flujo")
    emu, _, _ = caso("JMP", "PUSH 1\nJMP fin\nPUSH 999\nfin: PUSH 2\nHALT")
    check("JMP", emu.TOS == 2)

    base = "PUSH 5\nPUSH {b}\nSUB\nJZ {etiqueta}\nPUSH 0\nHALT\n{etiqueta}: PUSH 1\nHALT"
    emu, _, _ = caso("JZ", base.format(b=5, etiqueta="si"))
    check("JZ tomado", emu.TOS == 1)
    emu, _, _ = caso("JZ", base.format(b=6, etiqueta="si"))
    check("JZ no tomado", emu.TOS == 0)

    emu, _, _ = caso("JNZ", base.replace("JZ", "JNZ").format(b=6, etiqueta="si"))
    check("JNZ tomado", emu.TOS == 1)
    emu, _, _ = caso("JNZ", base.replace("JZ", "JNZ").format(b=5, etiqueta="si"))
    check("JNZ no tomado", emu.TOS == 0)

    mayor = "PUSH 5\nPUSH 3\nSUB\nJGT si\nPUSH 0\nHALT\nsi: PUSH 1\nHALT"
    emu, _, _ = caso("JGT", mayor)
    check("JGT tomado", emu.TOS == 1)
    emu, _, _ = caso("JGT", "PUSH 3\nPUSH 5\nSUB\nJGT si\nPUSH 0\nHALT\nsi: PUSH 1\nHALT")
    check("JGT no tomado", emu.TOS == 0)

    menor = "PUSH 3\nPUSH 5\nSUB\nJLT si\nPUSH 0\nHALT\nsi: PUSH 1\nHALT"
    emu, _, _ = caso("JLT", menor)
    check("JLT tomado con signo", emu.TOS == 1)
    emu, _, _ = caso("JLT", "PUSH 5\nPUSH 3\nSUB\nJLT si\nPUSH 0\nHALT\nsi: PUSH 1\nHALT")
    check("JLT no tomado", emu.TOS == 0)

    # CALL anidado: sub llama a sub2 y cada RET devuelve el control
    fuente = ("CALL sub\nPUSH 7\nHALT\n"
              "sub: CALL sub2\nPUSH 8\nRET\n"
              "sub2: PUSH 9\nRET\n")
    emu, _, _ = caso("CALL", fuente)
    check("CALL/RET anidado", emu.TOS == 7 and emu.SP == Global.STACK_TOP,
          f"TOS={emu.TOS} SP=0x{emu.SP:04X}")

    emu, _, _ = caso("NOP", "PUSH 5\nNOP\nHALT")
    check("NOP", emu.TOS == 5)


# ------------------------------------------------------------ concurrencia
def t_concurrencia() -> None:
    print("Concurrencia")
    emu, _, _ = caso("GET_CORE", "GET_CORE\nHALT")
    check("GET_CORE", emu.TOS == 0)
    emu, _, _ = caso("LOCK", "LOCK\nHALT")
    check("LOCK", emu.PSW["LOCK"] == 1 and emu.bus_bloqueado)
    emu, _, _ = caso("UNLOCK", "LOCK\nUNLOCK\nHALT")
    check("UNLOCK", emu.PSW["LOCK"] == 0 and not emu.bus_bloqueado)

    fuente = ("CORE_START n1\nPUSH 111\nSTORE v0\nHALT\n"
              "n1: PUSH 222\nSTORE v1\nGET_CORE\nSTORE c1\nHALT\n"
              ".VAR v0, v1, c1\n")
    emu, sim, _ = caso("CORE_START", fuente)
    check("CORE_START: núcleo 0", emu.leer_mem(sim["v0"]) == 111)
    check("CORE_START: núcleo 1", emu.leer_mem(sim["v1"]) == 222)
    check("CORE_START: CORE_ID del núcleo 1", emu.leer_mem(sim["c1"]) == 1)

    fuente = ("CORE_START n1\nCORE_YIELD\nPUSH 1\nHALT\n"
              "n1: PUSH 2\nHALT\n")
    emu, _, _ = caso("CORE_YIELD", fuente)
    check("CORE_YIELD", emu.TOS == 1, f"TOS={emu.TOS}")


# ---------------------------------------------------------------- E/S/red
def t_es_red() -> None:
    print("E/S y red")
    emu, _, _ = caso("OUT_PORT", "PUSH 42\nPUSH 7\nOUT_PORT\nPUSH 7\nIN_PORT\nHALT")
    check("OUT_PORT/IN_PORT", emu.TOS == 42)
    check("IN_PORT sin escribir", emu.puertos.get(7) == 42)

    emu, _, _ = caso("OUT", "PUSH 65\nOUT\nHALT")
    check("OUT", emu.salida == "A")

    fuente = ("PUSH datos\nPUSH 24\nNET_SEND\n"
              "PUSH dest0\nPUSH 24\nNET_RECV\nNET_STAT\nHALT\n"
              "datos: .WORD 1, 2, 3\n.VAR dest0, dest1, dest2\n")
    emu, sim, _ = caso("NET_SEND", fuente)
    esperado = b"".join(v.to_bytes(8, "big") for v in (1, 2, 3))
    check("NET_SEND", emu.nic_tx == [esperado], f"{emu.nic_tx}")
    check("NET_RECV", [emu.leer_mem(sim[f"dest{i}"]) for i in range(3)] == [1, 2, 3])
    check("NET_STAT", emu.TOS == 0, f"TOS={emu.TOS}")


# --------------------------------------------------------------- sistema
def t_sistema() -> None:
    print("Sistema")
    fuente = ("PUSH 3\nMEM_COPY datos, dest0\nHALT\n"
              "datos: .WORD 10, 20, 30\n.VAR dest0, dest1, dest2\n")
    emu, sim, _ = caso("MEM_COPY", fuente)
    check("MEM_COPY", [emu.leer_mem(sim[f"dest{i}"]) for i in range(3)] == [10, 20, 30])

    fuente = ("PUSH 4\nMEM_COPY datos, datos+8\nHALT\n"
              "datos: .WORD 1, 2, 3, 0\n")
    emu, sim, _ = caso("MEM_COPY", fuente)
    check("MEM_COPY con solapamiento",
          [emu.leer_mem(sim["datos"] + 8 * i) for i in range(4)] == [1, 1, 2, 3])

    emu, _, _ = caso("CACHE_FLUSH", "PUSH 5\nCACHE_FLUSH\nHALT")
    check("CACHE_FLUSH no altera el estado", emu.TOS == 5)

    emu, _, _ = caso("SET_FLAGS", "PUSH 23\nSET_FLAGS\nGET_FLAGS\nHALT")
    check("SET_FLAGS", emu.PSW["C"] == 1 and emu.PSW["Z"] == 1 and emu.PSW["N"] == 1
          and emu.PSW["V"] == 0 and emu.PSW["LOCK"] == 1)
    check("GET_FLAGS", emu.TOS == 23, f"TOS={emu.TOS}")

    fuente = ("EI\nPUSH isr\nSTORE 0x40\nPUSH 8\nINT\nPUSH 99\nHALT\n"
              "isr: LOAD cont\nPUSH 1\nADD\nSTORE cont\nIRET\n"
              ".VAR cont\n")
    emu, sim, _ = caso("INT", fuente)
    check("INT/IRET", emu.leer_mem(sim["cont"]) == 1 and emu.TOS == 99)
    check("IRET restaura I", emu.PSW["I"] == 1)

    emu, _, _ = caso("EI", "EI\nDI\nHALT")
    check("EI/DI", emu.PSW["I"] == 0)

    emu, _, _ = caso("EI", "EI\nPUSH 1\nHALT",
                     preparar=lambda m: setattr(m, "interrupt_pending", True))
    check("interrupción de teclado", emu.TOS == 1)


# ------------------------------------------------------------- ensamblador
def t_ensamblador() -> None:
    print("Errores del ensamblador")
    for fuente, motivo in [("FOO\nHALT\n", "instrucción desconocida"),
                           ("POP 5\nHALT\n", "no lleva operando"),
                           ("MEM_COPY 0x1000\nHALT\n", "dos direcciones"),
                           ("JMP\nHALT\n", "necesita un operando")]:
        try:
            ensamblar(fuente)
        except ErrorEnsamblador as e:
            check(motivo, True)
        else:
            check(motivo, False, "no se reportó el error")


def main() -> None:
    for prueba in (t_tablas, t_aritmetica, t_pila_memoria, t_saltos,
                   t_concurrencia, t_es_red, t_sistema, t_ensamblador):
        prueba()

    faltan = sorted(set(o.name for o in Op) - cubiertas)
    check("todas las instrucciones tienen prueba", not faltan, f"sin probar: {faltan}")
    print(f"\n{f'FALLOS: {fallos}' if fallos else 'OK: ISA completo y coherente'}"
          f"  ({len(cubiertas)}/{len(Op)} instrucciones probadas)")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
