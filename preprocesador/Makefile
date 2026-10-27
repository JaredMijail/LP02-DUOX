CC      ?= cc
CFLAGS  ?= -std=gnu11 -O2 -Wall -Wextra
BIN      = pp
BUILD    = build
GEN      = $(BUILD)/lex.yy.c
OBJETOS  = src/macros.c src/main.c

all: $(BIN)

$(BUILD):
	mkdir -p $(BUILD)

$(GEN): src/pp.l src/pp.h | $(BUILD)
	flex -o $@ $<

$(BIN): $(GEN) $(OBJETOS) src/pp.h
	$(CC) $(CFLAGS) -Isrc -o $@ $(GEN) $(OBJETOS)

test: $(BIN)
	python3 pruebas/ejecutar.py

clean:
	rm -rf $(BUILD) $(BIN)

.PHONY: all test clean
