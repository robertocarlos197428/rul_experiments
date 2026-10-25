# ==============================================================================
# Script: 01_audit_dataset.py
# Ruta de lectura: escribe aqui tu ruta
# Rutas de salida: 
#   - data/interim/FEMTO/metadata/
#   - results/exp001_femto_audit/
# Resumen:
# Audita y valida la estructura inicial del dataset FEMTO recorriendo carpetas
# para inventariar archivos, detectar anomalías estructurales (columnas, nulos,
# vacíos), identificar snapshots faltantes o duplicados por rodamiento y 
# generar reportes de calidad y metadatos base para el proyecto.
# ==============================================================================

import os
import re
import logging
from pathlib import Path
import pandas as pd
import numpy as np

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y LOGS
# ==========================================
BASE_DIR = Path(r"escribe aqui tu ruta")
DATA_RAW = BASE_DIR / "data" / "raw" / "FEMTO"
METADATA_DIR = BASE_DIR / "data" / "interim" / "FEMTO" / "metadata"
RESULTS_DIR = BASE_DIR / "results" / "exp001_femto_audit"

# Creación automática de carpetas necesarias
for folder in [
    METADATA_DIR,
    RESULTS_DIR / "figures",
    RESULTS_DIR / "tables",
    RESULTS_DIR / "logs"
]:
    folder.mkdir(parents=True, exist_ok=True)

# Configuración del sistema de logs
log_file = RESULTS_DIR / "logs" / "audit_femto.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.info("Iniciando auditoría del dataset FEMTO (EXP001)...")

# ==========================================
# 2. FUNCIONES DE INSPECCIÓN Y VALIDACIÓN
# ==========================================
def parse_filename(filename):
    """Extrae el tipo de archivo (acc/temp) y el ID del snapshot."""
    match_acc = re.match(r"acc_(\d+)\.csv$", filename)
    if match_acc:
        return "acc", int(match_acc.group(1))
    
    match_temp = re.match(r"temp_(\d+)\.csv$", filename)
    if match_temp:
        return "temp", int(match_temp.group(1))
        
    return "other", None

def audit_vibration_file(file_path):
    """Audita un archivo individual de aceleración (.csv)."""
    issues = []
    file_size = file_path.stat().st_size
    
    if file_size == 0:
        return {"status": "corrupt", "issues": ["archivo_vacio"], "rows": 0, "size_bytes": 0}
        
    try:
        # Lectura sin encabezados, separada por comas
        df = pd.read_csv(file_path, header=None, low_memory=False)
    except Exception as e:
        return {"status": "corrupt", "issues": [f"error_lectura: {str(e)}"], "rows": 0, "size_bytes": file_size}
        
    # Validar cantidad de columnas (deben ser exactamente 6)
    if df.shape[1] != 6:
        issues.append(f"columnas_invalidas_{df.shape[1]}")
        
    # Validar tipos de datos y valores nulos/infinitos
    if df.isnull().values.any():
        issues.append("valores_faltantes_nan")
        
    # Intentar conversión numérica estricta
    try:
        df_num = df.apply(pd.to_numeric, errors='coerce')
        if df_num.isnull().values.any():
            issues.append("valores_no_numericos")
        if np.isinf(df_num.values).any():
            issues.append("valores_infinitos")
    except Exception:
        issues.append("error_conversion_numerica")

    status = "warning" if issues else "ok"
    return {
        "status": status,
        "issues": ";".join(issues) if issues else "none",
        "rows": len(df),
        "size_bytes": file_size
    }

# ==========================================
# 3. RECORRIDO Y AUDITORÍA DEL DATASET
# ==========================================
inventory_records = []
quality_records = []
bearing_summaries = []

if not DATA_RAW.exists():
    logging.error(f"La ruta del dataset no existe: {DATA_RAW}")
    raise FileNotFoundError(f"Ruta no encontrada: {DATA_RAW}")

# Recorrer conjuntos (Learning_Set, Test_Set, Full_Test_Set)
for subset_dir in [d for d in DATA_RAW.iterdir() if d.is_dir()]:
    subset_name = subset_dir.name
    logging.info(f"Procesando conjunto: {subset_name}")
    
    # Recorrer carpetas de rodamientos dentro de cada conjunto
    for bearing_dir in [d for d in subset_dir.iterdir() if d.is_dir()]:
        bearing_name = bearing_dir.name
        logging.info(f"  -> Rodamiento: {bearing_name}")
        
        files = sorted(list(bearing_dir.glob("*.csv")))
        
        snapshots_acc = []
        file_counts = {}
        
        for file_path in files:
            file_type, snap_id = parse_filename(file_path.name)
            
            # Control de duplicados por nombre
            file_counts[file_path.name] = file_counts.get(file_path.name, 0) + 1
            is_duplicated = file_counts[file_path.name] > 1
            
            file_info = {
                "subset": subset_name,
                "bearing": bearing_name,
                "filename": file_path.name,
                "file_type": file_type,
                "snapshot_id": snap_id,
                "is_duplicated": is_duplicated,
                "status": "ok",
                "issues": "none",
                "rows": 0,
                "size_bytes": file_path.stat().st_size
            }
            
            if file_type == "acc":
                snapshots_acc.append(snap_id)
                audit_res = audit_vibration_file(file_path)
                file_info["status"] = audit_res["status"]
                file_info["issues"] = audit_res["issues"]
                file_info["rows"] = audit_res["rows"]
                if is_duplicated:
                    file_info["issues"] += ";archivo_duplicado"
                    file_info["status"] = "warning"
            elif file_type == "temp":
                if is_duplicated:
                    file_info["issues"] = "archivo_duplicado"
                    file_info["status"] = "warning"
            else:
                file_info["issues"] = "nomenclatura_desconocida"
                file_info["status"] = "warning"
                
            inventory_records.append(file_info)
            
            if file_info["status"] != "ok":
                quality_records.append(file_info)

        # Resumen por rodamiento (enfocado en aceleración/vibración)
        acc_snapshots = sorted([s for s in snapshots_acc if s is not None])
        total_snapshots = len(acc_snapshots)
        
        first_snapshot = acc_snapshots[0] if total_snapshots > 0 else None
        last_snapshot = acc_snapshots[-1] if total_snapshots > 0 else None
        
        # Detección de archivos faltantes en la secuencia numérica esperada
        missing_files = []
        if total_snapshots > 0:
            expected_range = set(range(first_snapshot, last_snapshot + 1))
            missing_files = sorted(list(expected_range - set(acc_snapshots)))

        bearing_summaries.append({
            "subset": subset_name,
            "bearing": bearing_name,
            "total_files": len(files),
            "total_acc_snapshots": total_snapshots,
            "first_snapshot": first_snapshot,
            "last_snapshot": last_snapshot,
            "missing_snapshots_count": len(missing_files),
            "missing_snapshots_list": str(missing_files) if missing_files else "none"
        })

# ==========================================
# 4. EXPORTACIÓN DE RESULTADOS Y METADATA
# ==========================================
df_inventory = pd.DataFrame(inventory_records)
df_quality = pd.DataFrame(quality_records)
df_bearing_summary = pd.DataFrame(bearing_summaries)

# Rutas de salida según instrucciones
path_inventory = METADATA_DIR / "dataset_inventory_femto_v001.csv"
path_summary = METADATA_DIR / "bearing_summary_femto_v001.csv"
path_quality = METADATA_DIR / "data_quality_femto_v001.csv"

df_inventory.to_csv(path_inventory, index=False)
df_bearing_summary.to_csv(path_summary, index=False)
df_quality.to_csv(path_quality, index=False)

logging.info("Auditoría completada con éxito.")
logging.info(f"Inventario guardado en: {path_inventory}")
logging.info(f"Resumen de rodamientos guardado en: {path_summary}")
logging.info(f"Reporte de calidad guardado en: {path_quality}")