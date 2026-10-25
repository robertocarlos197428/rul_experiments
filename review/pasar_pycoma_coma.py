import csv
import os
import tkinter as tk
from tkinter import filedialog


def corregir_csv():
    # Crear ventana para seleccionar archivo
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal de Tkinter

    # Abrir el selector de archivos
    ruta_archivo = filedialog.askopenfilename(
        title="Selecciona el archivo CSV a corregir",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
    )

    if not ruta_archivo:
        print("No se seleccionó ningún archivo.")
        return

    # Definir la ruta de salida agregando '_C' al nombre
    directorio, nombre_completo = os.path.split(ruta_archivo)
    nombre_base, extension = os.path.splitext(nombre_completo)
    ruta_salida = os.path.join(directorio, f"{nombre_base}_C{extension}")

    # Leer el archivo delimitado por ';' y escribirlo delimitado por ','
    with open(
        ruta_archivo, mode="r", encoding="utf-8-sig", newline=""
    ) as archivo_entrada:
        lector = csv.reader(archivo_entrada, delimiter=";")
        filas = list(lector)

    with open(
        ruta_salida, mode="w", encoding="utf-8", newline=""
    ) as archivo_salida:
        escritor = csv.writer(
            archivo_salida, delimiter=",", quoting=csv.QUOTE_MINIMAL
        )
        escritor.writerows(filas)

    print(f"Archivo corregido guardado exitosamente en:\n{ruta_salida}")


if __name__ == "__main__":
    corregir_csv()