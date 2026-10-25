# ==============================================================================
# Script: 04_fix_bearing1_4_delimiter.py
# Ruta de lectura: data/raw/FEMTO/Full_Test_Set/Bearing1_4/
# Ruta de salida: data/interim/FEMTO/corrected_data/Full_Test_Set/Bearing1_4/
# Resumen:
# Corrige de forma específica el delimitador (;) a comas (,) únicamente para los 
# archivos del rodamiento Bearing1_4, asegurando que el resto de los datos sanos 
# no se toquen innecesariamente.
# ==============================================================================

import os
import json
import yaml
import logging
from pathlib import Path
import pandas as pd

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y LOGS
# ==========================================
BASE_DIR = Path(r"escribe aqui tu ruta")
TARGET_RAW = BASE_DIR / "data" / "raw" / "FEMTO" / "Bearing1_4"
TARGET_INTERIM = BASE_DIR / "data" / "interim" / "FEMTO" / "corrected_data" / "Full_Test_Set" / "Bearing1_4"

RESULTS_DIR = BASE_DIR / "results" / "exp004_delimiter_fix"
TABLES_DIR = RESULTS_DIR / "tables"
LOGS_DIR = RESULTS_DIR / "logs"
EXP_DIR = BASE_DIR / "experiments" / "exp004_delimiter_fix"

# Creación de carpetas
for folder in [TARGET_INTERIM, TABLES_DIR, LOGS_DIR, EXP_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# Configuración del log
log_file = LOGS_DIR / "exp004_bearing1_4_fix.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.info("Iniciando corrección quirúrgica de delimitador para Full_Test_Set/Bearing1_4...")

# ==========================================
# 2. PROCESAMIENTO ESPECÍFICO
# ==========================================
processed_records = []
total_processed = 0
total_success = 0

if not TARGET_RAW.exists():
    raise FileNotFoundError(f"La ruta de origen no existe: {TARGET_RAW}")

files = list(TARGET_RAW.glob("*.csv"))
logging.info(f"Se encontraron {len(files)} archivos en Bearing1_4 para corregir.")

for file_path in files:
    filename = file_path.name
    total_processed += 1
    destination_path = TARGET_INTERIM / filename
    
    try:
        # Lectura forzando punto y coma
        df = pd.read_csv(file_path, header=None, sep=';', low_memory=False)
        
        if df.shape[1] == 6:
            df.columns = [
                "hour", "minute", "second", "microsecond", 
                "acc_horizontal_g", "acc_vertical_g"
            ]
            # Guardar limpio con comas en interim
            df.to_csv(destination_path, index=False, header=False)
            total_success += 1
            processed_records.append({
                "rodamiento": "Bearing1_4",
                "archivo": filename,
                "estado": "corregido_exitosamente"
            })
        else:
            logging.warning(f"Estructura inesperada en {filename}: {df.shape[1]} columnas")
            processed_records.append({
                "rodamiento": "Bearing1_4",
                "archivo": filename,
                "estado": f"fallo_columnas_{df.shape[1]}"
            })
    except Exception as e:
        logging.error(f"Error procesando {filename}: {str(e)}")
        processed_records.append({
            "rodamiento": "Bearing1_4",
            "archivo": filename,
            "estado": f"error: {str(e)}"
        })

# ==========================================
# 3. GUARDAR RESULTADOS Y REGISTROS
# ==========================================
df_res = pd.DataFrame(processed_records)
path_csv = TABLES_DIR / "bearing1_4_fix_summary.csv"
df_res.to_csv(path_csv, index=False)

# Config del experimento
config_data = {
    "experiment": "exp004_delimiter_fix_bearing1_4",
    "description": "Corrección específica del delimitador ';' a ',' para el rodamiento Bearing1_4.",
    "target_folder": "Full_Test_Set/Bearing1_4",
    "raw_data_modified": False
}
with open(EXP_DIR / "config.yaml", "w", encoding="utf-8") as f:
    yaml.dump(config_data, f, allow_unicode=True)

notes_content = """# Notas del Experimento EXP004 (Bearing1_4)
- **Aclaración:** El problema de delimitador por punto y coma (`;`) estaba confinado exclusivamente al rodamiento `Bearing1_4`.
- **Acción:** Se procesó únicamente esta carpeta, guardando el resultado normalizado en `data/interim/FEMTO/corrected_data/Full_Test_Set/Bearing1_4/`.
"""
(EXP_DIR / "notes.md").write_text(notes_content, encoding="utf-8")

manifest_data = {
    "experiment": "exp004_delimiter_fix_bearing1_4",
    "status": "completed",
    "target": "Full_Test_Set/Bearing1_4",
    "metrics": {
        "total_files": total_processed,
        "successfully_corrected": total_success
    }
}
with open(EXP_DIR / "manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest_data, f, indent=4, ensure_ascii=False)

# ==========================================
# 4. RESUMEN DE SALIDA
# ==========================================
print("\n--- RESUMEN DE ARCHIVOS CREADOS EN EXP004 (BEARING 1_4) ---")
print(f"1. {path_csv} -> Resumen de corrección de Bearing1_4.")
print(f"2. {TARGET_INTERIM} -> Carpeta interim con los archivos limpios de Bearing1_4.")
print(f"3. {EXP_DIR / 'config.yaml'} -> Configuración del experimento.")
print(f"4. {EXP_DIR / 'notes.md'} -> Notas del ajuste específico.")
print(f"5. {EXP_DIR / 'manifest.json'} -> Manifiesto del proceso.")
print(f"6. {log_file} -> Log de ejecución.\n")