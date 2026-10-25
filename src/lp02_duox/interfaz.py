import sys
import textwrap
from typing import Callable, Dict

class Interfaz():

    def __init__(self, emu):
        self.acciones: Dict[str, Callable[[], None]] = {
            "1": emu.paso,
            "2": emu.ejecutar_todo,
            "3": lambda: setattr(emu, "interrupt_pending", True),
            "4": lambda: print(f"\nSalida de consola: {emu.salida}"),
        }
    
        self.menu = textwrap.dedent("""
            === SO DUOS ===
            1. Ejecutar paso a paso
            2. Ejecutar todo
            3. Inyectar interrupción de teclado
            4. Mostrar salida
            5. Salir
        """)

    def ejecutar(self):
        while True:
            print(self.menu)
            opcion = input("Opción: ").strip()
            if opcion == "5":
                sys.exit()
            accion = self.acciones.get(opcion)
            if accion is None:
                print("Opción inválida.")
                continue
            accion()
            if opcion == "3":
                print("Interrupción pendiente. Se atenderá en el próximo ciclo si PSW.I=1.")
    
    