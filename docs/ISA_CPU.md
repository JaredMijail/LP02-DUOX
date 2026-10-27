# ISA de la máquina DUOS

Repertorio que ejecuta el emulador (`instrucciones.py`, `emuladorDuos.py`). Cada
opcode aparece una sola vez y esta tabla es la referencia del ensamblador
(`ensamblador.ISA`) y de las pruebas (`pruebas/prueba_isa.py`).

## Registros

* `PC` (64 bits): apunta a la siguiente instrucción.
* `SP` (64 bits): tope de la pila de memoria, crece hacia direcciones menores.
* `BP` (64 bits): base del marco de pila; la usan `LOAD_OFF` / `STORE_OFF`.
* `TOS` / `NOS` (64 bits): registros de trabajo (top of stack / next on stack).
* `PSW` (64 bits): banderas `C` (acarreo), `Z` (cero), `N` (negativo),
  `V` (desbordamiento), `I` (interrupciones habilitadas), `LOCK` (bus bloqueado)
  y `CORE_ID` (0 o 1, solo lectura).

Cada núcleo tiene su propio juego de registros y de `PSW`; la RAM, los puertos y
el NIC son compartidos. `MAR`/`MBR` y las cachés L1/L2 no están modelados.

## Formato de instrucción

| Formato | Longitud | Estructura |
| --- | --- | --- |
| **Tipo 0** | 1 byte | `[ Opcode ]` |
| **Tipo 1** | 9 bytes | `[ Opcode ]` + `[ Operando 64-bit ]` (inmediato, dirección o destino) |
| **Tipo 2** | 17 bytes | `[ Opcode ]` + `[ Origen 64-bit ]` + `[ Destino 64-bit ]` |

Los operandos son palabras de 64 bits en big-endian. Los saltos usan la
dirección absoluta.

## Banderas

* `Z` y `N`: se actualizan en toda operación aritmética o lógica.
* `C` y `V`: solo en `ADD` y `SUB` (`C` = acarreo o préstamo, `V` = desbordamiento
  con signo); el resto de operaciones las pone a 0.
* `I`: la cambian `EI`, `DI` e `IRET`; `INT` la guarda en la pila antes de saltar.
* `LOCK`: la cambian `LOCK`, `UNLOCK` y `SET_FLAGS`.
* `GET_FLAGS` / `SET_FLAGS` empaquetan así: bit 0 `C`, 1 `Z`, 2 `N`, 3 `V`,
  4 `LOCK`, bits 8-15 `CORE_ID` (solo lectura).

## Instrucciones

| Categoría | Mnemónico | Opcode | Formato | Descripción funcional |
| --- | --- | --- | --- | --- |
| **Aritmética y lógica** | `NOP` | `0x00` | Tipo 0 | No realiza operación. |
|  | `ADD` | `0x01` | Tipo 0 | `TOS <- TOS + NOS`; actualiza `Z N C V`. |
|  | `SUB` | `0x02` | Tipo 0 | `TOS <- NOS - TOS`; actualiza `Z N C V`. |
|  | `MUL` | `0x03` | Tipo 0 | `TOS <- TOS * NOS`; actualiza `Z N`. |
|  | `DIV` | `0x04` | Tipo 0 | `TOS <- TOS // NOS` (cociente entero); actualiza `Z N`. Detiene el núcleo si `NOS = 0`. |
|  | `MOD` | `0x05` | Tipo 0 | `TOS <- TOS % NOS`; actualiza `Z N`. Detiene el núcleo si `NOS = 0`. |
|  | `AND` | `0x06` | Tipo 0 | `TOS <- TOS & NOS`; actualiza `Z N`. |
|  | `OR` | `0x07` | Tipo 0 | `TOS <- TOS \| NOS`; actualiza `Z N`. |
|  | `XOR` | `0x08` | Tipo 0 | `TOS <- TOS ^ NOS`; actualiza `Z N`. |
|  | `NOT` | `0x09` | Tipo 0 | `TOS <- ~TOS` (complemento a 64 bits); actualiza `Z N`. |
|  | `SHL` | `0x0A` | Tipo 0 | `TOS <- (NOS << TOS) mod 2^64`; actualiza `Z N`. |
|  | `SHR` | `0x0B` | Tipo 0 | `TOS <- NOS >> TOS` (lógico, 64 bits); actualiza `Z N`. |
| **Pila y memoria** | `PUSH` | `0x10` | Tipo 1 | `NOS <- TOS`; `TOS <- inmediato`. |
|  | `POP` | `0x11` | Tipo 0 | `TOS <- NOS`; `NOS <- 0`. |
|  | `DUP` | `0x12` | Tipo 0 | `NOS <- TOS` (duplica el tope). |
|  | `SWAP` | `0x13` | Tipo 0 | Intercambia `TOS` y `NOS`. |
|  | `LOAD` | `0x14` | Tipo 1 | `NOS <- TOS`; `TOS <- MEM[dir]`. |
|  | `STORE` | `0x15` | Tipo 1 | `MEM[dir] <- TOS`. |
|  | `LOAD_OFF` | `0x16` | Tipo 0 | Desapila el desplazamiento y empuja `MEM[BP + desplazamiento]`. |
|  | `STORE_OFF` | `0x17` | Tipo 0 | Desapila el desplazamiento y el valor; `MEM[BP + desplazamiento] <- valor`. |
|  | `LOAD_IMM` | `0x18` | Tipo 1 | `TOS <- inmediato` (alias `LDI`); actualiza `Z N`. |
| **Control de flujo** | `JMP` | `0x20` | Tipo 1 | `PC <- dir`. |
|  | `JZ` | `0x21` | Tipo 1 | Salta si `Z = 1`. |
|  | `JNZ` | `0x22` | Tipo 1 | Salta si `Z = 0`. |
|  | `JGT` | `0x23` | Tipo 1 | Salta si `Z = 0` y `N = V` (mayor, con signo). |
|  | `JLT` | `0x24` | Tipo 1 | Salta si `N != V` (menor, con signo). |
|  | `CALL` | `0x25` | Tipo 1 | Apila `PC + 9` en la pila de memoria y salta a `dir`. |
|  | `RET` | `0x26` | Tipo 0 | `PC <-` desapila de la pila de memoria. |
|  | `HALT` | `0x27` | Tipo 0 | Detiene el núcleo actual. |
| **Concurrencia** | `GET_CORE` | `0x30` | Tipo 0 | Empuja `CORE_ID`. |
|  | `LOCK` | `0x31` | Tipo 0 | `LOCK <- 1` (cerrojo de bus). |
|  | `UNLOCK` | `0x32` | Tipo 0 | `LOCK <- 0`. |
|  | `CORE_START` | `0x33` | Tipo 1 | Arranca el núcleo 1 con `PC <- dir`; copia `SP = BP = 0xF800`. |
|  | `CORE_YIELD` | `0x34` | Tipo 0 | Fuerza el cambio de turno. |
| **E/S y red** | `IN_PORT` | `0x40` | Tipo 0 | `puerto <- TOS` (desapila); empuja el valor del puerto (0 si no se escribió). |
|  | `OUT_PORT` | `0x41` | Tipo 0 | `puerto <- TOS`, `valor <- NOS` (desapila ambos); `puertos[puerto] <- valor`. |
|  | `NET_SEND` | `0x42` | Tipo 0 | `largo <- TOS`, `dir <- NOS` (desapila ambos); envía `MEM[dir .. dir+largo)` al NIC. |
|  | `NET_RECV` | `0x43` | Tipo 0 | `largo <- TOS`, `dir <- NOS`; copia hasta `largo` bytes del paquete recibido en `MEM[dir]` y empuja los bytes copiados. |
|  | `NET_STAT` | `0x44` | Tipo 0 | Empuja los bytes pendientes en la cola de recepción. |
|  | `OUT` | `0x45` | Tipo 0 | Escribe `chr(TOS & 0xFF)` en la consola. |
| **Sistema** | `CACHE_FLUSH` | `0x50` | Tipo 0 | Sin efecto: no hay caché modelada. |
|  | `MEM_COPY` | `0x51` | Tipo 2 | `n <- TOS` (desapila); copia `n` palabras desde origen a destino (solapamiento seguro). |
|  | `SET_FLAGS` | `0x52` | Tipo 0 | Desapila y actualiza `C Z N V LOCK`. |
|  | `GET_FLAGS` | `0x53` | Tipo 0 | Empuja el estado de las banderas. |
|  | `INT` | `0x54` | Tipo 0 | `vector <- TOS`; apila `PC + 1` y `PSW.I` en la pila de memoria; `PC <- MEM[vector * 8]`. |
|  | `IRET` | `0x55` | Tipo 0 | `PSW.I <-` desapila; `PC <-` desapila. |
|  | `EI` | `0x56` | Tipo 0 | `I <- 1`. |
|  | `DI` | `0x57` | Tipo 0 | `I <- 0`. |

## Pila

`TOS`/`NOS` forman una pila de dos registros: `PUSH` corre `TOS` a `NOS` y las
operaciones dejan el resultado en `TOS`. La pila de memoria (`SP`), separada,
guarda direcciones de retorno y el estado de las interrupciones; `CALL`, `RET`,
`INT`, `IRET` y las interrupciones de teclado son sus únicos usuarios.

## Mapa de memoria

| Zona | Rango | Uso |
| --- | --- | --- |
| Vectores | `0x0000 - 0x0078` | 0 teclado, 1 print; 2-7 librería `mate.inc`; 8-15 libres |
| ISR | `0x0100` | `IRET` del teclado |
| Llamada al sistema | `0x0200` | `LOAD` + `OUT` + `IRET` de impresión |
| Programa | `0x1000 - 0xEFFF` | código y datos del usuario |
| Pilas | `0xF000 - 0xFFFF` | núcleo 0 desde `0xFFFF`, núcleo 1 desde `0xF800` (2 KB cada una, sin protección) |

La RAM emulada es de 64 KB (direcciones de 16 bits), aunque el bus de direcciones
del diseño sea de 64 bits.

## Concurrencia

Los dos núcleos se turnan un ciclo por vez (turno rotativo). `CORE_START` arranca
el núcleo 1 y `HALT` detiene solo el núcleo que la ejecuta; la máquina se detiene
cuando se han detenido los dos. `LOCK`/`UNLOCK` marcan el cerrojo de bus en `PSW`
(no hay coherencia de caché que proteger) y `CORE_YIELD` adelanta el cambio de
turno.

## E/S, red e interrupciones

Los puertos son un diccionario de 64 bits: leer un puerto no escrito devuelve 0.
El NIC es loopback: lo que se envía con `NET_SEND` queda en la cola de recepción
para `NET_RECV`, y `NET_STAT` informa los bytes pendientes. La interrupción de
teclado se entrega al núcleo en ejecución cuando `PSW.I = 1`, usando el vector 0.
