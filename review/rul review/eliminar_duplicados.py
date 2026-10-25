"""
Deduplicación de la tabla MASTER_RAW_DOI_URL
Agrupación de duplicados: por author + title (normalizados).
Reglas para elegir qué fila queda dentro de cada grupo:
 1) Si estado_doi == "Elsevier sin revisar" -> esa fila se queda.
 2) Si no, se queda la fila cuyo DOI (normalizado) tiene mayor
    frecuencia combinada entre las columnas doi + doi_web.
 3) Si hay empate, se prioriza la fila que tenga doi_web informado.

DOIs normalizados: se ignora "https://doi.org/" y mayúsculas/minúsculas,
por lo que "https://doi.org/10.1016/j.ecmx.2023.100503" y
"10.1016/j.ecmx.2023.100503" cuentan como el mismo DOI.
"""

import re
from collections import Counter

import pandas as pd
from tkinter import Tk, filedialog


def normalizar_doi(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    v = str(valor).strip().lower()
    v = re.sub(r"^https?://(dx\.)?doi\.org/", "", v)
    return v.rstrip("/")


def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    v = str(valor).strip().lower()
    v = re.sub(r"[^\w\s]", "", v)  # quita puntuación
    v = re.sub(r"\s+", " ", v)  # espacios múltiples a uno solo
    return v.strip()


def elegir_fila(grupo: pd.DataFrame) -> pd.Series:
    # Prioridad 1
    prioridad1 = grupo[grupo["estado_doi"] == "Elsevier sin revisar"]
    if len(prioridad1) > 0:
        return prioridad1.iloc[0]

    # Prioridad 2: mayor frecuencia combinada
    grupo = grupo.sort_values("frecuencia", ascending=False)
    max_frecuencia = grupo["frecuencia"].iloc[0]
    empatados = grupo[grupo["frecuencia"] == max_frecuencia]
    if len(empatados) == 1:
        return empatados.iloc[0]

    # Prioridad 3: preferir la fila con doi_web informado
    con_doi_web = empatados[empatados["doi_web_norm"].notna()]
    if len(con_doi_web) > 0:
        return con_doi_web.iloc[0]
    return empatados.iloc[0]


def elegir_archivo_entrada() -> str:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta = filedialog.askopenfilename(
        title="Selecciona el CSV a deduplicar",
        filetypes=[("Archivos CSV", "*.csv")],
    )
    root.destroy()
    if not ruta:
        raise SystemExit("No se seleccionó ningún archivo.")
    return ruta


def elegir_archivo_salida(ruta_entrada: str) -> str:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta = filedialog.asksaveasfilename(
        title="Guardar resultado como",
        defaultextension=".csv",
        filetypes=[("Archivos CSV", "*.csv")],
        initialfile=ruta_entrada.rsplit("/", 1)[-1].replace(".csv", "_dedup.csv"),
    )
    root.destroy()
    if not ruta:
        raise SystemExit("No se seleccionó dónde guardar el resultado.")
    return ruta


def main():
    archivo_entrada = elegir_archivo_entrada()
    archivo_salida = elegir_archivo_salida(archivo_entrada)

    df = pd.read_csv(archivo_entrada, sep=None, engine="python", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    columnas_necesarias = ["author", "title", "doi", "doi_web", "estado_doi"]
    faltantes = [c for c in columnas_necesarias if c not in df.columns]
    if faltantes:
        print("Columnas encontradas en el archivo:", list(df.columns))
        raise SystemExit(f"Faltan estas columnas: {faltantes}")

    df["doi_norm"] = df["doi"].apply(normalizar_doi)
    df["doi_web_norm"] = df["doi_web"].apply(normalizar_doi)

    # clave de agrupación: author + title normalizados
    df["clave_grupo"] = (
        df["author"].apply(normalizar_texto) + " || " + df["title"].apply(normalizar_texto)
    )

    # frecuencia combinada de cada DOI normalizado en ambas columnas
    conteo = Counter()
    for col in ["doi_norm", "doi_web_norm"]:
        conteo.update(df[col].dropna())
    df["frecuencia"] = (
        df["doi_norm"].map(conteo).fillna(0) + df["doi_web_norm"].map(conteo).fillna(0)
    )

    resultado = (
        df.groupby("clave_grupo", group_keys=False)
        .apply(elegir_fila)
        .reset_index(drop=True)
    )

    columnas_auxiliares = ["doi_norm", "doi_web_norm", "clave_grupo", "frecuencia"]
    columnas_auxiliares = [c for c in columnas_auxiliares if c in resultado.columns]
    resultado = resultado.drop(columns=columnas_auxiliares)

    resultado.to_csv(archivo_salida, index=False)
    print(f"Filas originales: {len(df)} -> Filas finales: {len(resultado)}")
    print(f"Guardado en: {archivo_salida}")


if __name__ == "__main__":
    main()
