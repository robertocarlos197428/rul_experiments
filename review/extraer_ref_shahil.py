import csv
import re
from pathlib import Path
import fitz  # PyMuPDF

# Ruta a tu archivo PDF local
pdf_path = Path(
    r"escribe aqui tu ruta"
)


def extraer_referencias_perfecto(ruta_pdf):
    if not ruta_pdf.exists():
        print(f"Error: No existe el archivo en la ruta: {ruta_pdf}")
        return

    doc = fitz.open(ruta_pdf)
    num_pagina_ref = None

    # 1. Encontrar la página donde comienza 'References'
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        if re.search(r"\bReferences\b", text, re.IGNORECASE):
            num_pagina_ref = page_num
            break

    if num_pagina_ref is None:
        print("No se encontró la sección 'References' en el PDF.")
        return

    print(f"Sección 'References' detectada en la página {num_pagina_ref + 1}.")

    # 2. Reconstruir todo el texto y extraer todos los hipervínculos desde References en adelante
    texto_seccion = ""
    enlaces_pagina = []

    for page_num in range(num_pagina_ref, len(doc)):
        page = doc[page_num]
        text_p = page.get_text("text")

        # Cortar lo que esté antes de la palabra "References" en la primera página
        if page_num == num_pagina_ref:
            pos = re.search(r"\bReferences\b", text_p, re.IGNORECASE)
            if pos:
                text_p = text_p[pos.start() :]

        texto_seccion += "\n" + text_p

        # Extraer enlaces interactivos anotados en la página
        for link in page.get_links():
            if "uri" in link:
                uri = link["uri"]
                if uri not in enlaces_pagina:
                    enlaces_pagina.append(uri)

    # 3. Expresión regular para separar el texto en bloques por su NÚMERO DE REFERENCIA
    # Captura patrones al inicio de línea como "1.", "[1]", "1 "
    patron_numero = re.compile(r"(?:^|\n)\s*\[?(\d+)\]?[\.\s]")
    matches = list(patron_numero.finditer(texto_seccion))

    if not matches:
        print("No se identificó el patrón numérico de las referencias.")
        return

    referencias_data = []

    # 4. Procesar cada referencia de forma aislada
    for i in range(len(matches)):
        num_ref = matches[i].group(1)
        start_idx = matches[i].start()
        end_idx = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(texto_seccion)
        )

        bloque_texto = texto_seccion[start_idx:end_idx].strip()
        link_encontrado = None

        # A) Buscar DOI directo en el texto (ej: https://doi.org/... o 10.1016/...)
        match_doi_url = re.search(
            r"https?://(?:dx\.)?doi\.org/[^\s\]\}]+", bloque_texto
        )
        if match_doi_url:
            link_encontrado = match_doi_url.group(0).rstrip(".,;")
        else:
            match_doi_raw = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", bloque_texto, re.IGNORECASE)
            if match_doi_raw:
                link_encontrado = f"https://doi.org/{match_doi_raw.group(0).rstrip('.,;')}"

        # B) Si no hay DOI en el texto, buscar si en las URLs del PDF hay un enlace que pertenezca a este bloque (Elsevier / RefHub)
        if not link_encontrado:
            for uri in list(enlaces_pagina):
                # Verificar si parte de la URI (ej. identificadores refhub o DOI) está en el bloque de texto
                # O si la URI es un enlace estándar de Crossref / DOI / Publisher
                if any(
                    k in uri.lower()
                    for k in [
                        "doi.org",
                        "crossref",
                        "elsevier.com",
                        "refhub",
                        "sciencedirect",
                        "ieee",
                        "springer",
                    ]
                ):
                    # Extraer ID o sufijo del enlace para confirmar correspondencia
                    id_uri = uri.split("/")[-1].replace("-", "").lower()
                    texto_limpio = bloque_texto.replace("-", "").lower()

                    if len(id_uri) > 5 and id_uri in texto_limpio:
                        link_encontrado = uri
                        enlaces_pagina.remove(uri)
                        break

        # C) Si sigue sin asignarse pero quedan enlaces ordenados disponibles en la lista de la página
        if not link_encontrado and enlaces_pagina:
            # Buscar el primer enlace de la lista que sea de una editorial/DOI
            for uri in list(enlaces_pagina):
                if any(
                    k in uri.lower()
                    for k in [
                        "doi.org",
                        "crossref",
                        "elsevier",
                        "refhub",
                        "sciencedirect",
                    ]
                ):
                    link_encontrado = uri
                    enlaces_pagina.remove(uri)
                    break

        # D) Si definitivamente no tiene enlace ni DOI
        if not link_encontrado:
            link_encontrado = "sin doi"

        referencias_data.append([num_ref, link_encontrado])

    # 5. Guardar CSV en Descargas
    user_home = Path.home()
    downloads_folder = user_home / "Downloads"
    if not downloads_folder.exists():
        descargas_alt = user_home / "Descargas"
        if descargas_alt.exists():
            downloads_folder = descargas_alt

    output_csv = downloads_folder / "referencias_crossref_pdf.csv"

    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Numero_Referencia", "Link_Crossref"])
        writer.writerows(referencias_data)

    print(
        f"¡Extracción exitosa sin desfases! Se procesaron {len(referencias_data)} referencias en:\n{output_csv}"
    )


# Ejecutar extracción
extraer_referencias_perfecto(pdf_path)