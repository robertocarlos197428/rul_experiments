"""
012_raw_hi_exploration.py

Experimento: exp012_raw_hi_exploration
Tipo: EXPLORACION INFORMAL (Capa 1) - no se usa para decidir la receta del HI.

Objetivo: calcular un HI "bruto" (promedio simple, pesos iguales, SIN cummax,
SIN filtrado de outliers) usando las 8 features x 2 canales, para los 17
bearings de FEMTO (6 Learning_set + 11 Full_Test_set), y visualizar 3
variantes por bearing:
    - HI_H  -> promedio de las 8 features del canal H
    - HI_V  -> promedio de las 8 features del canal V
    - HI_HV -> promedio de las 16 features (H+V juntas)

Cada bearing se normaliza con SU PROPIA ventana sana (primer 10% de sus
snapshots, sin filtrar outliers) como Xmin, y su propio percentil 99 como
Xmax. Se aplica clip [0, 1]. No se aplica cummax (version "bruta").

Genera automaticamente:
    experiments/exp012_raw_hi_exploration/
        config.yaml
        manifest.json
        notes.md
        results/exp012_raw_hi_exploration/
            figures/  -> 9 imagenes (grid 3x2: filas HI_H/HI_V/HI_HV, cols 2 bearings)
            log/      -> log de ejecucion
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# ----------------------------------------------------------------------
# CONFIGURACION
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(r"escribe aqui tu ruta")

FEATURES_DIR = PROJECT_ROOT / "results" / "exp007_time_features" / "features"
LEARNING_PARQUET = FEATURES_DIR / "tabla_maestra_learning_set.parquet"
TEST_PARQUET = FEATURES_DIR / "tabla_maestra_full_test_set.parquet"

EXPERIMENT_NAME = "exp012_raw_hi_exploration"
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / EXPERIMENT_NAME
FIGURES_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "figures"
LOG_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "log"

# Las 8 features base (nombres de columna sin prefijo h_/v_)
FEATURE_BASENAMES = [
    "rms",
    "std",
    "peak",
    "peak_to_peak",
    "mean",
    "skewness",
    "kurtosis",
    "crest_factor",
]

HEALTHY_WINDOW_FRACTION = 0.10  # primer 10% de snapshots
PERCENTILE_MAX = 99

# ----------------------------------------------------------------------
# SETUP DE CARPETAS Y LOGGING
# ----------------------------------------------------------------------

def setup_experiment_dirs():
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    log_file = LOG_DIR / f"{EXPERIMENT_NAME}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(EXPERIMENT_NAME)


# ----------------------------------------------------------------------
# CARGA DE DATOS
# ----------------------------------------------------------------------

def load_data(logger: logging.Logger) -> pd.DataFrame:
    logger.info(f"Cargando Learning_set desde: {LEARNING_PARQUET}")
    df_learning = pd.read_parquet(LEARNING_PARQUET)

    logger.info(f"Cargando Full_Test_set desde: {TEST_PARQUET}")
    df_test = pd.read_parquet(TEST_PARQUET)

    df = pd.concat([df_learning, df_test], ignore_index=True)
    df["hours"] = df["timestamp_sec"] / 3600.0

    bearings = df["bearing_id"].unique().tolist()
    logger.info(f"Total bearings cargados: {len(bearings)} -> {bearings}")

    return df


def ordered_bearings(df: pd.DataFrame, logger: logging.Logger) -> list:
    """Devuelve la lista de bearings: Learning_set primero, luego Test_set,
    en el orden en que aparecen en el dataframe concatenado."""
    seen = []
    for b in df["bearing_id"]:
        if b not in seen:
            seen.append(b)
    logger.info(f"Orden final de bearings: {seen}")
    return seen


# ----------------------------------------------------------------------
# NORMALIZACION Y CALCULO DE HI
# ----------------------------------------------------------------------

def normalize_feature(series: pd.Series) -> pd.Series:
    """Normaliza una serie usando healthy-window (media del primer 10%)
    como Xmin y percentil 99 como Xmax. Aplica clip [0, 1].
    Sin filtrado de outliers en la ventana sana (version bruta)."""
    n = len(series)
    n_healthy = max(1, int(np.ceil(n * HEALTHY_WINDOW_FRACTION)))

    x_min = series.iloc[:n_healthy].mean()
    x_max = np.percentile(series, PERCENTILE_MAX)

    denom = x_max - x_min
    if denom == 0:
        denom = 1e-9  # evita division por cero en casos degenerados

    normalized = (series - x_min) / denom
    normalized = normalized.clip(lower=0.0, upper=1.0)
    return normalized


def compute_hi_for_bearing(df_bearing: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    """Calcula HI_H, HI_V y HI_HV (bruto, sin cummax) para un bearing."""
    df_bearing = df_bearing.sort_values("hours").reset_index(drop=True)

    normalized_cols = {}
    for base in FEATURE_BASENAMES:
        for channel, prefix in [("H", "h_"), ("V", "v_")]:
            col = f"{prefix}{base}"
            if col not in df_bearing.columns:
                logger.warning(f"Columna no encontrada: {col} (bearing {df_bearing['bearing_id'].iloc[0]})")
                continue
            normalized_cols[f"{col}_norm"] = normalize_feature(df_bearing[col])

    norm_df = pd.DataFrame(normalized_cols)

    h_cols = [c for c in norm_df.columns if c.startswith("h_")]
    v_cols = [c for c in norm_df.columns if c.startswith("v_")]

    df_bearing = df_bearing.copy()
    df_bearing["HI_H"] = norm_df[h_cols].mean(axis=1)
    df_bearing["HI_V"] = norm_df[v_cols].mean(axis=1)
    df_bearing["HI_HV"] = norm_df[h_cols + v_cols].mean(axis=1)

    return df_bearing


# ----------------------------------------------------------------------
# GRAFICADO
# ----------------------------------------------------------------------

def plot_hi_pair(df: pd.DataFrame, bearing_a: str, bearing_b, pair_index: int, logger: logging.Logger):
    """Genera 1 imagen con grid 3x2: filas = HI_H/HI_V/HI_HV, columnas = hasta 2 bearings."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 12), sharex=False)

    bearings_pair = [bearing_a, bearing_b]
    hi_rows = ["HI_H", "HI_V", "HI_HV"]

    for col_idx, bearing in enumerate(bearings_pair):
        if bearing is None:
            for row_idx in range(3):
                axes[row_idx, col_idx].axis("off")
            continue

        sub = df[df["bearing_id"] == bearing].sort_values("hours")

        for row_idx, hi_name in enumerate(hi_rows):
            ax = axes[row_idx, col_idx]
            ax.plot(sub["hours"], sub[hi_name], linewidth=0.8)
            ax.set_ylim(0, 1)
            ax.set_title(f"{bearing} - {hi_name}", fontsize=10)
            ax.set_xlabel("Tiempo (horas)")
            ax.set_ylabel(hi_name)
            ax.grid(True, alpha=0.3)

    fig.suptitle(f"HI bruto (exploracion) - {bearing_a} vs {bearing_b or ''}", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = FIGURES_DIR / f"hi_pair_{pair_index:02d}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    logger.info(f"Guardado: {out_path}")
    return out_path


# ----------------------------------------------------------------------
# ARCHIVOS DE EXPERIMENTO
# ----------------------------------------------------------------------

def write_config(bearing_order: list):
    config = {
        "experiment_name": EXPERIMENT_NAME,
        "script": "012_raw_hi_exploration.py",
        "type": "exploracion_informal_capa_1_no_usar_para_receta_final",
        "input_parquets": [str(LEARNING_PARQUET), str(TEST_PARQUET)],
        "bearings_order": bearing_order,
        "features": FEATURE_BASENAMES,
        "healthy_window_fraction": HEALTHY_WINDOW_FRACTION,
        "percentile_max": PERCENTILE_MAX,
        "clip_range": [0, 1],
        "cummax_applied": False,
        "outlier_filtering_applied": False,
        "hi_variants": ["HI_H (8 features canal H)", "HI_V (8 features canal V)", "HI_HV (16 features H+V)"],
        "weights": "iguales (1/8 o 1/16 segun variante)",
    }
    with open(EXPERIMENT_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)


def write_manifest(generated_files: list):
    manifest = {
        "experiment_name": EXPERIMENT_NAME,
        "timestamp": datetime.now().isoformat(),
        "input_parquets": [str(LEARNING_PARQUET), str(TEST_PARQUET)],
        "outputs": [str(p) for p in generated_files],
    }
    with open(EXPERIMENT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def write_notes():
    notes = f"""# {EXPERIMENT_NAME}

## IMPORTANTE: exploracion informal
Este experimento es exploratorio (Capa 1). NO se usa para decidir la receta
final del HI (esa decision se documenta en exp011_feature_zoom_for_HI y en
el reporte principal). Aqui solo se mira como se ve un HI "bruto" (todas las
8 features, sin filtrar outliers, sin cummax) en los 17 bearings, incluyendo
Full_Test_set.

## Que se calculo
- HI_H  = promedio de 8 features normalizadas (canal H), pesos iguales.
- HI_V  = promedio de 8 features normalizadas (canal V), pesos iguales.
- HI_HV = promedio de 16 features normalizadas (H+V), pesos iguales.

Normalizacion: Xmin = media ventana sana (primer 10%, SIN filtrar outliers),
Xmax = percentil 99, clip [0, 1]. Sin cummax (no se fuerza monotonicidad).

## Bearings incluidos
17 en total: 6 Learning_set + 11 Full_Test_set (orden: Learning primero).

## Pendiente / siguiente paso
- Comparar esta version bruta contra la version final del HI (solo RMS,
  Std, Peak; con cummax) para dimensionar el efecto de incluir features
  descartadas y de no forzar monotonicidad.
"""
    with open(EXPERIMENT_DIR / "notes.md", "w", encoding="utf-8") as f:
        f.write(notes)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    setup_experiment_dirs()
    logger = setup_logging()
    logger.info(f"Inicio experimento: {EXPERIMENT_NAME}")

    df = load_data(logger)
    bearing_order = ordered_bearings(df, logger)

    logger.info("Calculando HI_H, HI_V, HI_HV por bearing (sin cummax)...")
    hi_frames = []
    for bearing in bearing_order:
        df_b = df[df["bearing_id"] == bearing]
        hi_frames.append(compute_hi_for_bearing(df_b, logger))
    df_hi = pd.concat(hi_frames, ignore_index=True)

    generated_files = []
    pair_index = 1
    for i in range(0, len(bearing_order), 2):
        bearing_a = bearing_order[i]
        bearing_b = bearing_order[i + 1] if i + 1 < len(bearing_order) else None
        path = plot_hi_pair(df_hi, bearing_a, bearing_b, pair_index, logger)
        generated_files.append(path)
        pair_index += 1

    write_config(bearing_order)
    write_manifest(generated_files)
    write_notes()

    logger.info(f"Experimento completado. {len(generated_files)} imagenes generadas.")
    logger.info(f"Resultados en: {FIGURES_DIR}")


if __name__ == "__main__":
    main()