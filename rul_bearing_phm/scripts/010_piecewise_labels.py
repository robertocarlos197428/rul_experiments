# scripts/10_piecewise_labels.py
# Generación de etiquetas RUL Piecewise (Fase 5) por rodamiento.
# Lee la tabla maestra y los FPTs previos, asigna meseta horizontal en fase sana y decaimiento lineal post-FPT.
# Exporta tabla etiquetada y gráficos PNG individuales de validación visual con la señal RMS de fondo.

import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

# 1. Definición de rutas base según Guía Maestra (v2)
BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_MASTER = (
    BASE_DIR
    / "results"
    / "exp007_time_features"
    / "features"
    / "tabla_maestra_learning_set.parquet"
)
INPUT_FPT = BASE_DIR / "results" / "exp009_fpt_baseline" / "fpt_por_bearing.parquet"

EXP_DIR = BASE_DIR / "experiments" / "exp010_piecewise_labels"
RES_DIR = BASE_DIR / "results" / "exp010_piecewise_labels"
LOGS_DIR = RES_DIR / "logs"
PLOTS_DIR = RES_DIR / "plots"


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "exp010_piecewise_labels.log"

    logger = logging.getLogger("Exp010Piecewise")
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
        "experiment_id": "exp010_piecewise_labels",
        "description": "Generación de etiquetas RUL piecewise con gráficos de validación duales (RMS + RUL).",
        "parameters": {
            "label_type": "piecewise",
            "healthy_plateau_mode": "max_rul_at_fpt",
        },
        "paths": {
            "input_master": str(INPUT_MASTER.relative_to(BASE_DIR)),
            "input_fpt": str(INPUT_FPT.relative_to(BASE_DIR)),
            "output_dir": str(RES_DIR.relative_to(BASE_DIR)),
        },
    }
    with open(EXP_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_content, f, allow_unicode=True, sort_keys=False)

    # notes.md
    notes_content = """# Bitácora de Experimento: exp010_piecewise_labels

## Objetivo
Construir las etiquetas de Remaining Useful Life (RUL) bajo el enfoque **Piecewise** (tramos) y generar gráficos de validación integrando la señal física (RMS) de fondo junto al RUL resultante.

## Criterios Técnicos
- **Fase Sana (Pre-FPT)**: El RUL se mantiene constante (meseta horizontal) en el valor de vida útil restante desde el momento del FPT.
- **Fase de Degradación (Post-FPT)**: El RUL decrece de forma lineal y proporcional desde el FPT hasta llegar a 0 en el último snapshot del rodamiento.
"""
    with open(EXP_DIR / "notes.md", "w", encoding="utf-8") as f:
        f.write(notes_content)

    # manifest.json
    manifest_content = {
        "experiment_id": "exp010_piecewise_labels",
        "status": "completed",
        "inputs": [
            str(INPUT_MASTER.relative_to(BASE_DIR)),
            str(INPUT_FPT.relative_to(BASE_DIR)),
        ],
        "outputs": [
            str(
                (
                    RES_DIR / "tabla_maestra_learning_set_etiquetada.parquet"
                ).relative_to(BASE_DIR)
            ),
            str(
                (
                    RES_DIR / "tabla_maestra_learning_set_etiquetada.csv"
                ).relative_to(BASE_DIR)
            ),
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
    logger.info("Iniciando experimento exp010_piecewise_labels...")

    # Crear archivos de gobernanza
    create_governance_files()
    logger.info("Archivos de gobernanza verificados/creados con éxito.")

    # Verificar inputs
    if not INPUT_MASTER.exists() or not INPUT_FPT.exists():
        logger.error("No se encontraron los archivos de entrada requeridos.")
        raise FileNotFoundError("Inputs faltantes para exp010.")

    # Cargar datos
    logger.info("Cargando tabla maestra y tabla de FPT...")
    df_master = pd.read_parquet(INPUT_MASTER)
    df_fpt = pd.read_parquet(INPUT_FPT)

    RES_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    processed_dfs = []

    # Procesar rodamiento por rodamiento
    bearings = df_master["bearing_id"].unique()
    logger.info(
        f"Procesando etiquetado piecewise y gráficos para bearings: {list(bearings)}"
    )

    for bearing_id in bearings:
        b_df = df_master[df_master["bearing_id"] == bearing_id].sort_values(
            "timestamp_sec"
        )
        b_df = b_df.reset_index(drop=True)

        # Buscar FPT para este bearing
        fpt_row = df_fpt[df_fpt["bearing_id"] == bearing_id]

        t_min = b_df["timestamp_sec"].min()
        t_max = b_df["timestamp_sec"].max()
        total_vida_horas = (t_max - t_min) / 3600.0

        time_hours = (b_df["timestamp_sec"] - t_min) / 3600.0

        rul_hours = []
        fpt_h = None

        if not fpt_row.empty and not pd.isna(
            fpt_row["FPT_tiempo_horas"].values[0]
        ):
            fpt_h = fpt_row["FPT_tiempo_horas"].values[0]
            max_rul_plateau = total_vida_horas - fpt_h

            for t in time_hours:
                if t <= fpt_h:
                    rul_hours.append(max_rul_plateau)
                else:
                    remaining = total_vida_horas - t
                    rul_hours.append(max(0.0, remaining))
        else:
            logger.warning(
                f"Bearing {bearing_id} sin FPT registrado. Aplicando lineal completo."
            )
            for t in time_hours:
                rul_hours.append(max(0.0, total_vida_horas - t))

        b_df["rul_horas"] = rul_hours
        b_df["rul_hhmm"] = [
            seconds_to_hhmm(r * 3600) for r in b_df["rul_horas"]
        ]

        processed_dfs.append(b_df)

        # Generar gráfico combinado: Arriba Señales RMS y abajo Etiqueta RUL Piecewise
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1]}
        )

        # Panel Superior: Señal RMS (H y V)
        ax1.plot(
            time_hours,
            b_df["h_rms"],
            label="RMS H",
            color="dodgerblue",
            alpha=0.7,
            linewidth=1.2,
        )
        ax1.plot(
            time_hours,
            b_df["v_rms"],
            label="RMS V",
            color="darkorange",
            alpha=0.7,
            linewidth=1.2,
        )
        if fpt_h is not None:
            ax1.axvline(
                fpt_h,
                color="red",
                linestyle="--",
                linewidth=1.5,
                label=f"FPT Detectado ({fpt_h:.2f} h)",
            )
        ax1.set_title(
            f"Validación Integral (RMS + RUL Piecewise) - {bearing_id}"
        )
        ax1.set_ylabel("RMS Amplitude")
        ax1.legend(loc="upper left", fontsize="small")
        ax1.grid(True, linestyle=":", alpha=0.5)

        # Panel Inferior: Etiqueta RUL Piecewise
        ax2.plot(
            time_hours,
            b_df["rul_horas"],
            label="RUL Piecewise (h)",
            color="forestgreen",
            linewidth=2,
        )
        if fpt_h is not None:
            ax2.axvline(
                fpt_h, color="red", linestyle="--", linewidth=1.5, alpha=0.7
            )
        ax2.set_xlabel("Tiempo de operación (horas)")
        ax2.set_ylabel("RUL (horas)")
        ax2.legend(loc="upper right", fontsize="small")
        ax2.grid(True, linestyle=":", alpha=0.5)

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / f"{bearing_id}_rul_piecewise_con_senal.png", dpi=150)
        plt.close()

    # Consolidar dataset final etiquetado
    df_final = pd.concat(processed_dfs, ignore_index=True)

    # Validación estricta
    assert "rul_horas" in df_final.columns, "Falta la columna rul_horas"
    assert "rul_hhmm" in df_final.columns, "Falta la columna rul_hhmm"

    # Exportar resultados
    out_parquet = RES_DIR / "tabla_maestra_learning_set_etiquetada.parquet"
    out_csv = RES_DIR / "tabla_maestra_learning_set_etiquetada.csv"

    df_final.to_parquet(out_parquet, index=False)
    df_final.to_csv(out_csv, index=False)

    logger.info(
        f"Etiquetado completado y exportado exitosamente a:\n- {out_parquet}\n- {out_csv}"
    )
    logger.info(
        f"Gráficos de validación duales guardados en la carpeta: {PLOTS_DIR}"
    )


if __name__ == "__main__":
    main()