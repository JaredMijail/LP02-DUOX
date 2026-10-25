class Global():
    WORD_SIZE = 8            
    RAM_SIZE = 65536         
    STACK_TOP = 0xFFFF
    
    VEC_TECLADO = 0x0000          
    VEC_SYSCALL_PRINT = 0x0008    
    
    ISR_TECLADO_ADDR = 0x0100
    SYSCALL_PRINT_ADDR = 0x0200
    BUFFER_SALIDA_ADDR = 0x2000
    
    PROGRAMA_BASE = 0x1000

parametrosEmu = {
    "ram" : bytearray(Global.RAM_SIZE),
    "PC" : 0,
    "TOS" : 0,                       
    "NOS" : 0,                     
    "SP" : Global.STACK_TOP,
    "PSW" : {"Z": 0, "N": 0, "I": 0},
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
        def emitir_caracter(codigo: int) -> str:
            return (
                f"10 00 00 00 00 00 00 00 {codigo:02X} "   
                "20 00 00 00 00 00 00 20 00 00 00 00 "    
                "10 00 00 00 00 00 00 00 01 "              
                "07"                                        
            )
 
        instrucciones = " ".join(emitir_caracter(ord(c)) for c in "hola\n")
        return instrucciones + " 00"  
