from enum import IntEnum
from config import Global

MASK64 = (1 << 64) - 1
BIT63 = 1 << 63


class Op(IntEnum):
    """Repertorio de instrucciones de la máquina DUOS (docs/ISA_CPU.md)."""
    NOP = 0x00
    ADD = 0x01
    SUB = 0x02
    MUL = 0x03
    DIV = 0x04
    MOD = 0x05
    AND = 0x06
    OR = 0x07
    XOR = 0x08
    NOT = 0x09
    SHL = 0x0A
    SHR = 0x0B

    PUSH = 0x10
    POP = 0x11
    DUP = 0x12
    SWAP = 0x13
    LOAD = 0x14
    STORE = 0x15
    LOAD_OFF = 0x16
    STORE_OFF = 0x17
    LOAD_IMM = 0x18

    JMP = 0x20
    JZ = 0x21
    JNZ = 0x22
    JGT = 0x23
    JLT = 0x24
    CALL = 0x25
    RET = 0x26
    HALT = 0x27

    GET_CORE = 0x30
    LOCK = 0x31
    UNLOCK = 0x32
    CORE_START = 0x33
    CORE_YIELD = 0x34

    IN_PORT = 0x40
    OUT_PORT = 0x41
    NET_SEND = 0x42
    NET_RECV = 0x43
    NET_STAT = 0x44
    OUT = 0x45

    CACHE_FLUSH = 0x50
    MEM_COPY = 0x51
    SET_FLAGS = 0x52
    GET_FLAGS = 0x53
    INT = 0x54
    IRET = 0x55
    EI = 0x56
    DI = 0x57


class Instrucciones():
    """Semántica de las instrucciones; se ejecuta en el contexto del emulador.

    TOS/NOS forman la pila de registros: _empujar deja el valor en TOS y corre
    el anterior a NOS; _sacar devuelve TOS y sube NOS. SP/BP son la pila de
    memoria (direcciones de retorno y marcos).
    """

    def _empujar(self, val: int) -> None:
        self.NOS = self.TOS
        self.TOS = val

    def _sacar(self) -> int:
        val = self.TOS
        self.TOS = self.NOS
        self.NOS = 0
        return val

    def _banderas(self, res: int, acarreo: int = 0, desborde: int = 0) -> None:
        """Actualiza PSW a partir del resultado (64 bits)."""
        self.PSW["Z"] = int((res & MASK64) == 0)
        self.PSW["N"] = int(bool(res & BIT63))
        self.PSW["C"] = acarreo
        self.PSW["V"] = desborde

    def _error(self, motivo: str) -> None:
        print(f"\n[Error de Hardware] {motivo} en PC=0x{self.PC:04X}")
        self.halt = True

    def _rango_valido(self, dir_: int, largo: int) -> bool:
        if dir_ < 0 or largo < 0 or dir_ + largo > Global.RAM_SIZE:
            self._error(f"rango fuera de la RAM: 0x{dir_:04X} + {largo} B")
            return False
        return True

    # ------------------------------------------------- aritmética y lógica
    def _op_nop(self) -> None:
        print("NOP")
        self.PC += 1

    def _op_add(self) -> None:
        a, b = self.NOS, self.TOS
        self.TOS = a + b
        aa, bb, rr = a & MASK64, b & MASK64, self.TOS & MASK64
        self._banderas(self.TOS,
                       acarreo=int(aa + bb > MASK64),
                       desborde=int(bool(~(aa ^ bb) & (aa ^ rr) & BIT63)))
        print(f"ADD -> {self.TOS}")
        self.PC += 1

    def _op_sub(self) -> None:
        a, b = self.NOS, self.TOS
        self.TOS = a - b
        aa, bb, rr = a & MASK64, b & MASK64, self.TOS & MASK64
        self._banderas(self.TOS,
                       acarreo=int(aa < bb),
                       desborde=int(bool((aa ^ bb) & (aa ^ rr) & BIT63)))
        print(f"SUB -> {self.TOS}")
        self.PC += 1

    def _op_mul(self) -> None:
        self.TOS *= self.NOS
        self._banderas(self.TOS)
        print(f"MUL -> {self.TOS}")
        self.PC += 1

    def _op_div(self) -> None:
        if self.NOS == 0:
            self._error("división por cero")
            return
        self.TOS //= self.NOS
        self._banderas(self.TOS)
        print(f"DIV -> {self.TOS}")
        self.PC += 1

    def _op_mod(self) -> None:
        if self.NOS == 0:
            self._error("módulo por cero")
            return
        self.TOS %= self.NOS
        self._banderas(self.TOS)
        print(f"MOD -> {self.TOS}")
        self.PC += 1

    def _op_and(self) -> None:
        self.TOS &= self.NOS
        self._banderas(self.TOS)
        print(f"AND -> {self.TOS}")
        self.PC += 1

    def _op_or(self) -> None:
        self.TOS |= self.NOS
        self._banderas(self.TOS)
        print(f"OR -> {self.TOS}")
        self.PC += 1

    def _op_xor(self) -> None:
        self.TOS ^= self.NOS
        self._banderas(self.TOS)
        print(f"XOR -> {self.TOS}")
        self.PC += 1

    def _op_not(self) -> None:
        self.TOS = ~self.TOS & MASK64
        self._banderas(self.TOS)
        print(f"NOT -> {self.TOS}")
        self.PC += 1

    def _op_shl(self) -> None:
        self.TOS = (self.NOS << self.TOS) & MASK64
        self._banderas(self.TOS)
        print(f"SHL -> {self.TOS}")
        self.PC += 1

    def _op_shr(self) -> None:
        self.TOS = (self.NOS & MASK64) >> self.TOS
        self._banderas(self.TOS)
        print(f"SHR -> {self.TOS}")
        self.PC += 1

    # ------------------------------------------------------- pila y memoria
    def _op_push(self) -> None:
        self._empujar(self.leer_mem(self.PC + 1))
        print(f"PUSH {self.TOS}")
        self.PC += 9

    def _op_pop(self) -> None:
        print(f"POP {self._sacar()}")
        self.PC += 1

    def _op_dup(self) -> None:
        self.NOS = self.TOS
        print(f"DUP {self.TOS}")
        self.PC += 1

    def _op_swap(self) -> None:
        self.NOS, self.TOS = self.TOS, self.NOS
        print(f"SWAP {self.TOS}")
        self.PC += 1

    def _op_load(self) -> None:
        dir_ = self.leer_mem(self.PC + 1)
        self._empujar(self.leer_mem(dir_))
        print(f"LOAD 0x{dir_:04X} -> {self.TOS}")
        self.PC += 9

    def _op_store(self) -> None:
        dir_ = self.leer_mem(self.PC + 1)
        self.escribir_mem(dir_, self.TOS)
        print(f"STORE 0x{dir_:04X} <- {self.TOS}")
        self.PC += 9

    def _op_load_off(self) -> None:
        off = self._sacar()
        self._empujar(self.leer_mem(self.BP + off))
        print(f"LOAD_OFF [BP+{off}] -> {self.TOS}")
        self.PC += 1

    def _op_store_off(self) -> None:
        off = self._sacar()
        val = self._sacar()
        self.escribir_mem(self.BP + off, val)
        print(f"STORE_OFF [BP+{off}] <- {val}")
        self.PC += 1

    def _op_load_imm(self) -> None:
        self.TOS = self.leer_mem(self.PC + 1)
        self._banderas(self.TOS)
        print(f"LOAD_IMM {self.TOS}")
        self.PC += 9

    # --------------------------------------------------- control de flujo
    def _op_jmp(self) -> None:
        offset = self.leer_mem(self.PC + 1)
        self.PC = Global.PROGRAMA_BASE + offset
        print(f"JMP 0x{self.PC:04X}")
        

    def _salto(self, condicion: bool, nombre: str) -> None:
        destino = self.leer_mem(self.PC + 1)
        if condicion:
            self.PC = Global.PROGRAMA_BASE +  destino
            print(f"{nombre} 0x{self.PC:04X}")
        else:
            self.PC += 9

    def _op_jz(self) -> None:
        self._salto(self.PSW["Z"] == 1, "JZ")

    def _op_jnz(self) -> None:
        self._salto(self.PSW["Z"] == 0, "JNZ")

    def _op_jgt(self) -> None:
        self._salto(self.PSW["Z"] == 0 and self.PSW["N"] == self.PSW["V"], "JGT")

    def _op_jlt(self) -> None:
        self._salto(self.PSW["N"] != self.PSW["V"], "JLT")

    def _op_call(self) -> None:
        destino = self.leer_mem(self.PC + 1)
        self._push(self.PC + 9)
        print(f"CALL 0x{destino:04X}")
        self.PC = destino

    def _op_ret(self) -> None:
        if self.SP >= Global.STACK_TOP:
            self._error("RET sin dirección de retorno")
            return
        self.PC = self._pop()
        print(f"RET -> 0x{self.PC:04X}")

    def _op_halt(self) -> None:
        print("HALT")
        self.halt = True

    # ------------------------------------------------- concurrencia
    def _op_get_core(self) -> None:
        self._empujar(self.PSW["CORE_ID"])
        print(f"GET_CORE -> {self.TOS}")
        self.PC += 1

    def _op_lock(self) -> None:
        self.PSW["LOCK"] = 1
        self.bus_bloqueado = True
        print("LOCK")
        self.PC += 1

    def _op_unlock(self) -> None:
        self.PSW["LOCK"] = 0
        self.bus_bloqueado = False
        print("UNLOCK")
        self.PC += 1

    def _op_core_start(self) -> None:
        destino = self.leer_mem(self.PC + 1)
        self._ctx[1] = (destino, 0, 0, Global.STACK_TOP_N1, Global.STACK_TOP_N1,
                        {"C": 0, "Z": 0, "N": 0, "V": 0, "I": 0, "LOCK": 0, "CORE_ID": 1},
                        False)
        self._activos[1] = True
        print(f"CORE_START núcleo 1 en 0x{destino:04X}")
        self.PC += 9

    def _op_core_yield(self) -> None:
        self._ceder = True
        print("CORE_YIELD")
        self.PC += 1

    # ------------------------------------------------------------- E/S
    def _op_in_port(self) -> None:
        puerto = self._sacar()
        self._empujar(self.puertos.get(puerto, 0))
        print(f"IN_PORT {puerto} -> {self.TOS}")
        self.PC += 1

    def _op_out_port(self) -> None:
        puerto = self._sacar()
        valor = self._sacar()
        self.puertos[puerto] = valor & MASK64
        print(f"OUT_PORT {puerto} <- {valor}")
        self.PC += 1

    def _op_out(self) -> None:
        char = chr(self.TOS & 0xFF)
        self.salida += char
        print(f"OUT '{char}'")
        self.PC += 1

    def _op_net_send(self) -> None:
        largo = self._sacar()
        addr = self._sacar()
        if not self._rango_valido(addr, largo):
            return
        paquete = bytes(self.ram[addr:addr + largo])
        self.nic_tx.append(paquete)
        self.nic_rx.append(paquete)          # el NIC emulado es loopback
        print(f"NET_SEND {len(paquete)} B desde 0x{addr:04X}")
        self.PC += 1

    def _op_net_recv(self) -> None:
        largo = self._sacar()
        addr = self._sacar()
        if not self._rango_valido(addr, largo):
            return
        if not self.nic_rx:
            self._empujar(0)
            print("NET_RECV sin paquetes")
            self.PC += 1
            return
        paquete = self.nic_rx.pop(0)
        copia = paquete[:largo]
        self.ram[addr:addr + len(copia)] = copia
        if len(copia) < len(paquete):
            self.nic_rx.insert(0, paquete[len(copia):])
        self._empujar(len(copia))
        print(f"NET_RECV {len(copia)} B en 0x{addr:04X}")
        self.PC += 1

    def _op_net_stat(self) -> None:
        self._empujar(sum(len(p) for p in self.nic_rx))
        print(f"NET_STAT -> {self.TOS} B pendientes")
        self.PC += 1

    # ---------------------------------------------------------- sistema
    def _op_cache_flush(self) -> None:
        print("CACHE_FLUSH")
        self.PC += 1

    def _op_mem_copy(self) -> None:
        origen = self.leer_mem(self.PC + 1)
        destino = self.leer_mem(self.PC + 9)
        palabras = self._sacar()
        largo = palabras * Global.WORD_SIZE
        if not self._rango_valido(origen, largo) or not self._rango_valido(destino, largo):
            return
        self.ram[destino:destino + largo] = self.ram[origen:origen + largo]
        print(f"MEM_COPY 0x{origen:04X} -> 0x{destino:04X} ({palabras} palabras)")
        self.PC += 17

    def _op_set_flags(self) -> None:
        valor = self._sacar()
        self.PSW["C"] = valor & 1
        self.PSW["Z"] = (valor >> 1) & 1
        self.PSW["N"] = (valor >> 2) & 1
        self.PSW["V"] = (valor >> 3) & 1
        self.PSW["LOCK"] = (valor >> 4) & 1
        self.bus_bloqueado = bool(self.PSW["LOCK"])
        print(f"SET_FLAGS 0x{valor & MASK64:016X}")
        self.PC += 1

    def _op_get_flags(self) -> None:
        valor = (self.PSW["C"] | self.PSW["Z"] << 1 | self.PSW["N"] << 2
                 | self.PSW["V"] << 3 | self.PSW["LOCK"] << 4 | self.PSW["CORE_ID"] << 8)
        self._empujar(valor)
        print(f"GET_FLAGS -> 0x{valor:016X}")
        self.PC += 1

    def _op_int(self) -> None:
        num = self.TOS
        print(f"INT {num}")
        self._push(self.PC + 1)
        self._push(self.PSW["I"])
        self.PC = self.leer_mem(num * Global.WORD_SIZE)

    def _op_iret(self) -> None:
        self.PSW["I"] = self._pop()
        self.PC = self._pop()
        print("IRET")

    def _op_ei(self) -> None:
        self.PSW["I"] = 1
        print("EI")
        self.PC += 1

    def _op_di(self) -> None:
        self.PSW["I"] = 0
        print("DI")
        self.PC += 1
