import os
import time
import difflib
import requests
import pandas as pd
import tkinter as tk
from tkinter import filedialog

# ==========================================
# CONFIGURACIÓN Y CONSTANTES
# ==========================================
EMAIL_POLITE = "ingenierordiaz@gmail.com"  # Reemplaza con tu email real para el Polite Pool de Crossref
UMBRAL_SIMILITUD = 0.90  # 90% de coincidencia mínima en títulos
PAUSA_ENTRE_PETICIONES = 0.5  # Segundos de pausa para ser amables con las APIs

HEADERS_CROSSREF = {
    "User-Agent": f"ValidadorMasterTesis/1.0 (mailto:{EMAIL_POLITE})"
}

# ==========================================
# FUNCIONES DE CONSULTA A LAS APIs
# ==========================================

def buscar_en_crossref(titulo):
    """Consulta la API de Crossref usando el título."""
    try:
        url = "https://api.crossref.org/works"
        params = {"query.bibliographic": titulo, "rows": 1}
        response = requests.get(url, params=params, headers=HEADERS_CROSSREF, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("message", {}).get("items", [])
            if items:
                item = items[0]
                doi = item.get("DOI")
                titulos_web = item.get("title", [])
                titulo_encontrado = titulos_web[0] if titulos_web else ""
                return doi, titulo_encontrado
    except Exception as e:
        print(f"  [Aviso] Error en Crossref: {e}")
    return None, None

def buscar_en_openalex(titulo):
    """Consulta la API de OpenAlex usando el título."""
    try:
        url = "https://api.openalex.org/works"
        params = {"search": titulo, "per-page": 1}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                item = results[0]
                doi_url = item.get("doi")
                doi = doi_url.replace("https://doi.org/", "") if doi_url else None
                titulo_encontrado = item.get("display_name", "")
                return doi, titulo_encontrado
    except Exception as e:
        print(f"  [Aviso] Error en OpenAlex: {e}")
    return None, None

def buscar_en_semantic_scholar(titulo):
    """Consulta la API de Semantic Scholar usando el título."""
    try:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {"query": titulo, "limit": 1, "fields": "externalIds,title"}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            data_results = data.get("data", [])
            if data_results:
                item = data_results[0]
                external_ids = item.get("externalIds", {})
                doi = external_ids.get("DOI")
                titulo_encontrado = item.get("title", "")
                return doi, titulo_encontrado
    except Exception as e:
        print(f"  [Aviso] Error en Semantic Scholar: {e}")
    return None, None

def son_titulos_similares(t1, t2):
    """Compara dos títulos usando secuencia de similitud de texto."""
    if not t1 or not t2:
        return False
    t1_limpio = str(t1).lower().strip()
    t2_limpio = str(t2).lower().strip()
    similitud = difflib.SequenceMatcher(None, t1_limpio, t2_limpio).ratio()
    return similitud >= UMBRAL_SIMILITUD

# ==========================================
# SCRIPT PRINCIPAL
# ==========================================

def main():
    print("=== Validador de DOIs para Tesis de Máster ===")
    
    # 1. Seleccionar archivo mediante ventana gráfica
    root = tk.Tk()
    root.withdraw()
    print("Por favor, selecciona tu archivo CSV original en la ventana que se abrió...")
    ruta_entrada = filedialog.askopenfilename(
        title="Selecciona el archivo CSV original",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
    )
    
    if not ruta_entrada:
        print("No seleccionaste ningún archivo. Saliendo del programa.")
        return

    # Definir nombre del archivo de salida 100% nuevo
    dir_base = os.path.dirname(ruta_entrada)
    nombre_archivo = os.path.basename(ruta_entrada)
    nombre_salida = f"VALIDADO_{nombre_archivo}"
    ruta_salida = os.path.join(dir_base, nombre_salida)

    # Cargar datos originales usando punto y coma (;) como delimitador de tu archivo
    print(f"Leyendo archivo: {nombre_archivo}...")
    df = pd.read_csv(ruta_entrada, sep=';', encoding='utf-8')

    # Identificar las columnas exactas de tu estructura
    col_titulo = "title" if "title" in df.columns else None
    col_doi_orig = "doi" if "doi" in df.columns else None

    if not col_titulo:
        print("[ERROR] No se encontró la columna 'title' en tu CSV.")
        print(f"Tus columnas detectadas son: {list(df.columns)}")
        return

    print(f"Columna de título identificada: '{col_titulo}'")
    print(f"Columna de DOI original identificada: '{col_doi_orig}'")

    # Asegurar columnas nuevas de control si no existen
    nuevas_columnas = ["doi_web", "estado_doi", "fuente_hallazgo", "titulo_web"]
    for col in nuevas_columnas:
        if col not in df.columns:
            df[col] = ""

    total_filas = len(df)
    print(f"Total de referencias a procesar: {total_filas}")

    for idx, row in df.iterrows():
        # Sistema reanudable: si ya tiene estado procesado, se salta
        if pd.notna(row.get("estado_doi")) and str(row.get("estado_doi")).strip() != "":
            continue

        titulo_actual = row[col_titulo]
        if pd.isna(titulo_actual) or str(titulo_actual).strip() == "":
            df.loc[idx, "estado_doi"] = "DOI no encontrado"
            df.loc[idx, "fuente_hallazgo"] = "Sin título"
            continue

        print(f"\n[{idx + 1}/{total_filas}] Buscando: {str(titulo_actual)[:60]}...")

        doi_encontrado = None
        titulo_web_encontrado = ""
        fuente_usada = ""

        # --- CAPA 1: Crossref ---
        time.sleep(PAUSA_ENTRE_PETICIONES)
        doi_c, tit_c = buscar_en_crossref(titulo_actual)
        if doi_c and son_titulos_similares(titulo_actual, tit_c):
            doi_encontrado, titulo_web_encontrado, fuente_usada = doi_c, tit_c, "Crossref"

        # --- CAPA 2: OpenAlex ---
        if not doi_encontrado:
            time.sleep(PAUSA_ENTRE_PETICIONES)
            doi_o, tit_o = buscar_en_openalex(titulo_actual)
            if doi_o and son_titulos_similares(titulo_actual, tit_o):
                doi_encontrado, titulo_web_encontrado, fuente_usada = doi_o, tit_o, "OpenAlex"

        # --- CAPA 3: Semantic Scholar ---
        if not doi_encontrado:
            time.sleep(PAUSA_ENTRE_PETICIONES)
            doi_s, tit_s = buscar_en_semantic_scholar(titulo_actual)
            if doi_s and son_titulos_similares(titulo_actual, tit_s):
                doi_encontrado, titulo_web_encontrado, fuente_usada = doi_s, tit_s, "Semantic Scholar"

        # Evaluar estados y comparar con DOI original
        doi_orig_val = str(row[col_doi_orig]).strip() if col_doi_orig and pd.notna(row[col_doi_orig]) else ""
        if doi_orig_val.lower() in ["nan", "none", "-", "", "sin_doi"]:
            doi_orig_val = ""

        df.loc[idx, "doi_web"] = doi_encontrado if doi_encontrado else ""
        df.loc[idx, "titulo_web"] = titulo_web_encontrado

        if doi_encontrado:
            df.loc[idx, "fuente_hallazgo"] = fuente_usada
            if doi_orig_val == "":
                df.loc[idx, "estado_doi"] = "DOI encontrado"
                print(f"  -> ¡Encontrado ({fuente_usada})!: {doi_encontrado}")
            else:
                if doi_encontrado.lower() == doi_orig_val.lower():
                    df.loc[idx, "estado_doi"] = "DOI coincide"
                    print("  -> Coincide exacto con tu DOI.")
                else:
                    df.loc[idx, "estado_doi"] = "DOI diferente"
                    print(f"  -> [DIFERENTE] Web: {doi_encontrado} | Original: {doi_orig_val}")
        else:
            df.loc[idx, "fuente_hallazgo"] = "No encontrado"
            df.loc[idx, "estado_doi"] = "DOI no encontrado"
            print("  -> No se encontró DOI en ninguna fuente.")

        # Guardado incremental fila a fila (Checkpoint seguro manteniendo separador ;)
        df.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')

    print("\n==========================================")
    print("¡PROCESO COMPLETADO CON ÉXITO!")
    print(f"Se ha generado el nuevo archivo en: {ruta_salida}")
    print("==========================================")

if __name__ == "__main__":
    main()