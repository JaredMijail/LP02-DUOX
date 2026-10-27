"""
Pruebas del preprocesador DUOS.

Cada caso es un archivo `.asm` de `casos/`:

* `X.asm` con `X.out`: debe terminar con código 0 y esa salida exacta.
* `error_X.asm` con `error_X.err`: debe fallar y el diagnóstico debe contener
  el texto del `.err`.

El último caso encadena las tres herramientas: preprocesa `integracion/prog.asm`,
lo ensambla con `src/lp02_duox/ensamblador.py` y lo ejecuta en el emulador.

Uso (desde preprocesador/):
    python3 pruebas/ejecutar.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
CASOS = AQUI / "casos"
PP = RAIZ / "pp"

ARGUMENTOS = {
    "include_angulo.asm": ["-I", str(CASOS / "inc")],
    "condicionales.asm": ["-D", "ACTIVO"],
}

fallos = 0


def falla(nombre: str, detalle: str) -> None:
    global fallos
    fallos += 1
    print(f"  MAL {nombre}: {detalle}")


def revisar(archivo: str) -> None:
    args = ARGUMENTOS.get(archivo, [])
    r = subprocess.run([str(PP), *args, str(CASOS / archivo)],
                       capture_output=True, text=True)
    if archivo.startswith("error_"):
        esperado = (CASOS / archivo.replace(".asm", ".err")).read_text().strip()
        if r.returncode == 0:
            falla(archivo, "salió con código 0 y se esperaba un error")
        elif esperado not in r.stderr:
            falla(archivo, f"diagnóstico {r.stderr.strip()!r} sin {esperado!r}")
        else:
            print(f"  ok  {archivo}")
        return

    esperado = (CASOS / archivo.replace(".asm", ".out")).read_text()
    aviso = CASOS / archivo.replace(".asm", ".warn")
    if r.returncode != 0:
        falla(archivo, f"código {r.returncode}: {r.stderr.strip()}")
    elif r.stdout != esperado:
        falla(archivo, f"salida {r.stdout!r} != {esperado!r}")
    elif aviso.exists() and aviso.read_text().strip() not in r.stderr:
        falla(archivo, f"sin el aviso {aviso.read_text().strip()!r}")
    else:
        print(f"  ok  {archivo}")


def salida_a_archivo() -> None:
    """-o escribe el resultado en el archivo indicado."""
    with tempfile.TemporaryDirectory() as tmp:
        destino = pathlib.Path(tmp) / "salida.i"
        r = subprocess.run([str(PP), "-o", str(destino), str(CASOS / "basico.asm")],
                           capture_output=True, text=True)
        esperado = (CASOS / "basico.out").read_text()
        if r.returncode != 0 or not destino.exists() or destino.read_text() != esperado \
                or r.stdout:
            falla("-o", f"código {r.returncode}, stdout {r.stdout!r}")
        else:
            print("  ok  -o (salida a archivo)")


def compatibilidad() -> None:
    """El fuente que ya ensambla el proyecto debe ensamblar igual tras pasar por pp."""
    asm = RAIZ.parent / "src" / "lp02_duox"
    fuente = asm / "asm" / "heron.asm"
    if not (asm / "ensamblador.py").exists() or not fuente.exists():
        return

    sys.path.insert(0, str(asm))
    from ensamblador import ensamblar_archivo          # noqa: E402

    with tempfile.TemporaryDirectory() as tmp:
        salida = pathlib.Path(tmp) / "heron.asm"
        r = subprocess.run([str(PP), str(fuente), "-o", str(salida)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            falla("compatibilidad", f"pp falló: {r.stderr.strip()}")
            return
        try:
            directo, _, _ = ensamblar_archivo(str(fuente))
            filtrado, _, _ = ensamblar_archivo(str(salida))
        except Exception as e:                         # noqa: BLE001
            falla("compatibilidad", f"{type(e).__name__}: {e}")
            return
    if bytes(directo) != bytes(filtrado):
        falla("compatibilidad", "el código ensamblado cambió al preprocesar")
    else:
        print(f"  ok  compatibilidad (heron.asm: {len(filtrado)} bytes idénticos)")


def integracion() -> None:
    """preprocesador -> ensamblador -> emulador."""
    entrada = CASOS / "integracion" / "prog.asm"
    r = subprocess.run([str(PP), str(entrada)], capture_output=True, text=True)
    if r.returncode != 0:
        falla("integracion", f"el preprocesador falló: {r.stderr.strip()}")
        return

    sys.path.insert(0, str(RAIZ.parent / "src" / "lp02_duox"))
    from ensamblador import ensamblar_archivo          # noqa: E402
    from ejecutar import correr, nueva_maquina         # noqa: E402

    with tempfile.TemporaryDirectory() as tmp:
        fuente = pathlib.Path(tmp) / "prog.asm"
        fuente.write_text(r.stdout)
        try:
            codigo, _, _ = ensamblar_archivo(str(fuente))
            emu = nueva_maquina(bytes(codigo))
            correr(emu, max_pasos=20000)
        except Exception as e:                         # noqa: BLE001
            falla("integracion", f"{type(e).__name__}: {e}")
            return
    if emu.salida != "ABC\n":
        falla("integracion", f"salida de la máquina {emu.salida!r} != 'ABC\\n'")
    else:
        print("  ok  integracion (preprocesador -> ensamblador -> emulador)")


def main() -> None:
    if not PP.exists():
        subprocess.run(["make", "-s"], cwd=RAIZ, check=True)

    print("Casos:")
    for ruta in sorted(CASOS.glob("*.asm")):
        revisar(ruta.name)
    salida_a_archivo()
    integracion()
    compatibilidad()

    print(f"\n{'FALLOS: %d' % fallos if fallos else 'OK: preprocesador sin fallos'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
