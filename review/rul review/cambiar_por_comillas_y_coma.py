import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox

# Ocultar la ventana principal de Tkinter
root = tk.Tk()
root.withdraw()

# Abrir el explorador de archivos para seleccionar el CSV o Excel
file_path = filedialog.askopenfilename(
    title="Selecciona tu archivo de datos",
    filetypes=[
        ("Archivos CSV o Excel", "*.csv *.xlsx *.xls"),
        ("Todos los archivos", "*.*"),
    ],
)

if file_path:
  try:
    # Detectar si es Excel o CSV y cargarlo adecuadamente
    if file_path.endswith(".xlsx") or file_path.endswith(".xls"):
      df = pd.read_excel(file_path)
    else:
      # Intenta leer con separador punto y coma o coma automáticamente
      try:
        df = pd.read_csv(file_path, sep=";", encoding="utf-8")
      except Exception:
        df = pd.read_csv(file_path, sep=",", encoding="utf-8")

    # Definir la ruta de salida para el archivo procesado
    output_path = file_path.rsplit(".", 1)[0] + "_quoted.csv"

    # Guardar asegurando que todo vaya entre comillas (QUOTE_ALL = 1)
    df.to_csv(output_path, sep=",", encoding="utf-8", index=False, quoting=1)

    messagebox.showinfo(
        "¡Éxito!",
        f"Archivo procesado correctamente.\n\nGuardado en:\n{output_path}",
    )

  except Exception as e:
    messagebox.showerror(
        "Error", f"Ocurrió un error al procesar el archivo:\n{str(e)}"
    )
else:
  print("No se seleccionó ningún archivo.")