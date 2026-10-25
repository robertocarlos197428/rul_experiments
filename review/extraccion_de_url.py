import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog


def extraer_urls_de_pdf():
    # Ocultar la ventana principal de tkinter
    root = tk.Tk()
    root.withdraw()

    # Abrir la ventana para seleccionar el archivo PDF
    ruta_pdf = filedialog.askopenfilename(
        title="Selecciona el archivo PDF",
        filetypes=[("Archivos PDF", "*.pdf")],
    )

    if not ruta_pdf:
        print("No se seleccionó ningún archivo.")
        return []

    urls_encontradas = []

    # Abrir el documento PDF
    doc = fitz.open(ruta_pdf)

    # Recorrer cada página del documento
    for num_pagina in range(len(doc)):
        pagina = doc[num_pagina]
        # Obtener todos los enlaces de la página
        enlaces = pagina.get_links()

        for enlace in enlaces:
            # Verificar si el enlace es una dirección URL externa
            if enlace.get("kind") == fitz.LINK_URI:
                uri = enlace.get("uri")
                if uri:
                    urls_encontradas.append(uri)

    doc.close()
    return urls_encontradas


if __name__ == "__main__":
    lista_urls = extraer_urls_de_pdf()

    print(f"\n--- Se encontraron {len(lista_urls)} enlaces ---")
    for url in lista_urls:
        print(url)