"""
013_HI_16vs3_features_comparison.py

Experimento: exp013_HI_16vs3_features_comparison
Tipo: EXPLORACION INFORMAL (Capa 1) - comparacion visual, no decide la receta.

Objetivo: comparar, para los 17 bearings (6 Learning_set + 11 Full_Test_set),
el HI_HV calculado de 2 formas distintas, mismo metodo de normalizacion:

    - HI16 -> promedio de las 16 features normalizadas (8 features x 2 canales,
              "version bruta", igual que exp012_raw_hi_exploration)
    - HI3  -> promedio de solo 6 columnas normalizadas: RMS, Std, Peak (H y V)
              (la receta final decidida en exp011_feature_zoom_for_HI)

En ambos casos: normalizacion por bearing (Xmin = media ventana sana 10%,
Xmax = percentil 99, propios de cada bearing), clip [0, 1], SIN cummax.

Genera automaticamente:
    experiments/exp013_HI_16vs3_features_comparison/
        config.yaml
        manifest.json
        notes.md
        results/exp013_HI_16vs3_features_comparison/
            figures/  -> 3 imagenes (grid 3x4: 6 bearings por imagen, 17 total)
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

EXPERIMENT_NAME = "exp013_HI_16vs3_features_comparison"
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / EXPERIMENT_NAME
FIGURES_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "figures"
LOG_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "log"

# Las 8 features base (usadas para HI16)
FEATURE_BASENAMES_16 = [
    "rms",
    "std",
    "peak",
    "peak_to_peak",
    "mean",
    "skewness",
    "kurtosis",
    "crest_factor",
]

# Las 3 features base finales (usadas para HI3)
FEATURE_BASENAMES_3 = ["rms", "std", "peak"]

HEALTHY_WINDOW_FRACTION = 0.10
PERCENTILE_MAX = 99
BEARINGS_PER_IMAGE = 6  # 3 filas x 2 bearings por fila

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
    """Normaliza usando healthy-window (media primer 10%) como Xmin y P99
    como Xmax. Clip [0, 1]. Sin filtrado de outliers."""
    n = len(series)
    n_healthy = max(1, int(np.ceil(n * HEALTHY_WINDOW_FRACTION)))

    x_min = series.iloc[:n_healthy].mean()
    x_max = np.percentile(series, PERCENTILE_MAX)

    denom = x_max - x_min
    if denom == 0:
        denom = 1e-9

    normalized = (series - x_min) / denom
    normalized = normalized.clip(lower=0.0, upper=1.0)
    return normalized


def compute_hi_variant(df_bearing: pd.DataFrame, feature_basenames: list, logger: logging.Logger) -> pd.Series:
    """Calcula HI_HV (promedio de todas las columnas H+V normalizadas) para
    el set de features indicado."""
    normalized_cols = {}
    for base in feature_basenames:
        for prefix in ["h_", "v_"]:
            col = f"{prefix}{base}"
            if col not in df_bearing.columns:
                logger.warning(f"Columna no encontrada: {col} (bearing {df_bearing['bearing_id'].iloc[0]})")
                continue
            normalized_cols[col] = normalize_feature(df_bearing[col])

    norm_df = pd.DataFrame(normalized_cols)
    return norm_df.mean(axis=1)


def compute_both_hi_for_bearing(df_bearing: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    df_bearing = df_bearing.sort_values("hours").reset_index(drop=True)
    df_bearing = df_bearing.copy()
    df_bearing["HI16"] = compute_hi_variant(df_bearing, FEATURE_BASENAMES_16, logger)
    df_bearing["HI3"] = compute_hi_variant(df_bearing, FEATURE_BASENAMES_3, logger)
    return df_bearing


# ----------------------------------------------------------------------
# GRAFICADO
# ----------------------------------------------------------------------

def plot_bearing_group(df: pd.DataFrame, bearings_group: list, image_index: int, logger: logging.Logger):
    """Genera 1 imagen grid 3x4: 3 filas (bearings de a 2), 4 columnas
    (HI16, HI3, HI16, HI3). bearings_group tiene hasta 6 bearings."""
    fig, axes = plt.subplots(3, 4, figsize=(18, 12), sharex=False)

    # Rellenar con None hasta completar 6 bearings (3 filas x 2)
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

    fig.suptitle("HI_HV: 16 features vs 3 features (RMS+Std+Peak)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = FIGURES_DIR / f"hi_comparison_{image_index:02d}.png"
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
        "script": "013_HI_16vs3_features_comparison.py",
        "type": "exploracion_informal_capa_1_no_usar_para_receta_final",
        "input_parquets": [str(LEARNING_PARQUET), str(TEST_PARQUET)],
        "bearings_order": bearing_order,
        "hi16_features": FEATURE_BASENAMES_16,
        "hi3_features": FEATURE_BASENAMES_3,
        "healthy_window_fraction": HEALTHY_WINDOW_FRACTION,
        "percentile_max": PERCENTILE_MAX,
        "clip_range": [0, 1],
        "cummax_applied": False,
        "outlier_filtering_applied": False,
        "grid_layout": "3x4 por imagen, 6 bearings por imagen (cada bearing: col HI16 + col HI3)",
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
Este experimento es exploratorio (Capa 1). Compara visualmente el HI_HV
calculado con las 16 features (version bruta, exp012) contra el HI_HV
calculado solo con RMS+Std+Peak (receta final decidida en exp011).
No decide nada nuevo por si solo, sirve para dimensionar el efecto de
la seleccion de features hecha en exp011.

## Que se calculo
- HI16 = promedio de 16 features normalizadas (8 features x H/V), pesos iguales.
- HI3  = promedio de 6 columnas normalizadas (RMS, Std, Peak x H/V), pesos iguales.

Mismo metodo de normalizacion en ambos casos: Xmin = media ventana sana
(primer 10%, sin filtrar outliers), Xmax = percentil 99, clip [0, 1].
Sin cummax.

## Bearings incluidos
17 en total: 6 Learning_set + 11 Full_Test_set (orden: Learning primero).

## Pendiente / siguiente paso
- Revisar si HI3 reduce el ruido/falsos picos observados en HI16 para
  bearings problematicos (ej. Bearing2_3 en exp012).
- Si HI3 se ve limpio y consistente, avanzar a aplicar cummax sobre HI3
  como version candidata final.
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

    logger.info("Calculando HI16 y HI3 por bearing (sin cummax)...")
    hi_frames = []
    for bearing in bearing_order:
        df_b = df[df["bearing_id"] == bearing]
        hi_frames.append(compute_both_hi_for_bearing(df_b, logger))
    df_hi = pd.concat(hi_frames, ignore_index=True)

    generated_files = []
    for i in range(0, len(bearing_order), BEARINGS_PER_IMAGE):
        group = bearing_order[i : i + BEARINGS_PER_IMAGE]
        image_index = (i // BEARINGS_PER_IMAGE) + 1
        path = plot_bearing_group(df_hi, group, image_index, logger)
        generated_files.append(path)

    write_config(bearing_order)
    write_manifest(generated_files)
    write_notes()

    logger.info(f"Experimento completado. {len(generated_files)} imagenes generadas.")
    logger.info(f"Resultados en: {FIGURES_DIR}")


if __name__ == "__main__":
    main()