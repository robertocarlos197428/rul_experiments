"""
011_feature_zoom_for_HI.py

Experimento: exp011_feature_zoom_for_HI
Objetivo: Generar graficos individuales por feature/canal (grid 3x2 con los 6
bearings de Learning_set), usando escalas fijas en el eje Y para evitar que
outliers distorsionen la lectura visual de tendencia/monotonicidad.

Features analizadas: RMS, Std, Skewness, Kurtosis (Peak ya fue confirmada,
no requiere este analisis).

Genera automaticamente la estructura de carpetas del experimento:
    experiments/exp011_feature_zoom_for_HI/
        config.yaml
        manifest.json
        notes.md
        results/
            figures/   -> 8 imagenes (4 features x 2 canales)
            log/       -> log de ejecucion
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml

# ----------------------------------------------------------------------
# CONFIGURACION
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(r"escribe aqui tu ruta")

INPUT_PARQUET = (
    PROJECT_ROOT
    / "results"
    / "exp007_time_features"
    / "features"
    / "tabla_maestra_learning_set.parquet"
)

EXPERIMENT_NAME = "exp011_feature_zoom_for_HI"
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / EXPERIMENT_NAME
FIGURES_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "figures"
LOG_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME / "log"

BEARINGS = [
    "Bearing1_1",
    "Bearing1_2",
    "Bearing2_1",
    "Bearing2_2",
    "Bearing3_1",
    "Bearing3_2",
]

# feature base -> (nombre_columna_H, nombre_columna_V, ylim)
FEATURES = {
    "rms": ("h_rms", "v_rms", (0, 5)),
    "std": ("h_std", "v_std", (0, 4)),
    "skewness": ("h_skewness", "v_skewness", (0, 2)),
    "kurtosis": ("h_kurtosis", "v_kurtosis", (0, 50)),
}

CHANNELS = ["H", "V"]

# ----------------------------------------------------------------------
# SETUP DE CARPETAS Y LOGGING
# ----------------------------------------------------------------------

def setup_experiment_dirs():
    """Crea la estructura de carpetas del experimento."""
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    """Configura logging a archivo y consola."""
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
    logger.info(f"Cargando datos desde: {INPUT_PARQUET}")
    df = pd.read_parquet(INPUT_PARQUET)

    faltantes = set(BEARINGS) - set(df["bearing_id"].unique())
    if faltantes:
        logger.warning(f"Bearings no encontrados en el parquet: {faltantes}")

    df = df[df["bearing_id"].isin(BEARINGS)].copy()
    df["hours"] = df["timestamp_sec"] / 3600.0

    logger.info(f"Filas cargadas (Learning_set, 6 bearings): {len(df)}")
    return df


# ----------------------------------------------------------------------
# GRAFICADO
# ----------------------------------------------------------------------

def plot_feature_channel(
    df: pd.DataFrame,
    feature_name: str,
    column: str,
    ylim: tuple,
    channel: str,
    logger: logging.Logger,
):
    """Genera 1 imagen con grid 3x2 (6 bearings) para una feature/canal."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 12), sharex=False)
    axes = axes.flatten()

    for ax, bearing in zip(axes, BEARINGS):
        sub = df[df["bearing_id"] == bearing].sort_values("hours")
        ax.plot(sub["hours"], sub[column], linewidth=0.8)
        ax.set_ylim(ylim)
        ax.set_title(bearing, fontsize=10)
        ax.set_xlabel("Tiempo (horas)")
        ax.set_ylabel(feature_name)
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"{feature_name.upper()} - Canal {channel} (Learning_set)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = FIGURES_DIR / f"{feature_name}_{channel}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    logger.info(f"Guardado: {out_path}")
    return out_path


# ----------------------------------------------------------------------
# ARCHIVOS DE EXPERIMENTO (config, manifest, notes)
# ----------------------------------------------------------------------

def write_config():
    config = {
        "experiment_name": EXPERIMENT_NAME,
        "script": "011_feature_zoom_for_HI.py",
        "input_parquet": str(INPUT_PARQUET),
        "bearings": BEARINGS,
        "features": {
            name: {"col_h": h, "col_v": v, "ylim": list(ylim)}
            for name, (h, v, ylim) in FEATURES.items()
        },
        "channels": CHANNELS,
        "x_axis": "timestamp_sec / 3600 (horas)",
        "grid_layout": "3x2, orden izquierda-derecha / arriba-abajo",
    }
    with open(EXPERIMENT_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)


def write_manifest(generated_files: list):
    manifest = {
        "experiment_name": EXPERIMENT_NAME,
        "timestamp": datetime.now().isoformat(),
        "input_parquet": str(INPUT_PARQUET),
        "outputs": [str(p) for p in generated_files],
    }
    with open(EXPERIMENT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def write_notes():
    notes = f"""# {EXPERIMENT_NAME}

## Objetivo
Revisar visualmente RMS, Std, Skewness y Kurtosis (canales H y V) en
Learning_set, usando escalas fijas por feature para evitar que outliers
distorsionen la lectura de tendencia y monotonicidad.

## Escalas fijas usadas
- RMS: 0-5
- Std: 0-4
- Skewness: 0-2
- Kurtosis: 0-50

(Peak no se incluye en este analisis, ya fue confirmada como feature valida.)

## Bearings incluidos
{', '.join(BEARINGS)}

## Pendiente
- Revisar resultado y actualizar veredicto de Skewness y Kurtosis.
- Definir tratamiento de outliers puntuales antes de normalizar.
- Comparar HI con y sin correccion de outliers (experimento posterior).
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

    generated_files = []
    for feature_name, (col_h, col_v, ylim) in FEATURES.items():
        for channel, column in zip(CHANNELS, [col_h, col_v]):
            path = plot_feature_channel(df, feature_name, column, ylim, channel, logger)
            generated_files.append(path)

    write_config()
    write_manifest(generated_files)
    write_notes()

    logger.info(f"Experimento completado. {len(generated_files)} imagenes generadas.")
    logger.info(f"Resultados en: {EXPERIMENT_DIR}")


if __name__ == "__main__":
    main()