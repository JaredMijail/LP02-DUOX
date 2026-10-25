from config import Global

class Cargador():

    def cargar_programa(self, hex_str: str, base: int = Global.PROGRAMA_BASE) -> None:
            """Módulo Cargador: monta en RAM, a partir de `base`, un programa
            dado como cadena hexadecimal de código de máquina."""
            print(hex_str)
            bytes_prog = bytes.fromhex("".join(hex_str.split()))
            self.ram[base:base + len(bytes_prog)] = bytes_prog
            self.PC = base
            print(f"[Cargador] Programa de usuario cargado en 0x{base:04X} "
                  f"({len(bytes_prog)} bytes)")
