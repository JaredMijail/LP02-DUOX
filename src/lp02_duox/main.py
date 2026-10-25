from __future__ import annotations

import sys
from emuladorDuos import EmuladorDUOS
from interfaz import Interfaz
from cargador import Cargador 
import config
 

def main() -> None:
    
    try :
        archivo = open(sys.argv[1])
        programa = archivo.read()
        archivo.close()
    except:
        programa = config._programa_demo()
    
    emu = EmuladorDUOS(config.parametrosEmu)
    emu.cargar_SO(config.parametrosSo)

    Cargador.cargar_programa(emu, programa, config.Global.PROGRAMA_BASE)

    ui = Interfaz(emu)
    ui.ejecutar()

if __name__ == "__main__":
    main()
