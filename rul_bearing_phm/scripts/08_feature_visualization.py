"""
08_feature_visualization.py

Genera visualizaciones exploratorias (series temporales) de las 16
features estadisticas extraidas en exp007, para los 17 rodamientos con
FPT valido (6 de learning_set + 11 de full_test_set).

Por cada feature se generan 3 imagenes (grid, 6+6+5 subplots), agrupadas
segun el dataset de origen y respetando el orden original de aparicion
de los bearing_id (sin reordenar ni mezclar). La escala del eje Y es
global por feature: el minimo/maximo entre los 17 rodamientos manda,
para permitir comparacion directa entre subplots.

Entrada:
    results/exp007_time_features/features/tabla_maestra_learning_set.parquet
    results/exp007_time_features/features/tabla_maestra_full_test_set.parquet

Salida:
    results/exp008_feature_visualization/<feature>/img1_learning_set.png
    results/exp008_feature_visualization/<feature>/img2_full_test_set_a.png
    results/exp008_feature_visualization/<feature>/img3_full_test_set_b.png
    results/exp008_feature_visualization/logs/exp008_feature_visualization.log
    experiments/exp008_feature_visualization/manifest.json

Ejecutar desde la raiz del proyecto con:
    python -m scripts.08_feature_visualization
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import yaml

# ----------------------------------------------------------------------
# Rutas base (seccion 2 de la guia)
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "experiments" / "exp008_feature_visualization" / "config.yaml"
MANIFEST_PATH = BASE_DIR / "experiments" / "exp008_feature_visualization" / "manifest.json"

REQUIRED_COLUMNS = [
    "data_set", "bearing_id", "file_id", "acc_filename",
    "timestamp_sec", "condition",
]


# ----------------------------------------------------------------------
# Logging dual (consola + archivo, seccion 4 de la guia)
# ----------------------------------------------------------------------

def setup_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("exp008_feature_visualization")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ----------------------------------------------------------------------
# Carga y validacion
# ----------------------------------------------------------------------

def cargar_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"No se encontro config.yaml en: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_y_validar(ruta: Path, data_set_label: str, logger: logging.Logger) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontro el archivo de entrada: {ruta}")

    df = pd.read_parquet(ruta)

    faltantes = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"El archivo {ruta.name} no tiene las columnas esperadas: {faltantes}"
        )

    if "data_set" not in df.columns or df["data_set"].isna().all():
        df["data_set"] = data_set_label

    df["tiempo_horas"] = df["timestamp_sec"] / 3600.0

    logger.info(f"Cargado {ruta.name}: {len(df)} filas, "
                f"{df['bearing_id'].nunique()} bearings unicos")

    return df


# ----------------------------------------------------------------------
# Graficos
# ----------------------------------------------------------------------

def graficar_grupo(df: pd.DataFrame, bearings: list, feature: str,
                    output_path: Path, ylim: tuple,
                    n_filas: int, n_cols: int, logger: logging.Logger) -> str:
    fig, axes = plt.subplots(n_filas, n_cols, figsize=(5 * n_cols, 4 * n_filas),
                              squeeze=False)
    axes_flat = axes.flatten()

    for i, bearing_id in enumerate(bearings):
        ax = axes_flat[i]
        sub = df[df["bearing_id"] == bearing_id]
        ax.plot(sub["tiempo_horas"], sub[feature], linewidth=0.8)
        ax.set_title(bearing_id)
        ax.set_xlabel("Tiempo (horas)")
        ax.set_ylabel(feature)
        ax.set_ylim(ylim)

    for j in range(len(bearings), len(axes_flat)):
        axes_flat[j].axis("off")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=120)
    plt.close(fig)

    logger.info(f"  Guardado: {output_path.relative_to(BASE_DIR)}")
    return str(output_path.relative_to(BASE_DIR))


def procesar_feature(feature: str, df_learning: pd.DataFrame, df_full: pd.DataFrame,
                      bearings_learning: list, bearings_full_a: list, bearings_full_b: list,
                      output_dir: Path, logger: logging.Logger) -> list:
    logger.info(f"Procesando feature: {feature}")

    valor_min = min(df_learning[feature].min(), df_full[feature].min())
    valor_max = max(df_learning[feature].max(), df_full[feature].max())
    ylim = (valor_min, valor_max)
    logger.info(f"  Escala Y global: {ylim}")

    feature_dir = output_dir / feature
    outputs = []

    outputs.append(graficar_grupo(
        df_learning, bearings_learning, feature,
        feature_dir / "img1_learning_set.png", ylim, 2, 3, logger,
    ))
    outputs.append(graficar_grupo(
        df_full, bearings_full_a, feature,
        feature_dir / "img2_full_test_set_a.png", ylim, 2, 3, logger,
    ))
    outputs.append(graficar_grupo(
        df_full, bearings_full_b, feature,
        feature_dir / "img3_full_test_set_b.png", ylim, 2, 3, logger,
    ))

    return outputs


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    config = cargar_config()

    output_dir = BASE_DIR / config["paths"]["output_dir"]
    log_path = BASE_DIR / config["paths"]["log_file"]
    features_dir = BASE_DIR / config["paths"]["features_dir"]

    logger = setup_logging(log_path)
    logger.info("=== Inicio exp008_feature_visualization ===")

    manifest = {
        "experiment_id": config["experiment_id"],
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "inputs": [],
        "outputs": [],
        "metrics": {},
        "errors": [],
    }

    try:
        ruta_learning = features_dir / config["paths"]["input_files"]["learning_set"]
        ruta_full = features_dir / config["paths"]["input_files"]["full_test_set"]

        df_learning = cargar_y_validar(ruta_learning, "learning_set", logger)
        df_full = cargar_y_validar(ruta_full, "full_test_set", logger)

        manifest["inputs"] = [
            str(ruta_learning.relative_to(BASE_DIR)),
            str(ruta_full.relative_to(BASE_DIR)),
        ]

        bearings_learning = list(pd.unique(df_learning["bearing_id"]))
        bearings_full = list(pd.unique(df_full["bearing_id"]))

        logger.info(f"Bearings learning_set ({len(bearings_learning)}): {bearings_learning}")
        logger.info(f"Bearings full_test_set ({len(bearings_full)}): {bearings_full}")

        val_cfg = config["validation"]
        if len(bearings_learning) != config["grouping"]["learning_set"]["expected_count"]:
            logger.warning(
                f"Se esperaban {config['grouping']['learning_set']['expected_count']} "
                f"bearings en learning_set, se encontraron {len(bearings_learning)}"
            )
        if len(bearings_full) != 11:
            logger.warning(f"Se esperaban 11 bearings en full_test_set, "
                          f"se encontraron {len(bearings_full)}")

        total_bearings = len(bearings_learning) + len(bearings_full)
        if total_bearings != val_cfg["expected_total_bearings"]:
            logger.warning(
                f"Total de bearings ({total_bearings}) distinto del esperado "
                f"({val_cfg['expected_total_bearings']})"
            )

        bearings_full_a = bearings_full[:6]
        bearings_full_b = bearings_full[6:]

        features = config["features"]
        logger.info(f"Total de features a procesar: {len(features)}")

        all_outputs = []
        for feature in features:
            outputs = procesar_feature(
                feature, df_learning, df_full,
                bearings_learning, bearings_full_a, bearings_full_b,
                output_dir, logger,
            )
            all_outputs.extend(outputs)

        manifest["outputs"] = all_outputs
        manifest["metrics"] = {
            "features_procesadas": len(features),
            "imagenes_generadas": len(all_outputs),
            "bearings_learning_set": len(bearings_learning),
            "bearings_full_test_set": len(bearings_full),
            "total_bearings": total_bearings,
        }
        manifest["status"] = "completed"
        logger.info(f"=== Completado: {len(all_outputs)} imagenes generadas ===")

    except Exception as e:
        manifest["status"] = "failed"
        manifest["errors"].append(str(e))
        logger.error(f"Fallo la ejecucion: {e}")
        raise

    finally:
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f"Manifest guardado en: {MANIFEST_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()