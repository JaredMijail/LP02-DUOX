"""
Ensamblador para la máquina DUOS (Tarea 10, Grupo F).

Traduce un programa escrito con mnemónicos a la cadena hexadecimal de código
de máquina que entiende el cargador de la Tarea 10. NO amplía el repertorio de
instrucciones: cada macro se expande únicamente a instrucciones nativas.

Repertorio nativo (codificación idéntica a la del emulador de la Tarea 10):

    Mnemónico      Opcode  Bytes  Efecto
    HALT           00      1      detiene la máquina
    ADD            01      1      TOS <- TOS + NOS
    SUB            02      1      TOS <- NOS - TOS ; Z <- (TOS == 0)
    MUL            03      1      TOS <- TOS * NOS
    DIV            04      1      TOS <- TOS // NOS
    MOD            05      1      TOS <- TOS % NOS
    INT            07      1      apila PC+1 y PSW.I ; PC <- MEM[TOS*8]
    IRET (RET)     08      1      desapila PSW.I y PC
    EI / DI        09/0A   1      habilita / deshabilita interrupciones
    OUT            0B      1      escribe el carácter TOS & 0xFF
    LDI  imm       99      9      TOS <- imm            (LOAD_IMM)
    PUSH imm       10      9      NOS <- TOS ; TOS <- imm
    POP            11      9      TOS <- NOS ; NOS <- 0 (ocupa 9 bytes)
    SWAP           13      1      intercambia TOS y NOS
    STORE dir      20      12     MEM[dir] <- TOS
    LOAD  dir      21      12     NOS <- TOS ; TOS <- MEM[dir]
    JZ   etiqueta  28      9      si Z: PC <- 0x1000 + desplazamiento
    JMP  etiqueta  29      9      PC <- 0x1000 + desplazamiento

(DUP 0x12 está declarado en instrucciones.py pero no figura en la tabla de
despacho del emulador, así que el ensamblador lo rechaza.)

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
#   bytes + 3 de relleno ; "salto": desplazamiento respecto a BASE ;
#   "relleno": 8 bytes en cero (POP)
ISA = {
    "HALT": (0x00, 1, None),
    "ADD": (0x01, 1, None),
    "SUB": (0x02, 1, None),
    "MUL": (0x03, 1, None),
    "DIV": (0x04, 1, None),
    "MOD": (0x05, 1, None),
    "INT": (0x07, 1, None),
    "IRET": (0x08, 1, None),
    "RET": (0x08, 1, None),
    "EI": (0x09, 1, None),
    "DI": (0x0A, 1, None),
    "OUT": (0x0B, 1, None),
    "LDI": (0x99, 9, "imm"),
    "LOAD_IMM": (0x99, 9, "imm"),
    "PUSH": (0x10, 9, "imm"),
    "POP": (0x11, 9, "relleno"),
    "SWAP": (0x13, 1, None),
    "STORE": (0x20, 12, "dir"),
    "LOAD": (0x21, 12, "dir"),
    "JZ": (0x28, 9, "salto"),
    "JMP": (0x29, 9, "salto"),
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
                for nombre in _dividir_args(resto):
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
            if op == "DUP":
                raise ErrorEnsamblador(
                    f"{ln.archivo}:{ln.num}: DUP no está en la tabla de despacho del "
                    "emulador de la Tarea 10 (la máquina se detendría)")
            if op not in ISA:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: instrucción desconocida '{op}'")
            opcode, tam, tipo = ISA[op]
            if tipo in ("imm", "dir", "salto") and not resto:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: {op} necesita un operando")
            if tipo in (None, "relleno") and resto:
                raise ErrorEnsamblador(f"{ln.archivo}:{ln.num}: {op} no lleva operando")
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
                    b += v.to_bytes(8, "big") + bytes(3)
                elif tipo == "salto":
                    v = self.evaluar(el.expr)
                    if v < BASE:
                        raise ErrorEnsamblador(f"destino de salto antes de 0x1000: {el.expr}")
                    b += (v - BASE).to_bytes(8, "big")
                elif tipo == "relleno":
                    b += bytes(8)
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
