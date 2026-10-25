import os
import time
import difflib
import requests
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN Y CONSTANTES
# ==========================================
UMBRAL_SIMILITUD = 0.80
PAUSA_ENTRE_PETICIONES = 2.0  # Un poco más de pausa para evitar saturar

# Cabeceras robustas para evitar bloqueos 403 Forbidden
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def limpiar_texto(texto):
    if not texto or pd.isna(texto):
        return ""
    t = str(texto).lower().replace('\n', ' ').replace('\r', ' ')
    return " ".join(t.split())

def obtener_enlace_candidato(row):
    val_doi = str(row.get("doi", "")).strip() if pd.notna(row.get("doi")) else ""
    val_url = str(row.get("url", "")).strip() if pd.notna(row.get("url")) else ""
    
    if any(k in val_doi.lower() for k in ["http", "www.", "refhub"]):
        return val_doi
    elif any(k in val_url.lower() for k in ["http", "www.", "refhub"]):
        return val_url
    elif val_doi.lower() not in ["nan", "none", "-", "sin_doi", ""]:
        if val_doi.startswith("10."):
            return f"https://doi.org/{val_doi}"
        return val_doi
    elif val_url.lower() not in ["nan", "none", "-", ""]:
        return val_url
        
    return None

def abrir_y_verificar_enlace(url_original, titulo_original):
    if not url_original:
        return "Sin enlace disponible para reintentar"

    url_final = url_original
    if "refhub.elsevier.com" in url_final and "10." in url_final:
        partes = url_final.split("10.")
        url_final = "https://doi.org/10." + partes[1].split("?")[0]
    elif not url_final.startswith("http://") and not url_final.startswith("https://"):
        if url_final.startswith("www."):
            url_final = "http://" + url_final
        else:
            url_final = "http://" + url_final

    try:
        # Usamos una sesión para mantener cookies y evitar bloqueos de seguridad básicos
        session = requests.Session()
        response = session.get(url_final, headers=HEADERS_WEB, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            textos_encontrados = []
            
            for meta_attr in [{"name": "citation_title"}, {"name": "DC.Title"}, {"property": "og:title"}, {"name": "twitter:title"}]:
                meta = soup.find('meta', attrs=meta_attr)
                if meta and meta.get('content'):
                    textos_encontrados.append(meta.get('content').strip())

            for h in soup.find_all(['h1', 'h2']):
                txt = h.get_text().strip()
                if len(txt) > 8:
                    textos_encontrados.append(txt)

            if soup.title and soup.title.string:
                textos_encontrados.append(soup.title.string.strip())

            t_orig = limpiar_texto(titulo_original)
            for t_web in textos_encontrados:
                t_w_limpio = limpiar_texto(t_web)
                similitud = difflib.SequenceMatcher(None, t_orig, t_w_limpio).ratio()
                if similitud >= UMBRAL_SIMILITUD:
                    return f"Enlace OK (Título coincide - Similitud {int(similitud*100)}%)"

            return "Revisar: El enlace abre otra página o contenido distinto"
        else:
            return f"Enlace bloqueado o con error HTTP (Código {response.status_code})"
            
    except requests.exceptions.Timeout:
        return "Error: Timeout al intentar abrir la dirección"
    except Exception as e:
        return f"Error de conexión: {str(e)[:30]}"

def main():
    print("=== Reintento Profundo Mejorado (Anti-Bloqueo 403) ===")
    
    root = tk.Tk()
    root.withdraw()
    ruta_entrada = filedialog.askopenfilename(
        title="Selecciona tu archivo CSV actual",
        filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
    )
    
    if not ruta_entrada:
        print("No seleccionaste archivo. Saliendo.")
        return

    dir_base = os.path.dirname(ruta_entrada)
    nombre_archivo = os.path.basename(ruta_entrada)
    nombre_salida = f"REVISADO_BLINDADO_{nombre_archivo}"
    ruta_salida = os.path.join(dir_base, nombre_salida)

    print(f"Leyendo archivo: {nombre_archivo}...")
    df = pd.read_csv(ruta_entrada, sep=';', encoding='utf-8')

    if "resultado_revision_profunda" not in df.columns:
        df["resultado_revision_profunda"] = ""

    col_title = "title" if "title" in df.columns else None
    col_estado_verif = "estado_verificacion_url" if "estado_verificacion_url" in df.columns else None

    if not col_title or not col_estado_verif:
        print("[ERROR] El archivo no contiene las columnas necesarias.")
        return

    indices_a_reintentar = []
    for idx, row in df.iterrows():
        estado_v = str(row.get(col_estado_verif, "")).strip()
        if estado_v == "No se pudo leer título en la web":
            indices_a_reintentar.append(idx)

    total_reintentos = len(indices_a_reintentar)
    print(f"Se encontraron {total_reintentos} registros para procesar con el sistema blindado.")

    if total_reintentos == 0:
        print("No hay registros con ese estado.")
        return

    procesados = 0
    for idx in indices_a_reintentar:
        procesados += 1
        row = df.loc[idx]
        titulo_original = row[col_title]
        enlace_candidato = obtener_enlace_candidato(row)
        
        print(f"\n[{procesados}/{total_reintentos}] Procesando: {str(titulo_original)[:40]}...")
        
        try:
            time.sleep(PAUSA_ENTRE_PETICIONES)
            resultado = abrir_y_verificar_enlace(enlace_candidato, titulo_original)
        except Exception as ex:
            resultado = f"Excepción de ejecución: {str(ex)[:30]}"

        df.loc[idx, "resultado_revision_profunda"] = resultado
        print(f"  -> Resultado: {resultado}")

        # Guardado incremental seguro
        df.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')

    print("\n==========================================")
    print("¡PROCESO BLINDADO FINALIZADO!")
    print(f"Archivo generado en: {ruta_salida}")
    print("==========================================")

if __name__ == "__main__":
    main()