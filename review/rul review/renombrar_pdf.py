"""
Renombra archivos con formato:
    NNNN_Autor1_Autor2..._AAAA.ext
a:
    NNNN_AAAA_Autor1_Autor2....ext

Donde NNNN es un número de 4 dígitos al inicio, y AAAA es un año
(1900-2099) al final, antes de la extensión.

Renombra los archivos DIRECTAMENTE en la carpeta que elijas (sobrescribe
los nombres originales, no crea copias).
"""

import re
from pathlib import Path
from tkinter import Tk, filedialog

PATRON_ANIO_SEGUNDO = re.compile(r"^(\d{4})_(19\d{2}|20\d{2})_(.+)$")
PATRON_ANIO_AL_FINAL = re.compile(r"^(\d{4})_(.+)_(19\d{2}|20\d{2})$")


def elegir_carpeta() -> str:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta = filedialog.askdirectory(title="Selecciona la carpeta con los PDFs")
    root.destroy()
    if not ruta:
        raise SystemExit("No se seleccionó ninguna carpeta.")
    return ruta


def main():
    carpeta = Path(elegir_carpeta())

    renombrados = 0
    omitidos = 0

    for archivo in sorted(carpeta.iterdir()):
        if not archivo.is_file():
            continue

        nombre_sin_ext = archivo.stem
        extension = archivo.suffix

        coincidencia_a = PATRON_ANIO_SEGUNDO.match(nombre_sin_ext)
        coincidencia_b = PATRON_ANIO_AL_FINAL.match(nombre_sin_ext)

        if coincidencia_a:
            numero, anio, autores = coincidencia_a.groups()
        elif coincidencia_b:
            numero, autores, anio = coincidencia_b.groups()
        else:
            print(f"[omitido, no calza el patrón] {archivo.name}")
            omitidos += 1
            continue

        nuevo_nombre = f"{anio}_{numero}_{autores}{extension}"
        nuevo_path = archivo.with_name(nuevo_nombre)

        if nuevo_path.exists() and nuevo_path != archivo:
            print(f"[omitido, ya existe destino] {archivo.name} -> {nuevo_nombre}")
            omitidos += 1
            continue

        archivo.rename(nuevo_path)
        print(f"{archivo.name}  ->  {nuevo_nombre}")
        renombrados += 1

    print(f"\nRenombrados: {renombrados}")
    print(f"Omitidos: {omitidos}")


if __name__ == "__main__":
    main()
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

import pandas as pd


def detectar_encoding(ruta):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, encoding=enc) as f:
                f.read()
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detectar_separador(ruta, enc):
    with open(ruta, encoding=enc) as f:
        cabecera = f.readline()
    return ";" if cabecera.count(";") > cabecera.count(",") else ","


def rellenar(serie):
    # "4. Texto" -> "04. Texto" | "10. Texto" queda igual
    return serie.str.replace(
        r"^(\s*)(\d+)\.",
        lambda m: f"{m.group(1)}{int(m.group(2)):02d}.",
        regex=True,
    )


def main():
    root = tk.Tk()
    root.withdraw()

    ruta = filedialog.askopenfilename(
        title="Elige el archivo CSV",
        filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
    )
    if not ruta:
        return

    enc = detectar_encoding(ruta)
    sep = detectar_separador(ruta, enc)

    df = pd.read_csv(ruta, sep=sep, dtype=str, encoding=enc, keep_default_na=False)

    # Columnas A y B (las dos primeras)
    for col in df.columns[:2]:
        df[col] = rellenar(df[col])

    salida = Path(ruta).with_name(Path(ruta).stem + "_corregido.csv")
    df.to_csv(salida, sep=sep, index=False, encoding=enc)

    messagebox.showinfo("Listo", f"Archivo guardado en:\n{salida}")


if __name__ == "__main__":
    main()