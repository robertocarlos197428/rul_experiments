"""
Descarga de papers en un solo script, por fila:
 1) Unpaywall (copia legal de acceso abierto vía DOI)
 2) doi        (resolviendo https://doi.org/<doi>)
 3) doi_web
 4) url
 5) Si todo lo anterior falla -> navegador real (Playwright), reutilizando
    tu sesión institucional (INACAP / ScienceDirect / IEEE, etc.)

Al iniciar se abre una ventana de Chrome UNA sola vez. Inicia sesión ahí
en tu acceso institucional antes de continuar (el script espera a que
presiones Enter). Esa sesión se reutiliza para todas las filas que
necesiten navegador durante toda la corrida, y queda guardada en la
carpeta "perfil_navegador" para la próxima vez.

Guarda una copia intacta del archivo original, y va guardando el
progreso cada cierto número de filas (por si se corta a la mitad).

Requiere:
    pip install pandas requests tqdm playwright --break-system-packages
    playwright install chromium      (una sola vez)
"""

import re
import shutil
import time
from pathlib import Path
from tkinter import Tk, filedialog

import pandas as pd
import requests
from tqdm import tqdm
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

DESCARGAS_DIR = Path(r"escribe aqui tu ruta")
PERFIL_DIR = Path("perfil_navegador")
EMAIL_UNPAYWALL = "TU_CORREO_AQUI@ejemplo.com"  # <-- cámbialo por tu correo real
TIMEOUT = 20  # segundos, para los intentos con requests
TIMEOUT_MS_NAV = 25_000  # milisegundos, para el navegador
PAUSA_ENTRE_FILAS = 1.0
GUARDAR_CADA = 20  # filas
HEADLESS = False  # deja en False para poder loguearte y ver qué pasa

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

PATRON_BOTON_PDF = re.compile(
    r"(download\s*pdf|view\s*pdf|get\s*pdf|full\s*text\s*pdf|pdf\s*download"
    r"|descargar\s*pdf|ver\s*pdf|obtener\s*pdf|article\s*pdf)",
    re.IGNORECASE,
)


# ---------- utilidades comunes ----------

def elegir_archivo_entrada() -> str:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta = filedialog.askopenfilename(
        title="Selecciona el CSV con los papers",
        filetypes=[("Archivos CSV", "*.csv")],
    )
    root.destroy()
    if not ruta:
        raise SystemExit("No se seleccionó ningún archivo.")
    return ruta


def normalizar_doi(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    v = str(valor).strip().lower()
    v = re.sub(r"^https?://(dx\.)?doi\.org/", "", v)
    return v.rstrip("/")


def nombre_archivo_seguro(texto, maximo: int = 80) -> str:
    texto = str(texto).strip()
    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = re.sub(r"\s+", "_", texto)
    return texto[:maximo] if texto else "sin_titulo"


# ---------- fase rápida (requests) ----------

def descargar_pdf_requests(url: str, destino: Path) -> bool:
    try:
        with requests.get(
            url, headers=HEADERS, timeout=TIMEOUT, stream=True, allow_redirects=True
        ) as r:
            if r.status_code != 200:
                return False
            content_type = r.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type:
                primer_chunk = next(r.iter_content(chunk_size=1024), b"")
                if not primer_chunk.startswith(b"%PDF"):
                    return False
                with open(destino, "wb") as f:
                    f.write(primer_chunk)
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            with open(destino, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except requests.RequestException:
        return False


def buscar_pdf_unpaywall(doi: str):
    try:
        resp = requests.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": EMAIL_UNPAYWALL},
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        mejor = data.get("best_oa_location") or {}
        return mejor.get("url_for_pdf") or mejor.get("url")
    except (requests.RequestException, ValueError):
        return None


def intentar_fase_rapida(fila, destino: Path):
    doi = normalizar_doi(fila.get("doi"))
    doi_web = normalizar_doi(fila.get("doi_web"))
    url_directa = fila.get("url")
    doi_para_unpaywall = doi or doi_web

    if doi_para_unpaywall:
        pdf_url = buscar_pdf_unpaywall(doi_para_unpaywall)
        if pdf_url and descargar_pdf_requests(pdf_url, destino):
            return "Si", "unpaywall"

    if doi and descargar_pdf_requests(f"https://doi.org/{doi}", destino):
        return "Si", "doi"

    if doi_web and descargar_pdf_requests(f"https://doi.org/{doi_web}", destino):
        return "Si", "doi_web"

    if pd.notna(url_directa) and str(url_directa).strip():
        if descargar_pdf_requests(str(url_directa).strip(), destino):
            return "Si", "url"

    return "No", ""


# ---------- fase navegador (Playwright) ----------

def url_objetivo(fila) -> str:
    doi = normalizar_doi(fila.get("doi"))
    doi_web = normalizar_doi(fila.get("doi_web"))
    if doi:
        return f"https://doi.org/{doi}"
    if doi_web:
        return f"https://doi.org/{doi_web}"
    url = fila.get("url")
    if pd.notna(url) and str(url).strip():
        return str(url).strip()
    return ""


def intentar_click_descarga(context, page, destino: Path) -> bool:
    candidatos = page.locator("a, button").filter(has_text=PATRON_BOTON_PDF)
    total = candidatos.count()
    if total == 0:
        return False

    for i in range(min(total, 3)):
        try:
            with page.expect_download(timeout=8000) as descarga_info:
                candidatos.nth(i).click(timeout=5000)
            descarga_info.value.save_as(str(destino))
            return True
        except PWTimeout:
            paginas_abiertas = context.pages
            if len(paginas_abiertas) > 1:
                nueva = paginas_abiertas[-1]
                try:
                    nueva.wait_for_load_state("networkidle", timeout=8000)
                except PWTimeout:
                    pass
                if nueva.url.lower().endswith(".pdf"):
                    resp = context.request.get(nueva.url, timeout=15000)
                    if resp.ok and "pdf" in resp.headers.get("content-type", "").lower():
                        destino.write_bytes(resp.body())
                        nueva.close()
                        return True
                nueva.close()
            continue
        except Exception:
            continue
    return False


def intentar_fase_navegador(context, fila, destino: Path):
    url = url_objetivo(fila)
    if not url:
        return "No", ""

    page = context.new_page()
    pdf_capturado = {"bytes": None}

    def al_recibir_respuesta(response):
        try:
            if "pdf" in response.headers.get("content-type", "").lower():
                pdf_capturado["bytes"] = response.body()
        except Exception:
            pass

    page.on("response", al_recibir_respuesta)

    try:
        page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS_NAV)
    except PWTimeout:
        pass
    except Exception:
        page.close()
        return "No", ""

    if pdf_capturado["bytes"]:
        destino.write_bytes(pdf_capturado["bytes"])
        page.close()
        return "Si", "navegador_directo"

    if intentar_click_descarga(context, page, destino):
        page.close()
        return "Si", "navegador_click"

    page.close()
    return "No", ""


# ---------- programa principal ----------

def main():
    archivo_entrada = elegir_archivo_entrada()
    ruta_entrada = Path(archivo_entrada)

    copia_control = ruta_entrada.with_name(ruta_entrada.stem + "_ORIGINAL_COPIA.csv")
    shutil.copy2(ruta_entrada, copia_control)

    DESCARGAS_DIR.mkdir(parents=True, exist_ok=True)
    PERFIL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(archivo_entrada, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    columnas_necesarias = ["author", "title", "doi", "doi_web", "url"]
    faltantes = [c for c in columnas_necesarias if c not in df.columns]
    if faltantes:
        print("Columnas encontradas en el archivo:", list(df.columns))
        raise SystemExit(f"Faltan estas columnas: {faltantes}")

    df["descargado"] = "No"
    df["fuente_descarga"] = ""

    archivo_salida = ruta_entrada.with_name(ruta_entrada.stem + "_con_descargas.csv")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PERFIL_DIR), headless=HEADLESS, channel="chrome"
        )
        input(
            "\nSe abrió una ventana de Chrome. Inicia sesión en tu acceso "
            "institucional (ScienceDirect, IEEE, etc.) si te lo pide, y luego "
            "presiona Enter aquí para comenzar la descarga...\n"
        )

        try:
            for contador, (idx, fila) in enumerate(
                tqdm(df.iterrows(), total=len(df), desc="Descargando papers"), start=1
            ):
                nombre_base = (
                    f"{idx:04d}_{nombre_archivo_seguro(fila.get('author'))}"
                    f"_{fila.get('year', '')}"
                )
                destino = (DESCARGAS_DIR / nombre_base).with_suffix(".pdf")

                descargado, fuente = intentar_fase_rapida(fila, destino)

                if descargado == "No":
                    descargado, fuente = intentar_fase_navegador(context, fila, destino)

                df.at[idx, "descargado"] = descargado
                df.at[idx, "fuente_descarga"] = fuente

                if contador % GUARDAR_CADA == 0:
                    df.to_csv(archivo_salida, index=False)

                time.sleep(PAUSA_ENTRE_FILAS)
        finally:
            context.close()

    df.to_csv(archivo_salida, index=False)

    total_ok = (df["descargado"] == "Si").sum()
    print(f"\nDescargados: {total_ok} / {len(df)}")
    print(f"PDFs guardados en: {DESCARGAS_DIR}")
    print(f"Copia de control (original intacto): {copia_control}")
    print(f"Archivo con columnas nuevas: {archivo_salida}")


if __name__ == "__main__":
    main()
