from config import Global
from instrucciones import Op, Instrucciones
from typing import Callable, Dict

class EmuladorDUOS:
    """Emulador de la máquina von Neumann DUOS."""
 
    def __init__(self, parametrosEmu ) -> None:
        self.ram = parametrosEmu["ram"]
        self.PC = parametrosEmu["PC"]
        self.TOS = parametrosEmu["TOS"]                       
        self.NOS = parametrosEmu["NOS"]                       
        self.SP = parametrosEmu["SP"]
        self.PSW = parametrosEmu["PSW"]
        self.halt = parametrosEmu["halt"]
        self.interrupt_pending = parametrosEmu["interrupt_pending"]
        self.salida = parametrosEmu["salida"]
        
        self._dispatch: Dict[int, Callable[[], None]] = {
            Op.HALT: Instrucciones._op_halt,
            Op.ADD: Instrucciones._op_add,
            Op.SUB: Instrucciones._op_sub,
            Op.MUL: Instrucciones._op_mul,
            Op.DIV: Instrucciones._op_div,
            Op.MOD: Instrucciones._op_mod,
            Op.INT: Instrucciones._op_int,
            Op.IRET: Instrucciones._op_iret,
            Op.EI: Instrucciones._op_ei,
            Op.DI: Instrucciones._op_di,
            Op.OUT: Instrucciones._op_out,
            Op.LOAD_IMM: Instrucciones._op_load_imm,
            Op.STORE: Instrucciones._op_store,
            Op.LOAD: Instrucciones._op_load,
            Op.PUSH: Instrucciones._op_push,
            Op.POP: Instrucciones._op_pop,
            Op.SWAP: Instrucciones._op_swap,
            Op.JZ: Instrucciones._op_jz,
            Op.JMP: Instrucciones._op_jmp

        }
 
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
            print(f"\n[Error de Hardware] Acceso fuera de los límites de la RAM: 0x{dir_:04X}")
            self.halt = True
            return False
        return True

    def cargar_SO(self, parametrosSo) -> None:
            """Inicializa la máquina y monta el mini-SO residente: vector de
            interrupciones, ISR de teclado y syscall de impresión."""
            self.ram = parametrosSo["ram"]
            self.PC = parametrosSo["PC"]
            self.SP = parametrosSo["SP"]
            
            self.halt = parametrosSo["halt"]
            self.salida = parametrosSo["salida"]
            
            self.PSW["I"] = 0
     
            self.escribir_mem(Global.VEC_TECLADO, Global.ISR_TECLADO_ADDR)
            self.escribir_mem(Global.VEC_SYSCALL_PRINT, Global.SYSCALL_PRINT_ADDR)
     
            self.ram[Global.ISR_TECLADO_ADDR] = Op.IRET
     
            self.ram[Global.SYSCALL_PRINT_ADDR] = Op.LOAD
            self.escribir_mem(Global.SYSCALL_PRINT_ADDR + 1, Global.BUFFER_SALIDA_ADDR)
            self.ram[Global.SYSCALL_PRINT_ADDR + 12] = Op.OUT
            self.ram[Global.SYSCALL_PRINT_ADDR + 13] = Op.IRET
     
            print(f"[SO] DUOS-OS cargado. Vector teclado: 0x{Global.ISR_TECLADO_ADDR:04X}, "
                  f"Syscall print: 0x{Global.SYSCALL_PRINT_ADDR:04X}")
     
 
    def cargar_programa(self, hex_str: str, base: int = Global.PROGRAMA_BASE) -> None:
        """Módulo Cargador: monta en RAM, a partir de `base`, un programa
        dado como cadena hexadecimal de código de máquina."""
        bytes_prog = bytes.fromhex("".join(hex_str.split()))
        print(bytes_prog)
        self.ram[base:base + len(bytes_prog)] = bytes_prog
        self.PC = base
        print(f"[Cargador] Programa de usuario cargado en 0x{base:04X} "
              f"({len(bytes_prog)} bytes)")
 
    def _push(self, val: int) -> None:
        self.SP -= Global.WORD_SIZE
        self.escribir_mem(self.SP, val)
 
    def _pop(self) -> int:
        val = self.leer_mem(self.SP)
        self.SP += Global.WORD_SIZE
        return val
 
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
 
    def paso(self) -> bool:
        print("PC",  self.PC - Global.PROGRAMA_BASE, "\t", "Stack: ",  (self.TOS, self.NOS))
        """Ejecuta un ciclo fetch-decode-execute. Devuelve False si la
        máquina se detuvo (HALT o error de hardware)."""
        if self.halt:
            return False
        if self.atender_interrupcion():
            return True
 
        ir = self.ram[self.PC]
        print(f"PC=0x{self.PC:04X} IR=0x{ir:02X}", end=" ")
 
        manejador = self._dispatch.get(ir)
        if manejador is None:
            print(f"?? 0x{ir:02X} (instrucción no reconocida)")
            self.halt = True
            return False
 
        manejador(self)
        return not self.halt
 
    def ejecutar_todo(self) -> None:
        """Ejecuta instrucciones hasta HALT o error de hardware."""
        while not self.halt:
            if not self.paso():
                break