# scripts/09_fpt_baseline_rms.py
# Detección de Failure Point Transition (FPT) por baseline de RMS (Canales H y V)
# Lee la tabla maestra del learning set, calcula umbrales estadísticos en ventana sana y detecta cruce sostenido.
# Genera tabla resumen, gráficos por bearing y archivos de gobernanza del experimento.

import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# 1. Definición de rutas base según Guía Maestra (v2)
BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    BASE_DIR
    / "results"
    / "exp007_time_features"
    / "features"
    / "tabla_maestra_learning_set.parquet"
)
EXP_DIR = BASE_DIR / "experiments" / "exp009_fpt_baseline"
RES_DIR = BASE_DIR / "results" / "exp009_fpt_baseline"
LOGS_DIR = RES_DIR / "logs"
PLOTS_DIR = RES_DIR / "plots"


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "exp009_fpt_baseline.log"

    logger = logging.getLogger("Exp009FPT")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Consola
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # Archivo
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    return logger


def create_governance_files():
    EXP_DIR.mkdir(parents=True, exist_ok=True)

    # config.yaml
    config_content = {
        "experiment_id": "exp009_fpt_baseline",
        "description": "Detección de FPT basado en RMS (canales H y V) usando ventana sana inicial y criterio de sostenimiento.",
        "parameters": {
            "healthy_window_pct": 0.10,
            "std_multiplier": 3.0,
            "sustain_windows": 10,
            "channels": ["h_rms", "v_rms"],
        },
        "paths": {
            "input_table": str(INPUT_PATH.relative_to(BASE_DIR)),
            "output_dir": str(RES_DIR.relative_to(BASE_DIR)),
        },
    }
    with open(EXP_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_content, f, allow_unicode=True, sort_keys=False)

    # notes.md
    notes_content = """# Bitácora de Experimento: exp009_fpt_baseline

## Objetivo
Detectar el Failure Point Transition (FPT) para cada bearing del learning set utilizando una baseline estadística sobre los canales de RMS horizontal (`h_rms`) y vertical (`v_rms`).

## Criterios Técnicos
- **Ventana Sana**: Primer 10% de los snapshots ordenados cronológicamente por bearing.
- **Umbral**: $\\text{media} + 3 \\times \\text{std}$ calculada en la ventana sana.
- **Cruce Sostenido**: El primer punto donde RMS supera el umbral y se mantiene durante 10 ventanas consecutivas.
- **Métricas**: Índice de FPT, tiempo total de vida, FPT en horas y formato HH:MM, además del porcentaje de vida sana.
"""
    with open(EXP_DIR / "notes.md", "w", encoding="utf-8") as f:
        f.write(notes_content)

    # manifest.json
    manifest_content = {
        "experiment_id": "exp009_fpt_baseline",
        "status": "completed",
        "inputs": [str(INPUT_PATH.relative_to(BASE_DIR))],
        "outputs": [
            str((RES_DIR / "fpt_por_bearing.parquet").relative_to(BASE_DIR)),
            str((RES_DIR / "fpt_por_bearing.csv").relative_to(BASE_DIR)),
        ],
    }
    with open(EXP_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_content, f, indent=4, ensure_ascii=False)


def seconds_to_hhmm(seconds):
    if pd.isna(seconds) or seconds < 0:
        return "N/A"
    total_minutes = int(round(seconds / 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def main():
    logger = setup_logging()
    logger.info("Iniciando experimento exp009_fpt_baseline...")

    # Crear archivos de gobernanza
    create_governance_files()
    logger.info(
        "Archivos de gobernanza (config.yaml, notes.md, manifest.json) verificados/creados."
    )

    # Verificar existencia de input
    if not INPUT_PATH.exists():
        logger.error(f"No se encontró la tabla maestra en: {INPUT_PATH}")
        raise FileNotFoundError(f"Archivo no encontrado: {INPUT_PATH}")

    # Cargar datos
    logger.info(f"Cargando tabla maestra desde {INPUT_PATH}...")
    df = pd.read_parquet(INPUT_PATH)
    logger.info(f"Datos cargados correctamente. Shape: {df.shape}")

    # Crear directorios de resultados
    RES_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    # Procesar por bearing
    bearings = df["bearing_id"].unique()
    logger.info(f"Bearings encontrados para procesar: {list(bearings)}")

    for bearing_id in bearings:
        b_df = df[df["bearing_id"] == bearing_id].sort_values("timestamp_sec")
        b_df = b_df.reset_index(drop=True)

        total_snapshots = len(b_df)
        if total_snapshots == 0:
            continue

        # Tiempo total de vida en horas (asumiendo timestamp_sec en segundos)
        t_min = b_df["timestamp_sec"].min()
        t_max = b_df["timestamp_sec"].max()
        vida_total_horas = (t_max - t_min) / 3600.0
        if vida_total_horas == 0:
            vida_total_horas = 1e-6  # Evitar división por cero

        # Definir ventana sana (primer 10%)
        healthy_limit_idx = max(1, int(total_snapshots * 0.10))
        healthy_window = b_df.iloc[:healthy_limit_idx]

        # Calcular umbrales por canal
        thresholds = {}
        means = {}
        stds = {}
        for channel in ["h_rms", "v_rms"]:
            mean_val = healthy_window[channel].mean()
            std_val = healthy_window[channel].std()
            means[channel] = mean_val
            stds[channel] = std_val
            thresholds[channel] = mean_val + 3.0 * std_val

        # Buscar cruce sostenido (10 ventanas consecutivas)
        fpt_idx = None
        fpt_tiempo_horas = None
        canal_detector = None
        umbral_usado = None

        sustain_req = 10

        # Evaluamos canal H y V de forma independiente buscando el primer cruce válido
        for idx, row in b_df.iterrows():
            # Verificar H
            if row["h_rms"] > thresholds["h_rms"]:
                # Revisar si se sostiene por las siguientes 10 ventanas
                if idx + sustain_req <= total_snapshots:
                    sub_window = b_df.loc[idx : idx + sustain_req - 1]
                    if (sub_window["h_rms"] > thresholds["h_rms"]).all():
                        fpt_idx = int(idx)
                        fpt_tiempo_horas = (
                            row["timestamp_sec"] - t_min
                        ) / 3600.0
                        canal_detector = "H"
                        umbral_usado = thresholds["h_rms"]
                        break

            # Verificar V
            if row["v_rms"] > thresholds["v_rms"]:
                if idx + sustain_req <= total_snapshots:
                    sub_window = b_df.loc[idx : idx + sustain_req - 1]
                    if (sub_window["v_rms"] > thresholds["v_rms"]).all():
                        # Si H ya detectó antes, nos quedamos con el menor índice cronológico
                        if fpt_idx is None or idx < fpt_idx:
                            fpt_idx = int(idx)
                            fpt_tiempo_horas = (
                                row["timestamp_sec"] - t_min
                            ) / 3600.0
                            canal_detector = "V"
                            umbral_usado = thresholds["v_rms"]
                            break

        # Métricas derivadas
        if fpt_idx is not None:
            pct_vida_sana = (fpt_tiempo_horas / vida_total_horas) * 100.0
            fpt_tiempo_hhmm = seconds_to_hhmm(fpt_tiempo_horas * 3600)
        else:
            pct_vida_sana = np.nan
            fpt_tiempo_hhmm = "N/A"
            fpt_tiempo_horas = np.nan

        vida_total_hhmm = seconds_to_hhmm(vida_total_horas * 3600)

        results.append(
            {
                "bearing_id": bearing_id,
                "canal_detector": canal_detector
                if canal_detector
                else "Ninguno",
                "FPT_index": fpt_idx if fpt_idx is not None else np.nan,
                "FPT_tiempo_horas": fpt_tiempo_horas,
                "FPT_tiempo_hhmm": fpt_tiempo_hhmm,
                "vida_total_horas": vida_total_horas,
                "vida_total_hhmm": vida_total_hhmm,
                "pct_vida_sana": pct_vida_sana,
                "umbral_usado": umbral_usado
                if umbral_usado is not None
                else np.nan,
            }
        )

        logger.info(
            f"Bearing {bearing_id}: FPT Index = {fpt_idx}, Canal = {canal_detector}, FPT Horas = {fpt_tiempo_horas}"
        )

        # Generar gráfico de diagnóstico
        plt.figure(figsize=(10, 4))
        time_hours = (b_df["timestamp_sec"] - t_min) / 3600.0
        plt.plot(
            time_hours,
            b_df["h_rms"],
            label="RMS_H",
            alpha=0.7,
            color="dodgerblue",
        )
        plt.axhline(
            thresholds["h_rms"],
            color="blue",
            linestyle="--",
            label=f"Umbral H ({thresholds['h_rms']:.3f})",
        )

        plt.plot(
            time_hours,
            b_df["v_rms"],
            label="RMS_V",
            alpha=0.7,
            color="darkorange",
        )
        plt.axhline(
            thresholds["v_rms"],
            color="darkorange",
            linestyle="--",
            label=f"Umbral V ({thresholds['v_rms']:.3f})",
        )

        if fpt_tiempo_horas is not None:
            plt.axvline(
                fpt_tiempo_horas,
                color="red",
                linestyle="-",
                label=f"FPT ({fpt_tiempo_horas:.2f} h)",
            )

        plt.title(f"Detección FPT - {bearing_id}")
        plt.xlabel("Tiempo (horas)")
        plt.ylabel("RMS")
        plt.legend(loc="upper left", fontsize="small")
        plt.tight_layout()
        plt.savefig(PLOTS_DIR / f"{bearing_id}_fpt_rms.png", dpi=150)
        plt.close()

    # Consolidar resultados en DataFrame
    df_results = pd.DataFrame(results)

    # Validación estricta antes de exportar
    expected_columns = [
        "bearing_id",
        "canal_detector",
        "FPT_index",
        "FPT_tiempo_horas",
        "FPT_tiempo_hhmm",
        "vida_total_horas",
        "vida_total_hhmm",
        "pct_vida_sana",
        "umbral_usado",
    ]
    for col in expected_columns:
        if col not in df_results.columns:
            raise ValueError(
                f"Validación estricta fallida: falta la columna {col}"
            )

    # Exportar salidas
    out_parquet = RES_DIR / "fpt_por_bearing.parquet"
    out_csv = RES_DIR / "fpt_por_bearing.csv"

    df_results.to_parquet(out_parquet, index=False)
    df_results.to_csv(out_csv, index=False)

    logger.info(f"Resultados exportados exitosamente a:\n- {out_parquet}\n- {out_csv}")
    logger.info("Experimento exp009_fpt_baseline finalizado con éxito.")


if __name__ == "__main__":
    main()