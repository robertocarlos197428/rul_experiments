"""
07_build_time_features.py - exp007
Crea 3 tablas maestras (learning/test/full_test) desde FEMTO.
Entrada: data/processed/FEMTO/*/Bearing*/acc_*.csv (H,V).
Salida: 22 cols [data_set,bearing_id,file_id,acc_filename,timestamp_sec,condition + 16 time_features].
Features (8): mean, std, rms, peak_to_peak, peak, crest_factor, kurtosis, skewness
Guarda: results/exp007_time_features/features/*.parquet y.csv + config/manifest/notes en experiments/.
"""

from pathlib import Path
import json
import logging
import sys
from datetime import datetime
import yaml
import pandas as pd
import numpy as np

# --- SETUP BASE ---
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from src.features.features_time_domain import extract_time_features

EXP_ID = "exp007_time_features"

# Rutas
EXP_DIR = BASE_DIR / f"experiments/{EXP_ID}"
RESULTS_DIR = BASE_DIR / f"results/{EXP_ID}"
FEATURES_DIR = RESULTS_DIR / "features"
LOGS_DIR = RESULTS_DIR / "logs"

FEMTO_BASE = BASE_DIR / "data" / "processed" / "FEMTO"
DATA_SETS = ["learning_set", "test_set", "full_test_set"]

for d in [EXP_DIR, RESULTS_DIR, FEATURES_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- LOGGING ---
log_file = LOGS_DIR / f"{EXP_ID}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- 1. CONFIG.YAML ---
config_content = {
    "experiment_id": EXP_ID,
    "description": "8 features tiempo x 2 ejes = 16 + 6 identificación = 22 cols",
    "data": {
        "input_base": str(FEMTO_BASE.relative_to(BASE_DIR)).replace("\\", "/"),
        "data_sets": DATA_SETS,
        "sampling_rate": 25600,
        "points_per_file": 2560,
        "interval_sec": 10,
        "acc_file_columns": 6,
        "h_col_index": 4,
        "v_col_index": 5
    },
    "features": {
        "identification_cols": ["data_set", "bearing_id", "file_id", "acc_filename", "timestamp_sec", "condition"],
        "axes": ["h", "v"],
        "n_base_formulas": 8,
        "total_features": 16,
        "std_ddof": 1,
        "peak_definition": "max_abs",
        "kurtosis_type": "fisher",
        "kurtosis_bias": False,
        "skewness_bias": False,
        "list": ["mean", "std", "rms", "peak_to_peak", "peak", "crest_factor", "kurtosis", "skewness"]
    },
    "output": {
        "output_dir": f"results/{EXP_ID}/features",
        "files": 6,
        "columns": 22,
        "naming": "tabla_maestra_{data_set}.parquet/csv",
        "formats": ["parquet", "csv"]
    }
}

config_path = EXP_DIR / "config.yaml"
with open(config_path, "w", encoding="utf-8") as f:
    yaml.dump(config_content, f, sort_keys=False, allow_unicode=True)
logger.info(f"1/4 config.yaml -> {config_path}")

# --- 2. MANIFEST.JSON ---
manifest_content = {
    "experiment_id": EXP_ID,
    "created_at": datetime.now().isoformat(),
    "script": "scripts/07_build_time_features.py",
    "module": "src/features/features_time_domain.py",
    "inputs": {
        "femto_base": str(FEMTO_BASE),
        "data_sets": DATA_SETS
    },
    "outputs": {
        "features_dir": str(FEATURES_DIR),
        "log": str(log_file.relative_to(BASE_DIR))
    },
    "parameters": config_content["features"],
    "status": "pending"
}

manifest_path = EXP_DIR / "manifest.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest_content, f, indent=2, ensure_ascii=False)
logger.info(f"2/4 manifest.json -> {manifest_path}")

# --- 3. NOTES.MD ---
notes_content = f"""# {EXP_ID} - Notas

## Objetivo
Extraer 16 features de dominio tiempo (8 fórmulas x H,V) para baseline RUL.

## Ruta entrada
`data/processed/FEMTO/{{learning_set,test_set,full_test_set}}/Bearing*/acc_*.csv`

Formato acc: 6 columnas [?,?,?,?, H, V] - H col 4, V col 5 (index 4,5)

## Columnas identificación (6)
1. data_set - learning_set / test_set / full_test_set
2. bearing_id - Bearing1_1
3. file_id - índice 0..N
4. acc_filename - acc_00001.csv
5. timestamp_sec - file_id * 10
6. condition - Bearing1, Bearing2, Bearing3

## Features (8 base)
mean, std, rms, peak_to_peak, peak, crest_factor, kurtosis, skewness

## Salida
`results/{EXP_ID}/features/` SOLO tablas:
- tabla_maestra_learning_set.parquet /.csv
- tabla_maestra_test_set.parquet /.csv
- tabla_maestra_full_test_set.parquet /.csv

Total 6 archivos, 22 columnas cada uno.

Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

notes_path = EXP_DIR / "notes.md"
with open(notes_path, "w", encoding="utf-8") as f:
    f.write(notes_content)
logger.info(f"3/4 notes.md -> {notes_path}")

# --- 4. CONSTRUIR 3 TABLAS ---
logger.info(f"4/4 Construyendo tablas desde {FEMTO_BASE}")

all_rows_by_dataset = {ds: [] for ds in DATA_SETS}

if not FEMTO_BASE.exists():
    logger.error(f"NO EXISTE {FEMTO_BASE}")
    raise FileNotFoundError(f"No existe {FEMTO_BASE}")

for data_set in DATA_SETS:
    ds_path = FEMTO_BASE / data_set
    if not ds_path.exists():
        logger.warning(f"No existe {ds_path}, se omite")
        continue

    bearing_dirs = [d for d in ds_path.iterdir() if d.is_dir()]
    logger.info(f"[{data_set}] {len(bearing_dirs)} bearings")

    for bearing_dir in bearing_dirs:
        acc_files = sorted(bearing_dir.glob("acc_*.csv"))
        if not acc_files:
            continue

        bearing_id = bearing_dir.name
        condition = bearing_id.split("_")[0] if "_" in bearing_id else bearing_id

        for file_id, acc_file in enumerate(acc_files):
            try:
                # FIX CRÍTICO: archivo tiene 6 cols, H y V son las últimas 2
                data = np.loadtxt(acc_file, delimiter=",")
                if data.ndim == 2 and data.shape[1] >= 6:
                    sig_h = data[:, 4]
                    sig_v = data[:, 5]
                elif data.ndim == 2 and data.shape[1] >= 2:
                    # fallback si algún día es solo H,V
                    sig_h = data[:, 0]
                    sig_v = data[:, 1]
                else:
                    sig_h = data
                    sig_v = data

                feat = extract_time_features(
                    sig_h, sig_v,
                    std_ddof=1,
                    peak_definition="max_abs",
                    kurtosis_type="fisher",
                    skewness_bias=False,
                    kurtosis_bias=False
                )

                row = {
                    "data_set": data_set,
                    "bearing_id": bearing_id,
                    "file_id": file_id,
                    "acc_filename": acc_file.name,
                    "timestamp_sec": file_id * 10,
                    "condition": condition,
                    **feat
                }
                all_rows_by_dataset[data_set].append(row)
            except Exception as e:
                logger.error(f"Error {acc_file}: {e}")

# Guardar 6 tablas con nombre tabla_maestra_
for data_set in DATA_SETS:
    rows = all_rows_by_dataset[data_set]
    if not rows:
        logger.warning(f"[{data_set}] sin filas")
        continue

    df = pd.DataFrame(rows)
    id_cols = ["data_set", "bearing_id", "file_id", "acc_filename", "timestamp_sec", "condition"]
    feat_cols = [c for c in df.columns if c not in id_cols]
    feat_cols_sorted = sorted(feat_cols)
    df = df[id_cols + feat_cols_sorted]

    parquet_path = FEATURES_DIR / f"tabla_maestra_{data_set}.parquet"
    csv_path = FEATURES_DIR / f"tabla_maestra_{data_set}.csv"

    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)

    logger.info(f"[{data_set}] -> {parquet_path.name} {df.shape} | {csv_path.name}")

# Actualizar manifest
manifest_content["status"] = "completed"
manifest_content["completed_at"] = datetime.now().isoformat()
manifest_content["output"] = {ds: len(all_rows_by_dataset[ds]) for ds in DATA_SETS}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest_content, f, indent=2, ensure_ascii=False)

print(f"\n=== {EXP_ID} LISTO ===")
print(f"Tablas en: {FEATURES_DIR}")
for ds in DATA_SETS:
    print(f" - tabla_maestra_{ds}: {len(all_rows_by_dataset[ds])} filas")