"""
test_exp007_features_stats.py - Chequeo salud tablas maestras exp007
Guarda reporte en tests/test_exp007_features_stats.md
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
FEATURES_DIR = BASE_DIR / "results/exp007_time_features/features"
OUT_PATH = BASE_DIR / "tests" / "test_exp007_features_stats.md"

lines = []
lines.append("# Reporte Salud exp007 - Time Features\n")

for data_set in ["learning_set", "test_set", "full_test_set"]:
    path = FEATURES_DIR / f"tabla_maestra_{data_set}.parquet"
    df = pd.read_parquet(path)

    lines.append(f"\n## {data_set} - shape {df.shape}\n")

    # 1. NaNs
    nans = df.isna().sum()
    lines.append("### NaNs por columna\n")
    lines.append(nans.to_markdown())
    lines.append("\n")

    # 2. Infs
    num_df = df.select_dtypes(include='number')
    n_inf = (num_df == float('inf')).sum().sum()
    n_ninf = (num_df == float('-inf')).sum().sum()
    lines.append(f"### Infs\n- Inf: {n_inf}\n- -Inf: {n_ninf}\n")

    # 3. Duplicados
    dups = df.duplicated(subset=['bearing_id','file_id']).sum()
    lines.append(f"\n### Duplicados (bearing_id + file_id): {dups}\n")

    # 4. Stats
    feature_cols = [c for c in df.columns if c not in ['bearing_id','data_set','file_id','timestamp','duration_sec','sampling_hz']]
    stats = df[feature_cols].describe().T[['min','mean','max','std']].round(6)
    lines.append(f"\n### Stats {len(feature_cols)} features\n")
    lines.append(stats.to_markdown())
    lines.append("\n---\n")

# Guardar en tests/ mismo nombre.md
OUT_PATH.write_text("\n".join(lines), encoding='utf-8')
print(f"Reporte guardado en: {OUT_PATH}\n")
print("\n".join(lines))