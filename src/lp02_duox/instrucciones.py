from enum import IntEnum
from config import Global

class Op(IntEnum):
    """Repertorio de microinstrucciones soportado por el emulador."""
    HALT = 0x00
    ADD = 0x01
    MUL = 0x03
    SUB = 0x02
    DIV = 0x04
    MOD = 0x05
    INT = 0x07
    IRET = 0x08
    EI = 0x09
    DI = 0x0A
    OUT = 0x0B
    LOAD_IMM = 0x99
    STORE = 0x20
    LOAD = 0x21
    PUSH = 0x10
    POP = 0x11
    DUP = 0x12
    SWAP = 0x13
    JZ = 0x28
    JMP= 0x29
        

class Instrucciones():
    def _op_halt(self) -> None:
        print("HALT")
        self.halt = True
    
    def _op_add(self) -> None:
        self.TOS += self.NOS
        print(f"ADD -> {self.TOS}")
        self.PC += 1

    def _op_sub(self) -> None:
        self.TOS = self.NOS - self.TOS
        self.PSW["Z"] = 1 if self.TOS == 0 else 0
        print(f"SUB -> {self.TOS}")
        self.PC += 1

    def _op_mul(self) -> None:
        self.TOS *= self.NOS
        print(f"MUL -> {self.TOS}")
        self.PC += 1

    def _op_div(self) -> None:
        self.TOS = self.TOS // self.NOS
        print(f"DIV -> {self.TOS}")
        self.PC += 1

    def _op_mod(self) -> None:
        self.TOS = self.TOS % self.NOS
        print(f"DIV -> {self.TOS}")
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
    
    def _op_out(self) -> None:
        char = chr(self.TOS & 0xFF)
        self.salida += char
        print(f"OUT '{char}'")
        self.PC += 1
    
    def _op_load_imm(self) -> None:
        self.TOS = self.leer_mem(self.PC + 1)
        print(f"LOAD_IMM {self.TOS}")
        self.PC += 9
    
    def _op_store(self) -> None:
        
        dir_ = self.leer_mem(self.PC + 1)
        self.escribir_mem(dir_, self.TOS)
        print(f"STORE 0x{dir_:04X}")
        self.PC += 12
    
    def _op_load(self) -> None:
        dir_ = self.leer_mem(self.PC + 1)
        self.NOS = self.TOS
        self.TOS = self.leer_mem(dir_)
        print(f"LOAD 0x{dir_:04X} -> {self.TOS}")
        self.PC += 12

    def _op_push(self) -> None:
        self.NOS = self.TOS
        self.TOS = self.leer_mem(self.PC + 1)
        print(f"PUSH {self.TOS}")
        self.PC += 9

    def _op_pop(self) -> None:
        self.TOS = self.NOS
        self.NOS = 0
        print(f"POP {self.TOS}")
        self.PC += 9

    def _op_swap(self) -> None:
        placeholder = self.NOS
        self.NOS = self.TOS
        self.TOS = placeholder
        print(f"SWAP {self.TOS}")  
        self.PC += 1

    def _op_dup(self) -> None:
        self.NOS = self.TOS
        print(f"SWAP {self.TOS}")
        self.PC += 1

    def _op_jz(self) -> None:
        if (self.PSW["Z"] == 1):
            print(f"JZ {self.leer_mem(self.PC + 1)}")
            self.PC = Global.PROGRAMA_BASE + self.leer_mem(self.PC + 1)
        else:
            print(f"No JZ {self.PC - Global.PROGRAMA_BASE}")
            self.PC += 9

    def _op_jmp(self) -> None:
        offset = self.leer_mem(self.PC + 1)
        print(f"JMP {self.leer_mem(self.PC + 1)}")
        self.PC = Global.PROGRAMA_BASE + offset