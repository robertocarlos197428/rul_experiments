"""
test_exp007_outlier_report.py

Detecta valores anomalos (outliers) en las tablas maestras de features
(exp007_time_features) usando el criterio mediana + k*MAD, el mismo
enfoque usado para la deteccion de FPT en etapas anteriores del proyecto.

Criterio de deteccion:
    Un valor x en una columna se considera anomalo si:
        |x - mediana| > k * MAD
    donde MAD = mediana(|x - mediana(x)|)

Criterio de fila anomala:
    Basta con que UNA sola feature este fuera de umbral para que la fila
    completa se incluya en el reporte (esto permite detectar tanto eventos
    de falla real como posibles errores de calculo puntuales).

Entrada:
    tabla_maestra_learning_set.parquet
    tabla_maestra_test_set.parquet
    tabla_maestra_full_test_set.parquet
    (ubicadas en .../results/exp007_time_features/features/)

Salida:
    test_exp007_outlier_report.csv
    Contiene SOLO las filas anomalas (no el dataset completo), con:
    data_set, bearing_id, file_id, acc_filename, timestamp_sec, condition,
    feature, valor, mediana, mad, umbral_inferior, umbral_superior, k

Ejecutar desde la raiz del proyecto con:
    python -m tests.test_exp007_outlier_report
"""

import pandas as pd
from pathlib import Path

# ----------------------------------------------------------------------
# Configuracion
# ----------------------------------------------------------------------

FEATURES_DIR = Path(
    r"escribe aqui tu ruta"
)
OUTPUT_DIR = Path(r"escribe aqui tu ruta")
OUTPUT_FILE = OUTPUT_DIR / "test_exp007_outlier_report.csv"

# Constante para escalar el MAD a una desviacion estandar equivalente
# bajo normalidad (1 / (Phi^-1(0.75))), estandar en literatura robusta.
MAD_SCALE = 1.4826

K_THRESHOLD = 5  # umbral conservador: k=5 * MAD escalado

DATASETS = {
    "learning_set": "tabla_maestra_learning_set.parquet",
    "test_set": "tabla_maestra_test_set.parquet",
    "full_test_set": "tabla_maestra_full_test_set.parquet",
}

ID_COLS = ["data_set", "bearing_id", "file_id", "acc_filename",
           "timestamp_sec", "condition"]

FEATURE_COLS = [
    "h_crest_factor", "h_kurtosis", "h_mean", "h_peak", "h_peak_to_peak",
    "h_rms", "h_skewness", "h_std",
    "v_crest_factor", "v_kurtosis", "v_mean", "v_peak", "v_peak_to_peak",
    "v_rms", "v_skewness", "v_std",
]


# ----------------------------------------------------------------------
# Funciones
# ----------------------------------------------------------------------

def cargar_datasets(features_dir: Path) -> pd.DataFrame:
    """Carga los 3 parquet y los concatena en un solo DataFrame."""
    frames = []
    for nombre, archivo in DATASETS.items():
        ruta = features_dir / archivo
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontro el archivo: {ruta}")
        df = pd.read_parquet(ruta)
        if "data_set" not in df.columns:
            df["data_set"] = nombre
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def detectar_outliers_columna(serie: pd.Series, k: float = K_THRESHOLD):
    """
    Calcula mediana, MAD escalado y limites para una columna.
    Devuelve una mascara booleana de outliers y los parametros usados.
    """
    mediana = serie.median()
    mad = (serie - mediana).abs().median() * MAD_SCALE

    if mad == 0:
        # Evita division por cero / falsos positivos masivos cuando
        # la columna es casi constante. Se marca como no detectable.
        mascara = pd.Series(False, index=serie.index)
        return mascara, mediana, mad, None, None

    umbral_inf = mediana - k * mad
    umbral_sup = mediana + k * mad
    mascara = (serie < umbral_inf) | (serie > umbral_sup)

    return mascara, mediana, mad, umbral_inf, umbral_sup


def generar_reporte_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre cada feature, detecta outliers segun mediana + k*MAD,
    y arma un reporte largo (una fila por combinacion fila-feature anomala).
    """
    registros = []

    for feature in FEATURE_COLS:
        serie = df[feature]
        mascara, mediana, mad, umbral_inf, umbral_sup = detectar_outliers_columna(serie)

        if not mascara.any():
            continue

        filas_anomalas = df.loc[mascara, ID_COLS].copy()
        filas_anomalas["feature"] = feature
        filas_anomalas["valor"] = serie.loc[mascara].values
        filas_anomalas["mediana"] = mediana
        filas_anomalas["mad_escalado"] = mad
        filas_anomalas["umbral_inferior"] = umbral_inf
        filas_anomalas["umbral_superior"] = umbral_sup
        filas_anomalas["k"] = K_THRESHOLD

        registros.append(filas_anomalas)

    if not registros:
        return pd.DataFrame(columns=ID_COLS + [
            "feature", "valor", "mediana", "mad_escalado",
            "umbral_inferior", "umbral_superior", "k",
        ])

    reporte = pd.concat(registros, ignore_index=True)

    # Orden util para lectura: primero los casos mas extremos
    reporte["desviacion_relativa"] = (
        (reporte["valor"] - reporte["mediana"]).abs() / reporte["mad_escalado"]
    )
    reporte = reporte.sort_values("desviacion_relativa", ascending=False)
    reporte = reporte.drop(columns="desviacion_relativa").reset_index(drop=True)

    return reporte


def main():
    print(f"Cargando datasets desde: {FEATURES_DIR}")
    df = cargar_datasets(FEATURES_DIR)
    print(f"Total de filas cargadas (3 datasets): {len(df)}")

    print(f"Detectando outliers (mediana + {K_THRESHOLD}xMAD, 1 feature basta)...")
    reporte = generar_reporte_outliers(df)
    print(f"Filas anomalas detectadas: {len(reporte)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reporte.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Reporte guardado en: {OUTPUT_FILE}")

    if not reporte.empty:
        print("\nResumen por feature:")
        print(reporte["feature"].value_counts())
        print("\nResumen por dataset:")
        print(reporte["data_set"].value_counts())


if __name__ == "__main__":
    main()