import csv
from pathlib import Path
import requests

doi = "10.1115/1.4071396"
url_api = f"https://api.crossref.org/works/{doi}"

headers = {"User-Agent": "ScriptAcademico/1.0 (mailto:usuario@ejemplo.com)"}

print(f"Obteniendo datos de la API de Crossref para el DOI: {doi}...")
response = requests.get(url_api, headers=headers)

references_data = []

if response.status_code == 200:
    data = response.json()
    items_ref = data.get("message", {}).get("reference", [])

    print(f"Referencias encontradas en la API: {len(items_ref)}")

    for idx, ref in enumerate(items_ref, start=1):
        num_ref = ref.get("key", str(idx))

        # Si el objeto tiene un DOI referenciado, se construye el enlace directo a Crossref
        ref_doi = ref.get("DOI")
        if ref_doi:
            link = f"https://doi.org/{ref_doi}"
        else:
            # Si no hay DOI directo, se extrae la cita sin estructurar o enlace alternativo
            link = ref.get(
                "unstructured", "Sin enlace directo registrado en Crossref"
            )

        references_data.append([num_ref, link])

    # Determinar la ruta de Descargas
    user_home = Path.home()
    downloads_folder = user_home / "Downloads"
    if not downloads_folder.exists():
        descargas_alt = user_home / "Descargas"
        if descargas_alt.exists():
            downloads_folder = descargas_alt

    output_csv = downloads_folder / "referencias_crossref.csv"

    # Guardar en el CSV
    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Numero_Referencia", "Link_Crossref"])
        writer.writerows(references_data)

    print(
        f"¡Proceso finalizado! Se guardaron {len(references_data)} referencias en:\n{output_csv}"
    )
else:
    print(f"Error al obtener datos de la API. Código HTTP: {response.status_code}")
    