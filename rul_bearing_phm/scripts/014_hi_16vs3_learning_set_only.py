"""
014_HI_16vs3_learning_only.py

Experimento: exp014_HI_16vs3_learning_only
Tipo: EXPLORACION INFORMAL (Capa 1) - version recortada de exp013.

Objetivo: MISMO que exp013 pero SOLO sobre Learning_set (6 bearings).
El Learning_set es el unico que se debe usar para toma de decisiones.

Compara:
    - HI16 -> promedio 16 features normalizadas (8 x 2 canales)
    - HI3  -> promedio 6 columnas: RMS, Std, Peak (H y V)

Metodo: normalizacion por bearing (Xmin = media ventana sana 10%, 
Xmax = percentil 99, propios de cada bearing), clip [0,1], SIN cummax.

Genera:
    experiments/exp014_HI_16vs3_learning_only/
        config.yaml
        manifest.json
        notes.md
        results/exp014_HI_16vs3_learning_only/
            figures/hi_comparison_learning_01.png
            log/
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

EXPERIMENT_NAME = "exp014_HI_16vs3_learning_only"
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / EXPERIMENT_NAME
FIGURES_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "figures"
LOG_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "log"

FEATURE_BASENAMES_16 = [
    "rms", "std", "peak", "peak_to_peak",
    "mean", "skewness", "kurtosis", "crest_factor",
]
FEATURE_BASENAMES_3 = ["rms", "std", "peak"]

HEALTHY_WINDOW_FRACTION = 0.10
PERCENTILE_MAX = 99

# ----------------------------------------------------------------------
# SETUP
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
# CARGA
# ----------------------------------------------------------------------

def load_data(logger: logging.Logger) -> pd.DataFrame:
    logger.info(f"Cargando SOLO Learning_set desde: {LEARNING_PARQUET}")
    df = pd.read_parquet(LEARNING_PARQUET)
    df["hours"] = df["timestamp_sec"] / 3600.0
    bearings = df["bearing_id"].unique().tolist()
    logger.info(f"Total bearings Learning_set: {len(bearings)} -> {bearings}")
    return df

def ordered_bearings(df: pd.DataFrame) -> list:
    seen = []
    for b in df["bearing_id"]:
        if b not in seen:
            seen.append(b)
    return seen

# ----------------------------------------------------------------------
# NORMALIZACION
# ----------------------------------------------------------------------

def normalize_feature(series: pd.Series) -> pd.Series:
    n = len(series)
    n_healthy = max(1, int(np.ceil(n * HEALTHY_WINDOW_FRACTION)))
    x_min = series.iloc[:n_healthy].mean()
    x_max = np.percentile(series, PERCENTILE_MAX)
    denom = x_max - x_min if (x_max - x_min) != 0 else 1e-9
    normalized = (series - x_min) / denom
    return normalized.clip(lower=0.0, upper=1.0)

def compute_hi_variant(df_bearing: pd.DataFrame, feature_basenames: list, logger: logging.Logger) -> pd.Series:
    normalized_cols = {}
    for base in feature_basenames:
        for prefix in ["h_", "v_"]:
            col = f"{prefix}{base}"
            if col not in df_bearing.columns:
                logger.warning(f"Columna no encontrada: {col}")
                continue
            normalized_cols[col] = normalize_feature(df_bearing[col])
    norm_df = pd.DataFrame(normalized_cols)
    return norm_df.mean(axis=1)

def compute_both_hi_for_bearing(df_bearing: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    df_bearing = df_bearing.sort_values("hours").reset_index(drop=True).copy()
    df_bearing["HI16"] = compute_hi_variant(df_bearing, FEATURE_BASENAMES_16, logger)
    df_bearing["HI3"] = compute_hi_variant(df_bearing, FEATURE_BASENAMES_3, logger)
    return df_bearing

# ----------------------------------------------------------------------
# GRAFICADO - 1 imagen con 6 bearings (3x4)
# ----------------------------------------------------------------------

def plot_learning_group(df: pd.DataFrame, bearings_group: list, logger: logging.Logger):
    fig, axes = plt.subplots(3, 4, figsize=(18, 12), sharex=False)
    padded = bearings_group + [None] * (6 - len(bearings_group))

    for row in range(3):
        for pair_col in range(2):
            bearing = padded[row * 2 + pair_col]
            col_hi16 = pair_col * 2
            col_hi3 = pair_col * 2 + 1
            ax16 = axes[row, col_hi16]
            ax3 = axes[row, col_hi3]

            if bearing is None:
                ax16.axis("off")
                ax3.axis("off")
                continue

            sub = df[df["bearing_id"] == bearing].sort_values("hours")

            ax16.plot(sub["hours"], sub["HI16"], linewidth=0.8, color="tab:blue")
            ax16.set_ylim(0, 1)
            ax16.set_title(f"{bearing} - HI16", fontsize=10)
            ax16.set_xlabel("Tiempo (horas)")
            ax16.set_ylabel("HI16")
            ax16.grid(True, alpha=0.3)

            ax3.plot(sub["hours"], sub["HI3"], linewidth=0.8, color="tab:orange")
            ax3.set_ylim(0, 1)
            ax3.set_title(f"{bearing} - HI3", fontsize=10)
            ax3.set_xlabel("Tiempo (horas)")
            ax3.set_ylabel("HI3")
            ax3.grid(True, alpha=0.3)

    fig.suptitle("HI_HV: 16 features vs 3 features (RMS+Std+Peak) - SOLO Learning_set", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = FIGURES_DIR / f"hi_comparison_learning_01.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info(f"Guardado: {out_path}")
    return out_path

# ----------------------------------------------------------------------
# YAML, MANIFEST, NOTES
# ----------------------------------------------------------------------

def write_config(bearing_order: list):
    config = {
        "experiment_name": EXPERIMENT_NAME,
        "script": "014_HI_16vs3_learning_only.py",
        "type": "exploracion_informal_capa_1_learning_only",
        "input_parquet": str(LEARNING_PARQUET),
        "bearings_order": bearing_order,
        "bearings_count": len(bearing_order),
        "decision_scope": "Learning_set only - es el unico valido para toma de decisiones",
        "hi16_features": FEATURE_BASENAMES_16,
        "hi3_features": FEATURE_BASENAMES_3,
        "healthy_window_fraction": HEALTHY_WINDOW_FRACTION,
        "percentile_max": PERCENTILE_MAX,
        "clip_range": [0, 1],
        "cummax_applied": False,
        "outlier_filtering_applied": False,
        "grid_layout": "3x4, 6 bearings en 1 imagen (cada bearing: col HI16 + col HI3)",
    }
    with open(EXPERIMENT_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

def write_manifest(generated_files: list):
    manifest = {
        "experiment_name": EXPERIMENT_NAME,
        "timestamp": datetime.now().isoformat(),
        "input_parquet": str(LEARNING_PARQUET),
        "outputs": [str(p) for p in generated_files],
    }
    with open(EXPERIMENT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def write_notes():
    notes = f"""# {EXPERIMENT_NAME}

## Objetivo
Version recortada de exp013. Mismo metodo pero SOLO sobre Learning_set (6 bearings).
El Learning_set es el unico conjunto valido para toma de decisiones de features.
Full_Test_set se excluye deliberadamente para no contaminar la evaluacion.

## Que se compara
- HI16 = promedio de 16 features normalizadas (8 x H/V) - version bruta exp012
- HI3  = promedio de 6 columnas (RMS, Std, Peak x H/V) - receta final exp011

Normalizacion: Xmin = media ventana sana primer 10%, Xmax = percentil 99, por bearing, clip [0,1], sin cummax.

## Salida
1 imagen: hi_comparison_learning_01.png con grid 3x4 (3 filas x 2 bearings, cada bearing 2 cols HI16/HI3)

## Decision esperada
Si HI3 se ve mas limpio y consistente que HI16 en los 6 Learning bearings, se confirma
que la seleccion de exp011 es correcta y se puede avanzar a aplicar cummax sobre HI3.
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
    bearing_order = ordered_bearings(df)
    logger.info(f"Orden bearings: {bearing_order}")

    logger.info("Calculando HI16 y HI3 por bearing...")
    hi_frames = []
    for bearing in bearing_order:
        df_b = df[df["bearing_id"] == bearing]
        hi_frames.append(compute_both_hi_for_bearing(df_b, logger))
    df_hi = pd.concat(hi_frames, ignore_index=True)

    path = plot_learning_group(df_hi, bearing_order, logger)

    write_config(bearing_order)
    write_manifest([path])
    write_notes()

    logger.info(f"Completado. Imagen en: {FIGURES_DIR}")

if __name__ == "__main__":
    main()