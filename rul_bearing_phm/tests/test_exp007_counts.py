"""
test_exp007_counts.py - Valida exp007
Cuenta acc_*.csv por bearing en FEMTO y compara vs filas en tabla_maestra.
Entrada: data/processed/FEMTO/*/Bearing*/acc_*.csv + results/exp007_time_features/features/
Salida: Tabla comparativa + resumen PASS/FAIL
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
FEMTO_BASE = BASE_DIR / "data" / "processed" / "FEMTO"
FEATURES_DIR = BASE_DIR / "results" / "exp007_time_features" / "features"
DATA_SETS = ["learning_set", "test_set", "full_test_set"]

print("=== TEST exp007: CONTEO ACC vs FILAS TABLA ===\n")

# 1. Contar acc en disco
disk_counts = {}
for data_set in DATA_SETS:
    ds_path = FEMTO_BASE / data_set
    if not ds_path.exists():
        continue
    for bearing_dir in sorted(ds_path.iterdir()):
        if not bearing_dir.is_dir():
            continue
        n_acc = len(list(bearing_dir.glob("acc_*.csv")))
        disk_counts[(data_set, bearing_dir.name)] = n_acc

# 2. Contar filas en tablas maestras
table_counts = {}
for data_set in DATA_SETS:
    parquet_path = FEATURES_DIR / f"tabla_maestra_{data_set}.parquet"
    if not parquet_path.exists():
        print(f"[WARN] No existe {parquet_path}")
        continue
    df = pd.read_parquet(parquet_path)
    grouped = df.groupby("bearing_id").size().to_dict()
    for bearing_id, n_rows in grouped.items():
        table_counts[(data_set, bearing_id)] = n_rows

# 3. Tabla comparativa
all_keys = sorted(set(disk_counts.keys()) | set(table_counts.keys()))
rows = []
for key in all_keys:
    data_set, bearing_id = key
    n_disk = disk_counts.get(key, 0)
    n_table = table_counts.get(key, 0)
    match = "OK" if n_disk == n_table else "FAIL"
    diff = n_table - n_disk
    rows.append({
        "data_set": data_set,
        "bearing_id": bearing_id,
        "n_acc_disco": n_disk,
        "n_filas_tabla": n_table,
        "diff": diff,
        "status": match
    })

df_check = pd.DataFrame(rows).sort_values(["data_set", "bearing_id"])
print(df_check.to_string(index=False))

print("\n--- RESUMEN POR DATA_SET ---")
summary = df_check.groupby("data_set").agg(
    bearings=("bearing_id", "count"),
    total_acc_disco=("n_acc_disco", "sum"),
    total_filas_tabla=("n_filas_tabla", "sum"),
    fails=("status", lambda x: (x=="FAIL").sum())
).reset_index()
print(summary.to_string(index=False))

# 4. Verificación global
total_disk = df_check["n_acc_disco"].sum()
total_table = df_check["n_filas_tabla"].sum()
print(f"\nTOTAL DISCO: {total_disk} | TOTAL TABLA: {total_table}")

if total_disk == total_table and summary["fails"].sum() == 0:
    print("\n✓ PASS: Todos los bearings coinciden acc == filas")
else:
    print(f"\n✗ FAIL: Hay {summary['fails'].sum()} bearings con diferencia")

# 5. Guardar reporte en tests/ mismo nombre.csv
out_path = BASE_DIR / "tests" / "test_exp007_counts.csv"
df_check.to_csv(out_path, index=False)
print(f"\nReporte guardado en: {out_path}")