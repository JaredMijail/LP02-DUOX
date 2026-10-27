class Global():
    WORD_SIZE = 8            # bytes por palabra (64 bits, big-endian)
    RAM_SIZE = 65536         # 64 KB direccionables (16 bits)
    STACK_TOP = 0xFFFF       # pila del núcleo 0 (crece hacia abajo)
    STACK_TOP_N1 = 0xF800    # pila del núcleo 1 (2 KB)

    VEC_TECLADO = 0x0000
    VEC_SYSCALL_PRINT = 0x0008

    ISR_TECLADO_ADDR = 0x0100
    SYSCALL_PRINT_ADDR = 0x0200
    BUFFER_SALIDA_ADDR = 0x2000

    PROGRAMA_BASE = 0x1000

PSW_INICIAL = {"C": 0, "Z": 0, "N": 0, "V": 0, "I": 0, "LOCK": 0, "CORE_ID": 0}

parametrosEmu = {
    "ram" : bytearray(Global.RAM_SIZE),
    "PC" : 0,
    "TOS" : 0,
    "NOS" : 0,
    "SP" : Global.STACK_TOP,
    "BP" : Global.STACK_TOP,
    "PSW" : dict(PSW_INICIAL),
    "halt" : False,
    "interrupt_pending" : False,
    "salida" : ""
}

parametrosSo = {
    "ram" : bytearray(Global.RAM_SIZE),
    "PC" : 0,
    "SP" : Global.STACK_TOP,
    "halt" : False,
    "salida" : ""
}

def _programa_demo() -> str:
        """Programa de ejemplo: imprime "hola" con la llamada al sistema 1."""
        from instrucciones import Op

        push = f"{int(Op.PUSH):02X}"
        def emitir_caracter(codigo: int) -> str:
            return (
                f"{push} {codigo:016X} "                              # PUSH codigo
                f"{int(Op.STORE):02X} {Global.BUFFER_SALIDA_ADDR:016X} "  # STORE buffer
                f"{push} 0000000000000001 "                           # PUSH 1 (syscall print)
                f"{int(Op.INT):02X}"                                  # INT
            )

        instrucciones = " ".join(emitir_caracter(ord(c)) for c in "hola\n")
        return instrucciones + f" {int(Op.HALT):02X}"
