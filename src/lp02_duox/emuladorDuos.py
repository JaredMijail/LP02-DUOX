from config import Global, PSW_INICIAL
from instrucciones import Op, Instrucciones
from typing import Callable, Dict

PSW_N1 = dict(PSW_INICIAL, CORE_ID=1)


class EmuladorDUOS(Instrucciones):
    """Emulador de la máquina von Neumann DUOS (dos núcleos, ISA de docs/ISA_CPU.md)."""

    def __init__(self, parametrosEmu) -> None:
        self.ram = parametrosEmu["ram"]
        self.PC = parametrosEmu["PC"]
        self.TOS = parametrosEmu["TOS"]
        self.NOS = parametrosEmu["NOS"]
        self.SP = parametrosEmu["SP"]
        self.BP = parametrosEmu.get("BP", parametrosEmu["SP"])
        self.PSW = parametrosEmu["PSW"]
        for bandera, valor in PSW_INICIAL.items():
            self.PSW.setdefault(bandera, valor)
        self.halt = parametrosEmu["halt"]
        self.interrupt_pending = parametrosEmu["interrupt_pending"]
        self.salida = parametrosEmu["salida"]

        self.puertos: Dict[int, int] = {}
        self.nic_rx: list = []
        self.nic_tx: list = []
        self.bus_bloqueado = False

        self._nucleo = 0
        self._activos = [True, False]
        self._ctx = [(self.PC, self.TOS, self.NOS, self.SP, self.BP, self.PSW, self.halt),
                     (0, 0, 0, Global.STACK_TOP_N1, Global.STACK_TOP_N1, dict(PSW_N1), True)]
        self._ceder = False

        self._dispatch: Dict[int, Callable[[], None]] = {
            Op.NOP: Instrucciones._op_nop,
            Op.ADD: Instrucciones._op_add,
            Op.SUB: Instrucciones._op_sub,
            Op.MUL: Instrucciones._op_mul,
            Op.DIV: Instrucciones._op_div,
            Op.MOD: Instrucciones._op_mod,
            Op.AND: Instrucciones._op_and,
            Op.OR: Instrucciones._op_or,
            Op.XOR: Instrucciones._op_xor,
            Op.NOT: Instrucciones._op_not,
            Op.SHL: Instrucciones._op_shl,
            Op.SHR: Instrucciones._op_shr,
            Op.PUSH: Instrucciones._op_push,
            Op.POP: Instrucciones._op_pop,
            Op.DUP: Instrucciones._op_dup,
            Op.SWAP: Instrucciones._op_swap,
            Op.LOAD: Instrucciones._op_load,
            Op.STORE: Instrucciones._op_store,
            Op.LOAD_OFF: Instrucciones._op_load_off,
            Op.STORE_OFF: Instrucciones._op_store_off,
            Op.LOAD_IMM: Instrucciones._op_load_imm,
            Op.JMP: Instrucciones._op_jmp,
            Op.JZ: Instrucciones._op_jz,
            Op.JNZ: Instrucciones._op_jnz,
            Op.JGT: Instrucciones._op_jgt,
            Op.JLT: Instrucciones._op_jlt,
            Op.CALL: Instrucciones._op_call,
            Op.RET: Instrucciones._op_ret,
            Op.HALT: Instrucciones._op_halt,
            Op.GET_CORE: Instrucciones._op_get_core,
            Op.LOCK: Instrucciones._op_lock,
            Op.UNLOCK: Instrucciones._op_unlock,
            Op.CORE_START: Instrucciones._op_core_start,
            Op.CORE_YIELD: Instrucciones._op_core_yield,
            Op.IN_PORT: Instrucciones._op_in_port,
            Op.OUT_PORT: Instrucciones._op_out_port,
            Op.NET_SEND: Instrucciones._op_net_send,
            Op.NET_RECV: Instrucciones._op_net_recv,
            Op.NET_STAT: Instrucciones._op_net_stat,
            Op.OUT: Instrucciones._op_out,
            Op.CACHE_FLUSH: Instrucciones._op_cache_flush,
            Op.MEM_COPY: Instrucciones._op_mem_copy,
            Op.SET_FLAGS: Instrucciones._op_set_flags,
            Op.GET_FLAGS: Instrucciones._op_get_flags,
            Op.INT: Instrucciones._op_int,
            Op.IRET: Instrucciones._op_iret,
            Op.EI: Instrucciones._op_ei,
            Op.DI: Instrucciones._op_di,
        }

    # ------------------------------------------------------------- memoria
    def escribir_mem(self, dir_: int, val: int) -> None:
        """Escribe una palabra de 64 bits en RAM (big-endian)."""
        if not self._direccion_valida(dir_):
            return
        for i in range(Global.WORD_SIZE - 1, -1, -1):
            self.ram[dir_ + i] = val & 0xFF
            val >>= 8

    def leer_mem(self, dir_: int) -> int:
        """Lee una palabra de 64 bits desde RAM (big-endian)."""
        if not self._direccion_valida(dir_):
            return 0
        val = 0
        for i in range(Global.WORD_SIZE):
            val = (val << 8) | self.ram[dir_ + i]
        return val

    def _direccion_valida(self, dir_: int) -> bool:
        if dir_ < 0 or dir_ + Global.WORD_SIZE > Global.RAM_SIZE:
            self._error(f"acceso fuera de los límites de la RAM: 0x{dir_:04X}")
            return False
        return True

    def _error(self, motivo: str) -> None:
        print(f"\n[Error de Hardware] {motivo}")
        self.halt = True

    # ------------------------------------------------------ pila de memoria
    def _push(self, val: int) -> None:
        self.SP -= Global.WORD_SIZE
        self.escribir_mem(self.SP, val)

    def _pop(self) -> int:
        val = self.leer_mem(self.SP)
        self.SP += Global.WORD_SIZE
        return val

    # ------------------------------------------------------------- arranque
    def _reiniciar_nucleos(self) -> None:
        self._nucleo = 0
        self._activos = [True, False]
        self._ctx = [(self.PC, self.TOS, self.NOS, self.SP, self.BP, self.PSW, self.halt),
                     (0, 0, 0, Global.STACK_TOP_N1, Global.STACK_TOP_N1, dict(PSW_N1), True)]

    def cargar_SO(self, parametrosSo) -> None:
        """Inicializa la máquina y monta el mini-SO residente: vector de
        interrupciones, ISR de teclado y llamada al sistema de impresión."""
        self.ram = parametrosSo["ram"]
        self.PC = parametrosSo["PC"]
        self.SP = parametrosSo["SP"]
        self.BP = parametrosSo["SP"]
        self.halt = parametrosSo["halt"]
        self.salida = parametrosSo["salida"]
        self.PSW = dict(PSW_INICIAL)
        self._reiniciar_nucleos()

        self.escribir_mem(Global.VEC_TECLADO, Global.ISR_TECLADO_ADDR)
        self.escribir_mem(Global.VEC_SYSCALL_PRINT, Global.SYSCALL_PRINT_ADDR)

        self.ram[Global.ISR_TECLADO_ADDR] = Op.IRET

        self.ram[Global.SYSCALL_PRINT_ADDR] = Op.LOAD
        self.escribir_mem(Global.SYSCALL_PRINT_ADDR + 1, Global.BUFFER_SALIDA_ADDR)
        self.ram[Global.SYSCALL_PRINT_ADDR + 9] = Op.OUT
        self.ram[Global.SYSCALL_PRINT_ADDR + 10] = Op.IRET

        print(f"[SO] DUOS-OS cargado. Vector teclado: 0x{Global.VEC_TECLADO:04X}, "
              f"syscall print: 0x{Global.SYSCALL_PRINT_ADDR:04X}")

    def cargar_programa(self, hex_str: str, base: int = Global.PROGRAMA_BASE) -> None:
        """Módulo Cargador: monta en RAM, a partir de `base`, un programa
        dado como cadena hexadecimal de código de máquina."""
        bytes_prog = bytes.fromhex("".join(hex_str.split()))
        self.ram[base:base + len(bytes_prog)] = bytes_prog
        self.PC = base
        self._reiniciar_nucleos()
        print(f"[Cargador] Programa de usuario cargado en 0x{base:04X} "
              f"({len(bytes_prog)} bytes)")

    # ------------------------------------------------------------ ejecución
    def atender_interrupcion(self) -> bool:
        """Atiende una interrupción de teclado pendiente si están habilitadas
        (PSW.I = 1). Devuelve True si se atendió alguna."""
        if self.interrupt_pending and self.PSW["I"] == 1:
            print("\n[SO] ¡Interrupción de teclado! Guardando estado...")
            self._push(self.PC)
            self._push(self.PSW["I"])
            self.PC = self.leer_mem(Global.VEC_TECLADO)
            self.PSW["I"] = 0
            self.interrupt_pending = False
            return True
        return False

    def _rotar(self) -> None:
        """Guarda el núcleo actual y pasa al otro si está vivo (turno rotativo)."""
        otro = 1 - self._nucleo
        self._ctx[self._nucleo] = (self.PC, self.TOS, self.NOS, self.SP, self.BP,
                                   self.PSW, self.halt)
        if not (self._activos[otro] and not self._ctx[otro][6]):
            return
        (self.PC, self.TOS, self.NOS, self.SP, self.BP, self.PSW, self.halt) = self._ctx[otro]
        self._nucleo = otro

    def paso(self) -> bool:
        """Ejecuta un ciclo fetch-decode-execute del núcleo en curso. Devuelve
        False cuando se han detenido todos los núcleos."""
        if self.halt:
            self._rotar()
            if self.halt:
                return False

        print("PC",  self.PC - Global.PROGRAMA_BASE, "\t", "Stack: ",  (self.TOS, self.NOS))
        if self.atender_interrupcion():
            return True

        ir = self.ram[self.PC]
        print(f"PC=0x{self.PC:04X} IR=0x{ir:02X}", end=" ")

        manejador = self._dispatch.get(ir)
        if manejador is None:
            print(f"?? 0x{ir:02X} (instrucción no reconocida)")
            self.halt = True
        else:
            manejador(self)
        if self._activos[1] or self.halt or self._ceder:
            self._ceder = False
            self._rotar()
        return not self.halt

    def ejecutar_todo(self) -> None:
        """Ejecuta instrucciones hasta que se detienen todos los núcleos."""
        while self.paso():
            pass
