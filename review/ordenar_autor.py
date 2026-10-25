import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os

def procesar_author(texto):
    """
    Procesa el texto de author:
    - Reemplaza "and" por coma
    - Elimina "et al" (y variantes)
    - Evita comas dobles
    - Devuelve el texto limpio y el mensaje de modificaciones
    """
    if pd.isna(texto) or not str(texto).strip():
        return texto, ""

    original = str(texto)
    modificado = original
    mensajes = []

    # 1. Eliminar "et al" (case-insensitive, con o sin punto, con o sin espacios)
    # Ejemplos: "et al", "et al.", "Et Al", "et al ,"
    patron_et_al = re.compile(r'\s*et\s+al\.?\s*', flags=re.IGNORECASE)
    if patron_et_al.search(modificado):
        modificado = patron_et_al.sub(' ', modificado)
        mensajes.append("et al borrado")

    # 2. Reemplazar la palabra "and" por coma (como palabra completa)
    # Evita reemplazar "and" dentro de otras palabras
    patron_and = re.compile(r'\band\b', flags=re.IGNORECASE)
    if patron_and.search(modificado):
        modificado = patron_and.sub(',', modificado)
        mensajes.append("and borrado")

    # 3. Limpiar espacios y comas dobles / múltiples
    # Reemplazar múltiples espacios por uno solo
    modificado = re.sub(r'\s+', ' ', modificado)
    # Reemplazar comas múltiples (con o sin espacios) por una sola coma + espacio
    modificado = re.sub(r',\s*,+', ',', modificado)
    # Quitar espacios antes/después de comas de forma limpia
    modificado = re.sub(r'\s*,\s*', ', ', modificado)
    # Quitar comas al principio o al final
    modificado = modificado.strip(' ,')

    mensaje = " | ".join(mensajes) if mensajes else ""

    return modificado, mensaje


def main():
    # Ocultar la ventana principal de tkinter
    root = tk.Tk()
    root.withdraw()

    # Elegir el archivo CSV
    archivo = filedialog.askopenfilename(
        title="Selecciona el archivo CSV",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not archivo:
        messagebox.showinfo("Cancelado", "No se seleccionó ningún archivo.")
        return

    try:
        # Leer el CSV (separador punto y coma)
        df = pd.read_csv(archivo, sep=';', dtype=str)

        # Verificar que exista la columna author
        if 'author' not in df.columns:
            messagebox.showerror("Error", "El archivo no tiene la columna 'author'.")
            return

        # Aplicar el procesamiento
        resultados = df['author'].apply(procesar_author)
        df['author'] = resultados.apply(lambda x: x[0])
        df['modificada'] = resultados.apply(lambda x: x[1])

        # Guardar el resultado
        base, ext = os.path.splitext(archivo)
        archivo_salida = f"{base}_modificado{ext}"

        df.to_csv(archivo_salida, sep=';', index=False, encoding='utf-8-sig')

        messagebox.showinfo(
            "Listo",
            f"Proceso completado.\n\nArchivo guardado en:\n{archivo_salida}"
        )

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error:\n{str(e)}")


if __name__ == "__main__":
    main()