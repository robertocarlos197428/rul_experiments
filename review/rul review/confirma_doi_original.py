import os
import time
import requests
import pandas as pd
import tkinter as tk
from tkinter import filedialog

# ==========================================
# CONFIGURACIÓN Y CONSTANTES
# ==========================================
EMAIL_POLITE = "tu_correo@ejemplo.com"  # Reemplaza con tu email real para Crossref
PAUSA_ENTRE_PETICIONES = 0.4

HEADERS_CROSSREF = {
    "User-Agent": f"ValidadorMasterTesisSegundaPasada/1.0 (mailto:{EMAIL_POLITE})"
}

def verificar_doi_directo(doi):
    """Consulta directamente a Crossref si un DOI específico existe y es válido."""
    if not doi or str(doi).strip() in ["-", "SIN_DOI", "nan", "None", ""]:
        return False, ""
    
    doi_limpio = str(doi).strip()
    for prefix in ["https://doi.org/", "http://doi.org/", "doi:"]:
        if doi_limpio.lower().startswith(prefix):
            doi_limpio = doi_limpio[len(prefix):]
            
    try:
        url = f"https://api.crossref.org/works/{doi_limpio}"
        response = requests.get(url, headers=HEADERS_CROSSREF, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {})
            titulo_oficial = message.get("title", [""])
            titulo_encontrado = titulo_oficial[0] if titulo_oficial else ""
            return True, doi_limpio
    except Exception as e:
        print(f"  [Aviso] Error al verificar DOI {doi_limpio}: {e}")
        
    return False, doi_limpio

def extraer_doi_de_url(url):
    """Intenta extraer un DOI válido si viene embebido en una URL."""
    if not url or pd.isna(url):
        return None
    url_str = str(url)
    if "10." in url_str:
        partes = url_str.split("10.")
        if len(partes) > 1:
            candidato = "10." + partes[1].split("?")[0].split("&")[0].split("#")[0]
            if candidato.endswith("/"):
                candidato = candidato[:-1]
            return candidato
    return None

# ==========================================
# SCRIPT PRINCIPAL
# ==========================================

def main():
    print("=== Verificador de Casos Pendientes (con nueva columna de auditoría) ===")
    
    root = tk.Tk()
    root.withdraw()
    print("Por favor, selecciona tu archivo CSV ya validado (el que empieza con 'VALIDADO_')...")
    ruta_entrada = filedialog.askopenfilename(
        title="Selecciona el archivo VALIDADO_",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
    )
    
    if not ruta_entrada:
        print("No seleccionaste ningún archivo. Saliendo del programa.")
        return

    dir_base = os.path.dirname(ruta_entrada)
    nombre_archivo = os.path.basename(ruta_entrada)
    nombre_salida = f"REVISADO_{nombre_archivo}"
    ruta_salida = os.path.join(dir_base, nombre_salida)

    print(f"Leyendo archivo: {nombre_archivo}...")
    df = pd.read_csv(ruta_entrada, sep=';', encoding='utf-8')

    col_doi_orig = "doi" if "doi" in df.columns else None
    col_url = "url" if "url" in df.columns else None
    col_estado = "estado_doi" if "estado_doi" in df.columns else None
    col_doi_web = "doi_web" if "doi_web" in df.columns else None

    if not col_estado or not col_doi_web:
        print("[ERROR] El archivo seleccionado no tiene las columnas de control requeridas.")
        return

    # Asegurar que exista la nueva columna exclusiva de auditoría de esta segunda pasada
    if "estado_revision_manual" not in df.columns:
        df["estado_revision_manual"] = ""

    pendientes_indices = []
    for idx, row in df.iterrows():
        estado = str(row.get(col_estado, ""))
        if estado == "DOI no encontrado":
            val_doi = str(row.get(col_doi_orig, "")).strip()
            val_url = str(row.get(col_url, "")).strip() if col_url else ""
            
            tiene_doi_o_url = (val_doi not in ["", "nan", "None", "-", "SIN_DOI"]) or \
                              (val_url not in ["", "nan", "None", "-"])
            if tiene_doi_o_url:
                pendientes_indices.append(idx)

    total_pendientes = len(pendientes_indices)
    print(f"Se encontraron {total_pendientes} registros pendientes para reevaluar y auditar.")

    if total_pendientes == 0:
        print("No hay registros pendientes para procesar.")
        return

    procesados = 0
    for idx in pendientes_indices:
        procesados += 1
        row = df.loc[idx]
        titulo_actual = row.get("title", "Sin título")
        print(f"\n[{procesados}/{total_pendientes}] Revisando: {str(titulo_actual)[:50]}...")

        val_doi = str(row.get(col_doi_orig, "")).strip()
        val_url = str(row.get(col_url, "")).strip() if col_url else ""

        doi_a_probar = None
        origen_intento = "doi"

        # 1. Intentar con el DOI original
        if val_doi not in ["", "nan", "None", "-", "SIN_DOI"]:
            doi_a_probar = val_doi
            origen_intento = "doi"

        # 2. Si no hay DOI válido, intentar extraer de la URL
        if not doi_a_probar and val_url not in ["", "nan", "None", "-"]:
            doi_a_probar = extraer_doi_de_url(val_url)
            origen_intento = "url"

        if doi_a_probar:
            time.sleep(PAUSA_ENTRE_PETICIONES)
            valido, doi_limpio = verificar_doi_directo(doi_a_probar)
            
            if valido:
                df.loc[idx, "doi_web"] = doi_limpio
                df.loc[idx, "fuente_hallazgo"] = "Verificación Directa"
                
                if origen_intento == "doi":
                    df.loc[idx, "estado_revision_manual"] = "DOI propio validado"
                    print(f"  -> [ÉXITO] Tu DOI original sirvió y es válido: {doi_limpio}")
                else:
                    df.loc[idx, "estado_revision_manual"] = "DOI extraído de URL"
                    print(f"  -> [ÉXITO] Se rescató el DOI desde tu URL: {doi_limpio}")

                # Actualizar también el estado general si ya se encontró
                if val_doi.lower() in doi_limpio.lower() or doi_limpio.lower() in val_doi.lower():
                    df.loc[idx, "estado_doi"] = "DOI coincide"
                else:
                    df.loc[idx, "estado_doi"] = "DOI verificado"
            else:
                df.loc[idx, "estado_revision_manual"] = "DOI/URL propio inválido"
                print(f"  -> El valor aportado no respondió en Crossref: {doi_a_probar}")
        else:
            df.loc[idx, "estado_revision_manual"] = "Sin formato DOI útil"
            print("  -> No se pudo aislar un DOI válido.")

        # Guardado incremental de seguridad
        df.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')

    print("\n==========================================")
    print("¡PROCESO Y AUDITORÍA COMPLETADOS!")
    print(f"Se ha generado el archivo final con la nueva columna en: {ruta_salida}")
    print("==========================================")

if __name__ == "__main__":
    main()