"""
015_hi3_smoothing_families_learning.py

Experimento: exp015_hi3_smoothing_families_learning
Tipo: EXPLORACION INFORMAL - Evaluacion de suavizado sobre hi3

Nueva definicion: Mon(y)=1 - N-/(K-1) donde N-=count(dy<0)
Mide "nunca baja" que es lo relevante para FPT. A y C = 1.0 por construccion.

Familias:
    raw: hi3 crudo
    A: cummax(hi3)
    B: EWMA(hi3, alpha=0.1)
    C: cummax(EWMA(hi3))

Metricas:
    Monotonicity: Mon(y)=1 - N-/(K-1)
    Separabilidad: Sep(y)=mean(last 5%)/mean(first 10%)
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
# RUTAS
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(r"escribe aqui tu ruta")
FEATURES_DIR = PROJECT_ROOT / "results" / "exp007_time_features" / "features"
LEARNING_PARQUET = FEATURES_DIR / "tabla_maestra_learning_set.parquet"

EXPERIMENT_NAME = "exp015_hi3_smoothing_families_learning"
EXPERIMENT_DIR = PROJECT_ROOT / "experiments" / EXPERIMENT_NAME
RESULTS_DIR = PROJECT_ROOT / "results" / EXPERIMENT_NAME
FIGURES_DIR = RESULTS_DIR / "figures"
METRICS_DIR = RESULTS_DIR / "metrics"
LOG_DIR = RESULTS_DIR / "log"

FEATURE_BASENAMES = ["rms", "std", "peak"]
HEALTHY_WINDOW_FRACTION = 0.10
PERCENTILE_MAX = 99
EWMA_ALPHA = 0.1

# ----------------------------------------------------------------------
# SETUP
# ----------------------------------------------------------------------

def setup_dirs():
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
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

def load_data(logger):
    logger.info(f"Cargando Learning_set desde: {LEARNING_PARQUET}")
    df = pd.read_parquet(LEARNING_PARQUET)
    df["hours"] = df["timestamp_sec"] / 3600.0
    logger.info(f"Bearings: {df['bearing_id'].unique().tolist()}")
    return df

def ordered_bearings(df):
    seen = []
    for b in df["bearing_id"]:
        if b not in seen:
            seen.append(b)
    return seen

# ----------------------------------------------------------------------
# NORMALIZACION Y hi3
# ----------------------------------------------------------------------

def normalize_feature(series):
    n = len(series)
    n_healthy = max(1, int(np.ceil(n * HEALTHY_WINDOW_FRACTION)))
    x_min = series.iloc[:n_healthy].mean()
    x_max = np.percentile(series, PERCENTILE_MAX)
    denom = x_max - x_min if (x_max - x_min) != 0 else 1e-9
    return ((series - x_min) / denom).clip(lower=0.0, upper=1.0)

def compute_hi3(df_bearing):
    df_bearing = df_bearing.sort_values("hours").reset_index(drop=True).copy()
    norm_cols = {}
    for base in FEATURE_BASENAMES:
        for prefix in ["h_", "v_"]:
            col = f"{prefix}{base}"
            if col in df_bearing.columns:
                norm_cols[col] = normalize_feature(df_bearing[col])
    norm_df = pd.DataFrame(norm_cols)
    df_bearing["hi3_raw"] = norm_df.mean(axis=1)
    df_bearing["hi3_A"] = df_bearing["hi3_raw"].cummax()
    df_bearing["hi3_B"] = df_bearing["hi3_raw"].ewm(alpha=EWMA_ALPHA, adjust=False).mean()
    df_bearing["hi3_C"] = df_bearing["hi3_B"].cummax()
    return df_bearing

# ----------------------------------------------------------------------
# METRICAS CORREGIDAS
# ----------------------------------------------------------------------

def monotonicity_corrected(series):
    """
    CORREGIDA: Mon(y) = 1 - N-/(K-1)
    N- = count(dy < 0)
    Si nunca baja, Mon=1.0. Cummax siempre 1.0
    """
    diff = np.diff(series.values)
    n_minus = np.sum(diff < 0)
    k = len(series)
    if k <= 1:
        return 1.0
    return 1.0 - (n_minus / (k - 1))

def separability(series):
    n = len(series)
    n_first = max(1, int(np.ceil(n * 0.10)))
    n_last = max(1, int(np.ceil(n * 0.05)))
    mean_first = series.iloc[:n_first].mean()
    mean_last = series.iloc[-n_last:].mean()
    if mean_first == 0:
        return np.nan
    return mean_last / mean_first

def compute_metrics(df_hi, bearing_order, logger):
    rows = []
    for bearing in bearing_order:
        sub = df_hi[df_hi["bearing_id"] == bearing]
        row = {"bearing_id": bearing}
        for variant in ["hi3_raw", "hi3_A", "hi3_B", "hi3_C"]:
            row[f"Mon_{variant}"] = monotonicity_corrected(sub[variant])
            row[f"Sep_{variant}"] = separability(sub[variant])
        rows.append(row)
    
    df_metrics = pd.DataFrame(rows)
    df_table = pd.DataFrame({
        "bearing_id": df_metrics["bearing_id"],
        "Mon_raw": df_metrics["Mon_hi3_raw"],
        "Mon_A": df_metrics["Mon_hi3_A"],
        "Mon_B": df_metrics["Mon_hi3_B"],
        "Mon_C": df_metrics["Mon_hi3_C"],
        "Sep_raw": df_metrics["Sep_hi3_raw"],
        "Sep_A": df_metrics["Sep_hi3_A"],
        "Sep_B": df_metrics["Sep_hi3_B"],
        "Sep_C": df_metrics["Sep_hi3_C"],
    })
    logger.info(f"\n{df_table}")
    return df_table

# ----------------------------------------------------------------------
# GRAFICOS
# ----------------------------------------------------------------------

def plot_comparison(df_hi, bearing_order, logger):
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharex=False, sharey=True)
    axes = axes.flatten()
    
    for i, bearing in enumerate(bearing_order):
        if i >= len(axes):
            break
        ax = axes[i]
        sub = df_hi[df_hi["bearing_id"] == bearing].sort_values("hours")
        ax.plot(sub["hours"], sub["hi3_raw"], linewidth=1, label="raw", color="#7f7f7f", alpha=0.7)
        ax.plot(sub["hours"], sub["hi3_A"], linewidth=1.2, label="A: cummax(hi3)", color="tab:blue")
        ax.plot(sub["hours"], sub["hi3_B"], linewidth=1.2, label="B: EWMA(a=0.1)", color="tab:green")
        ax.plot(sub["hours"], sub["hi3_C"], linewidth=1.2, label="C: cummax(EWMA)", color="tab:red")
        ax.set_title(f"{bearing}", fontsize=10)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Tiempo (horas)")
        ax.set_ylabel("hi3")
        ax.grid(True, alpha=0.3)
        if i == 0:
            ax.legend(fontsize=8, loc="upper left")

    fig.suptitle("Exp015 - hi3: raw vs 3 familias de suavizado (Learning_set only)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = FIGURES_DIR / "hi_smoothing_comparison_learning_01.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    logger.info(f"Guardado: {out}")
    return out

def plot_table_jpg(df_table, logger):
    fig = plt.figure(figsize=(14, 4.5))
    ax = plt.subplot(111)
    ax.axis('off')

    headers = [
        "bearing_id",
        r"Mon_raw" + "\n" + r"$Mon=1-\frac{N_{-}}{K-1}$",
        r"Mon_A" + "\n" + r"$cummax(hi3)$",
        r"Mon_B" + "\n" + r"$EWMA_{\alpha=0.1}$",
        r"Mon_C" + "\n" + r"$cummax(EWMA)$",
        r"Sep_raw" + "\n" + r"$Sep=\frac{\mu_{last5\%}}{\mu_{first10\%}}$",
        r"Sep_A" + "\n" + r"$Sep=\frac{\mu_{last5\%}}{\mu_{first10\%}}$",
        r"Sep_B" + "\n" + r"$Sep=\frac{\mu_{last5\%}}{\mu_{first10\%}}$",
        r"Sep_C" + "\n" + r"$Sep=\frac{\mu_{last5\%}}{\mu_{first10\%}}$",
    ]

    table_data = []
    for _, row in df_table.iterrows():
        table_data.append([
            row["bearing_id"],
            f"{row['Mon_raw']:.3f}",
            f"{row['Mon_A']:.3f}",
            f"{row['Mon_B']:.3f}",
            f"{row['Mon_C']:.3f}",
            f"{row['Sep_raw']:.2f}",
            f"{row['Sep_A']:.2f}",
            f"{row['Sep_B']:.2f}",
            f"{row['Sep_C']:.2f}",
        ])

    table = ax.table(
        cellText=table_data,
        colLabels=headers,
        loc='center',
        cellLoc='center',
        colLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.2)

    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_text_props(weight='bold', color='white')
        cell.set_facecolor('#1F3A3A')

    title_text = (
        "Exp015 - Tabla 1: Monotonicity y Separabilidad por bearing (Learning_set only) - CORREGIDA\n"
        r"Monotonicity: $Mon(y)=1-\frac{N_{-}}{K-1}$, $N_{-}=count(\Delta y<0)$  |  "
        r"Separabilidad: $Sep(y)=\frac{\mu(y_{last5\%})}{\mu(y_{first10\%})}$"
    )
    plt.title(title_text, fontsize=10, pad=20, loc='left')
    plt.tight_layout()
    out = FIGURES_DIR / "tabla1_monotonicity_separabilidad.jpg"
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Guardado tabla JPG: {out}")
    return out

# ----------------------------------------------------------------------
# TRAZABILIDAD
# ----------------------------------------------------------------------

def write_config(bearing_order):
    config = {
        "experiment_name": EXPERIMENT_NAME,
        "script": "015_hi3_smoothing_families_learning.py",
        "type": "exploracion_informal_capa_1_corregida",
        "input_parquet": str(LEARNING_PARQUET),
        "bearings_order": bearing_order,
        "decision_scope": "Learning_set only",
        "hi_variant": "hi3",
        "hi3_features": [f"{p}{b}" for b in FEATURE_BASENAMES for p in ["h_", "v_"]],
        "healthy_window_fraction": HEALTHY_WINDOW_FRACTION,
        "percentile_max": PERCENTILE_MAX,
        "families": {
            "raw": "hi3_raw",
            "A": "cummax(hi3_raw)",
            "B": f"EWMA(alpha={EWMA_ALPHA})",
            "C": f"cummax(EWMA(alpha={EWMA_ALPHA}))"
        },
        "metrics": {
            "Mon_corrected": "Mon(y)=1 - N-/(K-1), N-=count(dy<0), A y C =1.0 por construccion",
            "Sep": "Sep(y)=mean(last 5%)/mean(first 10%)"
        },
        "correction_note": "Mon original |N+-N-|/(K-1) penalizaba planos de cummax. Corregida a 1-N-/(K-1)",
        "clip_range": [0, 1],
    }
    with open(EXPERIMENT_DIR / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)

def write_manifest(files):
    manifest = {
        "experiment_name": EXPERIMENT_NAME,
        "timestamp": datetime.now().isoformat(),
        "input_parquet": str(LEARNING_PARQUET),
        "correction": "Monotonicity corregida a 1 - N-/(K-1)",
        "outputs": [str(p) for p in files],
    }
    with open(EXPERIMENT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def write_notes():
    notes = f"""# {EXPERIMENT_NAME} - CORREGIDO

## Correccion critica
Mon original Mon=|N+-N-|/(K-1) daba 0.01 para cummax porque penalizaba diffs=0 (plateaus).
cummax sube en escalones: 30 subidas y 2770 planos -> 30/2800=0.01

Nueva formula: Mon(y)=1 - N-/(K-1), N-=count(dy<0)
- Mide "nunca baja" que es lo relevante para FPT
- A y C = 1.0 por construccion

## Familias sobre hi3
- raw: hi3 crudo
- A: cummax(hi3) - Mon=1.0 garantizado
- B: EWMA(hi3, alpha=0.1)
- C: cummax(EWMA) - Mon=1.0 garantizado

hi3 = promedio de 6 columnas: h_rms, v_rms, h_std, v_std, h_peak, v_peak

## Salidas
- hi_smoothing_comparison_learning_01.png
- tabla1_monotonicity_separabilidad.jpg con formula corregida arriba
- monotonicity_separabilidad.csv
"""
    with open(EXPERIMENT_DIR / "notes.md", "w", encoding="utf-8") as f:
        f.write(notes)

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    setup_dirs()
    logger = setup_logging()
    logger.info(f"Inicio: {EXPERIMENT_NAME} - CORREGIDO")

    df = load_data(logger)
    bearing_order = ordered_bearings(df)

    logger.info("Calculando hi3 y familias A,B,C...")
    hi_frames = []
    for b in bearing_order:
        hi_frames.append(compute_hi3(df[df["bearing_id"] == b]))
    df_hi = pd.concat(hi_frames, ignore_index=True)

    fig1 = plot_comparison(df_hi, bearing_order, logger)
    df_metrics = compute_metrics(df_hi, bearing_order, logger)

    csv_path = METRICS_DIR / "monotonicity_separabilidad.csv"
    df_metrics.to_csv(csv_path, index=False)
    logger.info(f"Guardado CSV: {csv_path}")

    fig2 = plot_table_jpg(df_metrics, logger)

    write_config(bearing_order)
    write_manifest([fig1, fig2, csv_path])
    write_notes()

    logger.info("Completado corregido. A y C deben dar Mon=1.0")

if __name__ == "__main__":
    main()