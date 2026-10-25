import tkinter as tk
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox


def leer_texto(ruta):
    datos = Path(ruta).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(enc)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


def arreglar_mojibake(linea):
    # "Ã³" -> "ó", "Ã±" -> "ñ", etc.
    try:
        return linea.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return linea


def quitar_tildes(texto):
    # Quita tildes y diéresis, pero conserva la ñ
    nfd = unicodedata.normalize("NFD", texto)
    salida = []
    for ch in nfd:
        if unicodedata.combining(ch):
            if ch == "\u0303" and salida and salida[-1] in "nN":
                salida.append(ch)
            continue
        salida.append(ch)
    return unicodedata.normalize("NFC", "".join(salida))


def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    ruta = filedialog.askopenfilename(
        parent=root,
        title="Elige el archivo CSV",
        initialdir=str(Path.home() / "Downloads"),
        filetypes=[("Todos los archivos", "*.*"), ("CSV", "*.csv")],
    )
    if not ruta:
        return

    texto = leer_texto(ruta)
    lineas = texto.splitlines(keepends=True)
    limpias = [quitar_tildes(arreglar_mojibake(l)) for l in lineas]
    resultado = "".join(limpias)

    restantes = resultado.count("\ufffd")

    salida = Path(ruta).with_name(Path(ruta).stem + "_sin_tildes.csv")
    salida.write_text(resultado, encoding="utf-8-sig", newline="")

    msg = f"Archivo guardado en:\n{salida}"
    if restantes:
        msg += f"\n\nQuedaron {restantes} símbolos ' ' que no se pueden recuperar."
    messagebox.showinfo("Listo", msg)


if __name__ == "__main__":
    main()
