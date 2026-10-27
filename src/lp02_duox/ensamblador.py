"""
Ensamblador para la máquina DUOS.

Traduce un programa escrito con mnemónicos a la cadena hexadecimal de código
de máquina que entiende el cargador. NO amplía el repertorio de instrucciones:
cada macro se expande únicamente a instrucciones nativas.

Repertorio nativo (opcodes y formatos de docs/ISA_CPU.md):

    Tipo 0 (1 byte): operan sobre TOS/NOS
        NOP 00  ADD 01  SUB 02  MUL 03  DIV 04  MOD 05  AND 06  OR 07
        XOR 08  NOT 09  SHL 0A  SHR 0B  POP 11  DUP 12  SWAP 13
        LOAD_OFF 16  STORE_OFF 17  RET 26  HALT 27  GET_CORE 30  LOCK 31
        UNLOCK 32  CORE_YIELD 34  IN_PORT 40  OUT_PORT 41  NET_SEND 42
        NET_RECV 43  NET_STAT 44  OUT 45  CACHE_FLUSH 50  SET_FLAGS 52
        GET_FLAGS 53  INT 54  IRET 55  EI 56  DI 57
    Tipo 1 (9 bytes): opcode + operando de 64 bits
        PUSH 10 imm  LOAD 14 dir  STORE 15 dir  LOAD_IMM 18 imm (LDI)
        JMP 20 addr  JZ 21 addr  JNZ 22 addr  JGT 23 addr  JLT 24 addr
        CALL 25 addr  CORE_START 33 addr
    Tipo 2 (17 bytes): opcode + dos direcciones de 64 bits
        MEM_COPY 51 src, dst

Las de tipo 0 dejan el resultado en TOS; los saltos usan la dirección absoluta.

Directivas:
    etiqueta:                 define una etiqueta (dirección absoluta)
    .EQU nombre, expr         constante simbólica
    .WORD expr[, expr...]     palabras de 64 bits (big-endian)
    .DOUBLE real[, real...]   palabras con el patrón IEEE 754 binary64 del real
                              (conversión hecha por el ensamblador, igual que
                              la directiva .double de cualquier ensamblador)
    .VAR a, b, ...            reserva una palabra en cero para cada nombre
    .INCLUDE "archivo"        incluye otro archivo fuente
    .MACRO nombre p1, p2 ...  define una macro; en el cuerpo se usa \\p1 ...
    .ENDM                     fin de la macro. %%x crea etiquetas locales.
    PRINTS "texto"            pseudo-instrucción: PUSH c ; OUT por carácter
    PUTC expr                 pseudo-instrucción: PUSH expr ; OUT

Expresiones: enteros (decimal, 0x.., 0b..), 'c', nombres, + - * // % << >> 
& | ^ ** y paréntesis.

Uso:
    python3 ensamblador.py programa.asm [-o salida.hex]
Genera salida.hex (para main.py), salida.lst (listado) y salida.sym (símbolos).
"""
from __future__ import annotations

import ast
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, field

BASE = 0x1000          # Global.PROGRAMA_BASE de la Tarea 10
MASK64 = (1 << 64) - 1
LIMITE_SEGURO = 0xF000  # por encima está la pila del sistema (SP = 0xFFFF)

# mnemónico -> (opcode, bytes totales, tipo de operando)
#   None: sin operando ; "imm": inmediato de 8 bytes ; "dir": dirección de 8
#   bytes ; "addr": destino absoluto de 8 bytes ; "bloque": dos direcciones.
ISA = {
    "NOP": (0x00, 1, None),
    "ADD": (0x01, 1, None),
    "SUB": (0x02, 1, None),
    "MUL": (0x03, 1, None),
    "DIV": (0x04, 1, None),
    "MOD": (0x05, 1, None),
    "AND": (0x06, 1, None),
    "OR": (0x07, 1, None),
    "XOR": (0x08, 1, None),
    "NOT": (0x09, 1, None),
    "SHL": (0x0A, 1, None),
    "SHR": (0x0B, 1, None),
    "PUSH": (0x10, 9, "imm"),
    "POP": (0x11, 1, None),
    "DUP": (0x12, 1, None),
    "SWAP": (0x13, 1, None),
    "LOAD": (0x14, 9, "dir"),
    "STORE": (0x15, 9, "dir"),
    "LOAD_OFF": (0x16, 1, None),
    "STORE_OFF": (0x17, 1, None),
    "LOAD_IMM": (0x18, 9, "imm"),
    "LDI": (0x18, 9, "imm"),
    "JMP": (0x20, 9, "addr"),
    "JZ": (0x21, 9, "addr"),
    "JNZ": (0x22, 9, "addr"),
    "JGT": (0x23, 9, "addr"),
    "JLT": (0x24, 9, "addr"),
    "CALL": (0x25, 9, "addr"),
    "RET": (0x26, 1, None),
    "HALT": (0x27, 1, None),
    "GET_CORE": (0x30, 1, None),
    "LOCK": (0x31, 1, None),
    "UNLOCK": (0x32, 1, None),
    "CORE_START": (0x33, 9, "addr"),
    "CORE_YIELD": (0x34, 1, None),
    "IN_PORT": (0x40, 1, None),
    "OUT_PORT": (0x41, 1, None),
    "NET_SEND": (0x42, 1, None),
    "NET_RECV": (0x43, 1, None),
    "NET_STAT": (0x44, 1, None),
    "OUT": (0x45, 1, None),
    "CACHE_FLUSH": (0x50, 1, None),
    "MEM_COPY": (0x51, 17, "bloque"),
    "SET_FLAGS": (0x52, 1, None),
    "GET_FLAGS": (0x53, 1, None),
    "INT": (0x54, 1, None),
    "IRET": (0x55, 1, None),
    "EI": (0x56, 1, None),
    "DI": (0x57, 1, None),
}


class ErrorEnsamblador(Exception):
    pass


@dataclass
class Linea:
    texto: str
    archivo: str
    num: int
    nivel: int = 0          # profundidad de expansión de macro (para el listado)


@dataclass
class Elemento:
    tipo: str               # "instr" | "word"
    mnem: str = ""
    expr: str | None = None
    palabras: list = field(default_factory=list)   # para .WORD/.DOUBLE/.VAR
    dir: int = 0
    tam: int = 0
    origen: Linea | None = None


@dataclass
class Macro:
    nombre: str
    params: list
    cuerpo: list


def _quitar_comentario(s: str) -> str:
    fuera = []
    en_cad = None
    for c in s:
        if en_cad:
            fuera.append(c)
            if c == en_cad:
                en_cad = None
            continue
        if c in "\"'":
            en_cad = c
        elif c == ";":
            break
        fuera.append(c)
    return "".join(fuera).rstrip()


def _dividir_args(s: str) -> list:
    args, prof, act, en_cad = [], 0, [], None
    for c in s:
        if en_cad:
            act.append(c)
            if c == en_cad:
                en_cad = None
            continue
        if c in "\"'":
            en_cad = c
        elif c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
        elif c == "," and prof == 0:
            args.append("".join(act).strip())
            act = []
            continue
        act.append(c)
    if "".join(act).strip():
        args.append("".join(act).strip())
    return args


def _cadena(s: str) -> str:
    s = s.strip()
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        raise ErrorEnsamblador(f"se esperaba una cadena entre comillas: {s}")
    return bytes(s[1:-1], "utf-8").decode("unicode_escape")


class Ensamblador:
    def __init__(self):
        self.macros: dict[str, Macro] = {}
        self.simbolos: dict[str, int] = {}
        self.equs: dict[str, str] = {}
        self.elementos: list[Elemento] = []
        self.contador_macro = 0
        self.incluidos: set = set()

    # ------------------------------------------------------------ lectura
    def _leer(self, ruta: str) -> list:
        ruta = os.path.abspath(ruta)
        with open(ruta, encoding="utf-8") as f:
            return [Linea(t.rstrip("\n"), ruta, i + 1) for i, t in enumerate(f)]

    # --------------------------------------------- expansión (paso 0)
    def _expandir(self, lineas: list, nivel: int = 0) -> list:
        salida = []
        i = 0
        while i < len(lineas):
            ln = lineas[i]
            txt = _quitar_comentario(ln.texto).strip()
            i += 1
            if not txt:
                continue
            # etiquetas al inicio de la línea
            while True:
                m = re.match(r"^([A-Za-z_.%][\w.%]*)\s*:(.*)$", txt)
                if not m:
                    break
                salida.append(Linea(m.group(1) + ":", ln.archivo, ln.num, nivel))
                txt = m.group(2).strip()
            if not txt:
                continue
            partes = txt.split(None, 1)
            op = partes[0].upper()
            resto = partes[1] if len(partes) > 1 else ""

            if op == ".MACRO":
                cab = resto.split(None, 1)
                nombre = cab[0].upper()
                params = _dividir_args(cab[1]) if len(cab) > 1 else []
                cuerpo = []
                while True:
                    if i >= len(lineas):
                        raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: .MACRO {nombre} sin .ENDM")
                    l2 = lineas[i]
                    i += 1
                    if _quitar_comentario(l2.texto).strip().upper() == ".ENDM":
                        break
                    cuerpo.append(l2)
                self.macros[nombre] = Macro(nombre, [p.strip() for p in params], cuerpo)
                continue

            if op == ".INCLUDE":
                nombre = _cadena(resto)
                ruta = os.path.join(os.path.dirname(ln.archivo), nombre)
                clave = os.path.abspath(ruta)
                if clave in self.incluidos:
                    continue
                self.incluidos.add(clave)
                salida.extend(self._expandir(self._leer(ruta), nivel))
                continue

            if op in self.macros:
                mac = self.macros[op]
                args = _dividir_args(resto)
                if len(args) != len(mac.params):
                    raise ErrorEnsamblador(
                        f"{ln.archivo}:{ln.num}: la macro {op} espera {len(mac.params)} "
                        f"argumentos y recibió {len(args)}")
                self.contador_macro += 1
                uid = self.contador_macro
                valores = dict(zip(mac.params, args))
                nuevas = []
                for cl in mac.cuerpo:
                    t = re.sub(r"\\(\w+)",
                               lambda mm: valores.get(mm.group(1), mm.group(0)), cl.texto)
                    t = re.sub(r"%%(\w+)", lambda mm: f"__m{uid}_{mm.group(1)}", t)
                    nuevas.append(Linea(t, ln.archivo, ln.num, nivel + 1))
                salida.extend(self._expandir(nuevas, nivel + 1))
                continue

            if op == "PRINTS":
                for c in _cadena(resto):
                    salida.append(Linea(f"PUSH {ord(c)}", ln.archivo, ln.num, nivel + 1))
                    salida.append(Linea("OUT", ln.archivo, ln.num, nivel + 1))
                continue
            if op == "PUTC":
                salida.append(Linea(f"PUSH {resto}", ln.archivo, ln.num, nivel + 1))
                salida.append(Linea("OUT", ln.archivo, ln.num, nivel + 1))
                continue

            salida.append(Linea(txt, ln.archivo, ln.num, nivel))
        return salida

    # ------------------------------------------------------ expresiones
    def evaluar(self, expr: str, pila=()) -> int:
        expr = re.sub(r"'(\\?.)'", lambda m: str(ord(bytes(m.group(1), "utf-8")
                                                     .decode("unicode_escape"))), expr)
        try:
            arbol = ast.parse(expr.strip(), mode="eval")
        except SyntaxError:
            raise ErrorEnsamblador(f"expresión inválida: {expr}")

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, int):
                return n.value
            if isinstance(n, ast.Name):
                nombre = n.id
                if nombre in self.simbolos:
                    return self.simbolos[nombre]
                if nombre in self.equs:
                    if nombre in pila:
                        raise ErrorEnsamblador(f".EQU circular: {nombre}")
                    return self.evaluar(self.equs[nombre], pila + (nombre,))
                raise ErrorEnsamblador(f"símbolo no definido: {nombre}")
            if isinstance(n, ast.UnaryOp):
                v = ev(n.operand)
                if isinstance(n.op, ast.USub):
                    return -v
                if isinstance(n.op, ast.UAdd):
                    return v
                if isinstance(n.op, ast.Invert):
                    return ~v
            if isinstance(n, ast.BinOp):
                a, b = ev(n.left), ev(n.right)
                ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b,
                       ast.Mult: lambda: a * b, ast.FloorDiv: lambda: a // b,
                       ast.Mod: lambda: a % b, ast.LShift: lambda: a << b,
                       ast.RShift: lambda: a >> b, ast.BitOr: lambda: a | b,
                       ast.BitAnd: lambda: a & b, ast.BitXor: lambda: a ^ b,
                       ast.Pow: lambda: a ** b}
                for t, f in ops.items():
                    if isinstance(n.op, t):
                        return f()
            raise ErrorEnsamblador(f"expresión no soportada: {expr}")

        return ev(arbol)

    # ------------------------------------------------- paso 1: direcciones
    def _paso1(self, lineas: list):
        dir_ = BASE
        for ln in lineas:
            txt = ln.texto.strip()
            if txt.endswith(":") and " " not in txt:
                nombre = txt[:-1]
                if nombre in self.simbolos or nombre in self.equs:
                    raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: etiqueta repetida {nombre}")
                self.simbolos[nombre] = dir_
                continue
            partes = txt.split(None, 1)
            op = partes[0].upper()
            resto = partes[1] if len(partes) > 1 else ""
            if op == ".EQU":
                a = _dividir_args(resto)
                if len(a) != 2:
                    raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: .EQU nombre, valor")
                self.equs[a[0]] = a[1]
                continue
            if op == ".VAR":
                nombres = _dividir_args(resto)
                if not nombres:
                    raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: .VAR sin nombres")
                for nombre in nombres:
                    if nombre in self.simbolos:
                        raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: variable repetida {nombre}")
                    self.simbolos[nombre] = dir_
                    self.elementos.append(Elemento("word", palabras=["0"], dir=dir_, tam=8,
                                                   origen=ln))
                    dir_ += 8
                continue
            if op == ".WORD":
                exprs = _dividir_args(resto)
                self.elementos.append(Elemento("word", palabras=exprs, dir=dir_,
                                               tam=8 * len(exprs), origen=ln))
                dir_ += 8 * len(exprs)
                continue
            if op == ".DOUBLE":
                vals = []
                for t in _dividir_args(resto):
                    bits = struct.unpack(">Q", struct.pack(">d", float(t)))[0]
                    vals.append(str(bits))
                self.elementos.append(Elemento("word", palabras=vals, dir=dir_,
                                               tam=8 * len(vals), origen=ln))
                dir_ += 8 * len(vals)
                continue
            if op not in ISA:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: instrucción desconocida '{op}'")
            opcode, tam, tipo = ISA[op]
            if tipo in ("imm", "dir", "addr", "bloque") and not resto:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: {op} necesita un operando")
            if tipo is None and resto:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: {op} no lleva operando")
            if tipo == "bloque" and len(_dividir_args(resto)) != 2:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: {op} necesita dos direcciones")
            self.elementos.append(Elemento("instr", mnem=op, expr=resto or None,
                                           dir=dir_, tam=tam, origen=ln))
            dir_ += tam
        self.fin = dir_

    # ------------------------------------------------- paso 2: código
    def _paso2(self) -> bytearray:
        codigo = bytearray()
        for el in self.elementos:
            try:
                if el.tipo == "word":
                    for p in el.palabras:
                        codigo += (self.evaluar(p) & MASK64).to_bytes(8, "big")
                    continue
                opcode, tam, tipo = ISA[el.mnem]
                b = bytearray([opcode])
                if tipo == "imm":
                    v = self.evaluar(el.expr)
                    if not (-(1 << 63) <= v <= MASK64):
                        raise ErrorEnsamblador(f"inmediato fuera de 64 bits: {el.expr}")
                    b += (v & MASK64).to_bytes(8, "big")
                elif tipo == "dir":
                    v = self.evaluar(el.expr)
                    if not (0 <= v <= 0xFFF8):
                        raise ErrorEnsamblador(f"dirección fuera de la RAM: {el.expr}")
                    b += v.to_bytes(8, "big")
                elif tipo == "addr":
                    v = self.evaluar(el.expr)
                    if not (0 <= v <= 0xFFFF):
                        raise ErrorEnsamblador(f"destino fuera de la RAM: {el.expr}")
                    b += v.to_bytes(8, "big")
                elif tipo == "bloque":
                    for arg in _dividir_args(el.expr):
                        v = self.evaluar(arg)
                        if not (0 <= v <= 0xFFF8):
                            raise ErrorEnsamblador(f"dirección fuera de la RAM: {arg}")
                        b += v.to_bytes(8, "big")
                assert len(b) == tam
                codigo += b
            except ErrorEnsamblador as e:
                o = el.origen
                raise ErrorEnsamblador(f"{o.archivo}:{o.num}: {e}") from None
        return codigo

    # ---------------------------------------------------------- API
    def ensamblar(self, ruta: str):
        self.incluidos.add(os.path.abspath(ruta))
        lineas = self._expandir(self._leer(ruta))
        self._paso1(lineas)
        codigo = self._paso2()
        if BASE + len(codigo) > LIMITE_SEGURO:
            raise ErrorEnsamblador(
                f"el programa ocupa hasta 0x{BASE + len(codigo):04X} e invade la zona de pila")
        return codigo

    def listado(self, codigo: bytes) -> str:
        filas = []
        for el in self.elementos:
            off = el.dir - BASE
            datos = codigo[off:off + el.tam]
            o = el.origen
            src = _quitar_comentario(o.texto).strip() if o else ""
            if el.tipo == "instr":
                src = f"{el.mnem} {el.expr or ''}".strip()
            filas.append(f"{el.dir:04X}  {datos.hex(' ').upper():<36.36}  "
                         f"{'  ' * (o.nivel if o else 0)}{src}")
        etiquetas = {v: k for k, v in self.simbolos.items() if not k.startswith("__m")}
        salida = []
        for f in filas:
            d = int(f[:4], 16)
            if d in etiquetas:
                salida.append(f"{'':4}  {'':36}  {etiquetas[d]}:")
            salida.append(f)
        return "\n".join(salida)


def ensamblar_archivo(ruta: str):
    """Devuelve (codigo: bytearray, simbolos: dict, ensamblador)."""
    ens = Ensamblador()
    codigo = ens.ensamblar(ruta)
    simbolos = {k: v for k, v in ens.simbolos.items() if not k.startswith("__m")}
    return codigo, simbolos, ens


def a_hex(codigo: bytes, por_linea: int = 16) -> str:
    return "\n".join(codigo[i:i + por_linea].hex(" ").upper()
                     for i in range(0, len(codigo), por_linea)) + "\n"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ruta = sys.argv[1]
    salida = None
    if "-o" in sys.argv:
        salida = sys.argv[sys.argv.index("-o") + 1]
    if salida is None:
        salida = os.path.splitext(ruta)[0] + ".hex"
    try:
        codigo, simbolos, ens = ensamblar_archivo(ruta)
    except ErrorEnsamblador as e:
        print(f"Error de ensamblado: {e}")
        sys.exit(2)
    raiz = os.path.splitext(salida)[0]
    with open(salida, "w") as f:
        f.write(a_hex(codigo))
    with open(raiz + ".lst", "w", encoding="utf-8") as f:
        f.write(ens.listado(codigo) + "\n")
    with open(raiz + ".sym", "w") as f:
        json.dump({k: f"0x{v:04X}" for k, v in sorted(simbolos.items(), key=lambda x: x[1])},
                  f, indent=1)
    print(f"{ruta}: {len(codigo)} bytes (0x{BASE:04X}-0x{BASE + len(codigo) - 1:04X}) -> {salida}")


if __name__ == "__main__":
    main()
