* **Nivel 0: Registros de Control del Sistema (Por Núcleo):**
* `PC` (Program Counter): 64 bits. Apunta a la siguiente instrucción.
* `SP` (Stack Pointer): 64 bits. Apunta al tope de la pila en memoria.
* `BP` (Base Pointer): 64 bits. Apunta al marco de pila actual.
* `FLAGS` (Registro de Banderas): 64 bits (C: Carga, Z: Cero, N: Negativo, V: Desbordamiento, LOCK: Bus bloqueado, CORE_ID: Identificador de núcleo 0 o 1).
* `MAR` (Memory Address Register) y `MBR` (Memory Buffer Register): 64 bits para el ciclo de lectura/escritura de bus.


* **Nivel 1: Caché L1 (Privada por Núcleo):** 64 KB de L1-Instruction (L1i) y 64 KB de L1-Data (L1d) por cada núcleo.
* **Nivel 2: Caché L2 (Compartida):** 2 MB de caché unificada interconectada por un bus directo entre ambos núcleos.
* **Nivel 3: Memoria Principal (RAM):** Memoria volátil compartida de dirección única de 64 bits.
* **Nivel 4: Almacenamiento Secundario:** Bloque virtual de disco direccionado mediante E/S.


El sistema extiende los tres buses del modelo Von Neumann clásico para coordinar el acceso concurrente entre ambos núcleos:

* **Bus de Datos (64 bits):** Canal bidireccional por donde transitan operandos, resultados e instrucciones entre la memoria principal, las cachés, la CPU y la Unidad de E/S.
* **Bus de Direcciones (64 bits):** Unidireccional desde los núcleos o la unidad DMA hacia la memoria, permitiendo direccionar $2^{64}$ bytes.
* **Bus de Control:** Transporta señales de reloj, lectura/escritura (`READ`/`WRITE`), interrupciones (`IRQ0`-`IRQ7`), señales de arbitraje multinúcleo (`BUS_LOCK`, `BUS_GRANT`) y señales de sincronización entre núcleos.
* **Unidad de Entrada/Salida e Interfaz de Red (NIC):** La unidad E/S incluye una interfaz de red Ethernet emulada (NIC) mapeada en memoria. Posee registros E/S de 64 bits para enviar y recibir paquetes (*Network Sockets*), gestionando colas RX/TX con acceso directo a memoria (DMA).


| Formato | Longitud | Estructura del Byte / Palabra | Uso Principal |
| --- | --- | --- | --- |
| **Tipo 0 (Cero Operandos)** | 1 Byte | `[ Opcode (8-bit) ]` | Operaciones sobre la pila (`ADD`, `MUL`, `POP`, etc.) |
| **Tipo 1 (Un Operando Inmediato/Dir)** | 9 Bytes | `[ Opcode (8-bit) ]` + `[ Valor/Dirección (64-bit) ]` | Salto de control o Push explícito (`PUSH 0x0F`, `JMP addr`) |
| **Tipo 2 (Dos Direcciones)** | 17 Bytes | `[ Opcode (8-bit) ]` + `[ Dir_Origen (64-bit) ]` + `[ Dir_Destino (64-bit) ]` | Copia de bloques o memoria a memoria directos (`MEM_COPY`) |


| Módulo / Categoría | Código Mnemónico | Opcode (Hex) | Formato | Descripción Funcional |
| --- | --- | --- | --- | --- |
| **Aritmética y Lógica** | `NOP` | `0x00` | Tipo 0 | No realiza operación. |
|  | `ADD` | `0x01` | Tipo 0 | Desapila 2 valores, los suma y apila el resultado. |
|  | `SUB` | `0x02` | Tipo 0 | Desapila $A$ y $B$, apila $B - A$. |
|  | `MUL` | `0x03` | Tipo 0 | Multiplica los dos valores superiores de la pila. |
|  | `DIV` | `0x04` | Tipo 0 | Divide los dos valores superiores de la pila. |
|  | `MOD` | `0x05` | Tipo 0 | Obtiene el residuo de la división en la pila. |
|  | `AND` | `0x06` | Tipo 0 | Operación AND bit a bit entre TOS y TOS-1. |
|  | `OR` | `0x07` | Tipo 0 | Operación OR bit a bit entre TOS y TOS-1. |
|  | `XOR` | `0x08` | Tipo 0 | Operación XOR bit a bit. |
|  | `NOT` | `0x09` | Tipo 0 | Invierte los bits del elemento en el tope de la pila. |
|  | `SHL` | `0x0A` | Tipo 0 | Desplazamiento a la izquierda del valor TOS por $N$ posiciones. |
|  | `SHR` | `0x0B` | Tipo 0 | Desplazamiento a la derecha. |
| **Pila y Memoria** | `PUSH val64` | `0x10` | Tipo 1 | Empuja un valor inmediato de 64 bits a la pila. |
|  | `POP` | `0x11` | Tipo 0 | Elimina el elemento superior de la pila. |
|  | `DUP` | `0x12` | Tipo 0 | Duplica el elemento superior de la pila. |
|  | `SWAP` | `0x13` | Tipo 0 | Intercambia los dos elementos del tope de la pila. |
|  | `LOAD addr64` | `0x14` | Tipo 1 | Lee de la RAM en `addr64` y lo apila. |
|  | `STORE addr64` | `0x15` | Tipo 1 | Desapila el valor e ingresa en la RAM en `addr64`. |
|  | `LOAD_OFF` | `0x16` | Tipo 0 | Lee de RAM usando `BP + Offset` (desapilado). |
|  | `STORE_OFF` | `0x17` | Tipo 0 | Escribe en RAM usando `BP + Offset` (desapilado). |
| **Control de Flujo** | `JMP addr64` | `0x20` | Tipo 1 | Salto incondicional a la dirección especificada. |
|  | `JZ addr64` | `0x21` | Tipo 1 | Salta si la bandera `Z` (Zero) está activa. |
|  | `JNZ addr64` | `0x22` | Tipo 1 | Salta si la bandera `Z` no está activa. |
|  | `JGT addr64` | `0x23` | Tipo 1 | Salta si la comparación es mayor. |
|  | `JLT addr64` | `0x24` | Tipo 1 | Salta si la comparación es menor. |
|  | `CALL addr64` | `0x25` | Tipo 1 | Apila la dirección de retorno y salta a la subrutina. |
|  | `RET` | `0x26` | Tipo 0 | Retorna de la subrutina desapilando el `PC`. |
|  | `HALT` | `0x27` | Tipo 0 | Detiene la ejecución del núcleo actual. |
| **Concurrencia y Núcleos** | `GET_CORE` | `0x30` | Tipo 0 | Apila el ID del núcleo en ejecución (0 o 1). |
|  | `LOCK` | `0x31` | Tipo 0 | Activa el cerrojo de bus de hardware para exclusión mutua. |
|  | `UNLOCK` | `0x32` | Tipo 0 | Libera el cerrojo de bus. |
|  | `CORE_START` | `0x33` | Tipo 1 | Inicia el Núcleo 1 apuntando su `PC` a la dirección dada. |
|  | `CORE_YIELD` | `0x34` | Tipo 0 | Cede el ciclo de ejecución en el bus al otro núcleo. |
| **E/S y Red** | `IN_PORT` | `0x40` | Tipo 0 | Lee datos del puerto indicado en TOS. |
|  | `OUT_PORT` | `0x41` | Tipo 0 | Escribe el dato TOS-1 en el puerto TOS. |
|  | `NET_SEND` | `0x42` | Tipo 0 | Envía el buffer apuntado en la pila mediante el NIC. |
|  | `NET_RECV` | `0x43` | Tipo 0 | Recibe datos del socket de red hacia la pila/RAM. |
|  | `NET_STAT` | `0x44` | Tipo 0 | Obtiene el estado del controlador de red. |
| **Sistema y Caché** | `CACHE_FLUSH` | `0x50` | Tipo 0 | Sincroniza la Caché L1/L2 con la Memoria RAM. |
|  | `MEM_COPY` | `0x51` | Tipo 2 | Copia directa por bloque entre dos zonas de memoria. |
|  | `SET_FLAGS` | `0x52` | Tipo 0 | Actualiza el registro `FLAGS` desapilando el valor. |
|  | `GET_FLAGS` | `0x53` | Tipo 0 | Apila el estado actual del registro `FLAGS`. |
|  | `INT num` | `0x54` | Tipo 1 | Genera una interrupción por software. |

