# ============================================================
# Makefile - Analizador Léxico del Compilador DUOXC
# Arquitectura destino: DUOX / DUOS (pila 64 bits)
# Taller #01 - Grupo F - LP02-DUOX
# ============================================================
# Uso:
#   make          -> compila duoxc_lex
#   make test     -> compila y ejecuta con test_programa.dx
#   make run      -> ejecuta en modo interactivo (stdin)
#   make clean    -> elimina archivos generados
#   make help     -> muestra esta ayuda
# ============================================================

CC      = gcc
FLEX    = flex
CFLAGS  = -Wall -Wextra -std=c99 -D_POSIX_C_SOURCE=200809L -O2
TARGET  = duoxc_lex
SRC_L   = duoxc.l
GEN_C   = lex.yy.c
TEST    = test_programa.dx

.PHONY: all test run clean help

# Objetivo por defecto: compilar el analizador léxico
all: $(TARGET)
	@echo "[OK] Compilado: ./$(TARGET)"

# 1) FLEX genera el archivo C
$(GEN_C): $(SRC_L)
	@echo "[FLEX] Generando $(GEN_C) desde $(SRC_L)..."
	$(FLEX) $(SRC_L)

# 2) GCC compila el C generado
$(TARGET): $(GEN_C)
	@echo "[GCC]  Compilando $(TARGET)..."
	$(CC) $(CFLAGS) $(GEN_C) -lfl -o $(TARGET)

# Ejecutar el test automático
test: $(TARGET)
	@echo "============================================================"
	@echo " EJECUTANDO TEST: $(TEST)"
	@echo "============================================================"
	./$(TARGET) $(TEST)

# Modo interactivo (stdin)
run: $(TARGET)
	@echo "[INFO] Modo interactivo - escribe DUOXC, Ctrl+D para terminar"
	./$(TARGET)

# Limpieza de archivos generados
clean:
	@echo "[CLEAN] Eliminando archivos generados..."
	rm -f $(TARGET) $(GEN_C)
	@echo "[OK] Limpieza completada."

# Ayuda
help:
	@echo "============================================================"
	@echo " Analizador Léxico DUOXC - Taller #01 LP02-DUOX Grupo F"
	@echo "============================================================"
	@echo " Objetivos disponibles:"
	@echo "   make        -> compila el analizador léxico"
	@echo "   make test   -> ejecuta el análisis sobre $(TEST)"
	@echo "   make run    -> modo interactivo desde stdin"
	@echo "   make clean  -> elimina binarios y código C generado"
	@echo "   make help   -> muestra este mensaje"
	@echo ""
	@echo " Requisitos: flex (>= 2.6), gcc (>= 9)"
	@echo "============================================================"
