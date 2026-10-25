# ==============================================================
# Script: 05_fix_bearing1_1_timestamps.py
# Experimento: EXP005 - Corrección de timestamps Bearing1_1
#
# Entrada:
# escribe aqui tu ruta
#
# Salidas:
# escribe aqui tu ruta
# escribe aqui tu ruta
# escribe aqui tu ruta
#
# Resumen:
# Corrige los timestamps de acc_02121.csv y acc_02122.csv.
# Establece una separación de 10 segundos entre archivos consecutivos.
# Reconstruye hour, minute, second y microsecond sin modificar las aceleraciones.
# Conserva el formato original de los archivos FEMTO, sin encabezados.
# Genera resumen, log, configuración, notas y manifest del EXP005.
# ==============================================================

from pathlib import Path
from datetime import datetime, timedelta
import csv
import json
import yaml


# ==============================================================
# RUTAS
# ==============================================================

ROOT = Path(r"escribe aqui tu ruta")

INPUT_DIR = (
    ROOT / "data" / "raw" / "FEMTO" / "Bearing1_1"
)

OUTPUT_DIR = (
    ROOT / "data" / "interim" / "FEMTO" / "corrected_data"
    / "Learning_Set" / "Bearing1_1"
)

RESULTS_DIR = ROOT / "results" / "exp005_timestamp_fix"
TABLES_DIR = RESULTS_DIR / "tables"
LOGS_DIR = RESULTS_DIR / "logs"

EXPERIMENT_DIR = ROOT / "experiments" / "exp005_timestamp_fix"


# ==============================================================
# ARCHIVOS
# ==============================================================

FILE_02120 = INPUT_DIR / "acc_02120.csv"
FILE_02121 = INPUT_DIR / "acc_02121.csv"
FILE_02122 = INPUT_DIR / "acc_02122.csv"
FILE_02123 = INPUT_DIR / "acc_02123.csv"


# ==============================================================
# CONFIGURACIÓN
# ==============================================================

FILE_INTERVAL_SECONDS = 10

# FEMTO: 2560 muestras por archivo.
# La adquisición corresponde a 25.6 kHz.
SAMPLE_RATE_HZ = 25600

EXPECTED_COLUMNS = 6


# ==============================================================
# PREPARAR CARPETAS
# ==============================================================

for directory in [
    OUTPUT_DIR,
    TABLES_DIR,
    LOGS_DIR,
    EXPERIMENT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


LOG_FILE = LOGS_DIR / "exp005_timestamp_fix.log"


def log(message):
    print(message)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


# ==============================================================
# LECTURA DE CSV SIN ENCABEZADO
# ==============================================================

def read_csv(path):

    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)

        rows = []

        for row in reader:

            if not row:
                continue

            if len(row) != EXPECTED_COLUMNS:
                raise ValueError(
                    f"{path.name}: se esperaban "
                    f"{EXPECTED_COLUMNS} columnas y se encontraron "
                    f"{len(row)}."
                )

            rows.append(row)

    return rows


# ==============================================================
# CONVERTIR LAS 4 COLUMNAS DE TIEMPO
#
# Posiciones:
# 0 = hour
# 1 = minute
# 2 = second
# 3 = microsecond
# 4 = acc_horizontal_g
# 5 = acc_vertical_g
# ==============================================================

def get_timestamp(row):

    return datetime(
        2000,
        1,
        1,
        int(float(row[0])),
        int(float(row[1])),
        int(float(row[2])),
        int(float(row[3])),
    )


# ==============================================================
# FORMATEAR TIMESTAMP
# ==============================================================

def timestamp_to_columns(timestamp):

    return [
        str(timestamp.hour),
        str(timestamp.minute),
        str(timestamp.second),
        str(timestamp.microsecond),
    ]


# ==============================================================
# CORREGIR ARCHIVO
#
# IMPORTANTE:
# Se copia la fila completa y SOLO se reemplazan las columnas
# 0, 1, 2 y 3 correspondientes al timestamp.
# Las columnas 4 y 5 quedan exactamente iguales.
# ==============================================================

def correct_file(rows, start_timestamp):

    corrected_rows = []

    sample_period = 1 / SAMPLE_RATE_HZ

    for index, row in enumerate(rows):

        corrected_row = row.copy()

        timestamp = (
            start_timestamp
            + timedelta(seconds=index * sample_period)
        )

        time_columns = timestamp_to_columns(timestamp)

        corrected_row[0] = time_columns[0]
        corrected_row[1] = time_columns[1]
        corrected_row[2] = time_columns[2]
        corrected_row[3] = time_columns[3]

        corrected_rows.append(corrected_row)

    return corrected_rows


# ==============================================================
# GUARDAR CSV SIN ENCABEZADO
# ==============================================================

def write_csv(path, rows):

    with open(path, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerows(rows)


# ==============================================================
# INICIO
# ==============================================================

log("=" * 70)
log("EXP005 - CORRECCIÓN DE TIMESTAMPS - Bearing1_1")
log("=" * 70)

log(f"Entrada: {INPUT_DIR}")
log(f"Salida:  {OUTPUT_DIR}")


# ==============================================================
# COMPROBAR ARCHIVOS
# ==============================================================

for path in [
    FILE_02120,
    FILE_02121,
    FILE_02122,
    FILE_02123,
]:

    if not path.exists():
        raise FileNotFoundError(
            f"No existe el archivo requerido: {path}"
        )

log("Todos los archivos de referencia fueron encontrados.")


# ==============================================================
# LEER ARCHIVOS
# ==============================================================

rows_02120 = read_csv(FILE_02120)
rows_02121 = read_csv(FILE_02121)
rows_02122 = read_csv(FILE_02122)
rows_02123 = read_csv(FILE_02123)

log(f"acc_02120.csv: {len(rows_02120)} filas")
log(f"acc_02121.csv: {len(rows_02121)} filas")
log(f"acc_02122.csv: {len(rows_02122)} filas")
log(f"acc_02123.csv: {len(rows_02123)} filas")


# ==============================================================
# OBTENER REFERENCIA TEMPORAL
#
# Se toma la última muestra de 02120.
# El siguiente archivo debe comenzar 10 segundos después.
# 02122 comienza 20 segundos después de 02120.
# ==============================================================

timestamp_02120_last = get_timestamp(rows_02120[-1])

timestamp_02121_start = (
    timestamp_02120_last
    + timedelta(seconds=FILE_INTERVAL_SECONDS)
)

timestamp_02122_start = (
    timestamp_02121_start
    + timedelta(seconds=FILE_INTERVAL_SECONDS)
)


log(f"Último timestamp 02120: {timestamp_02120_last}")
log(f"Nuevo inicio 02121:      {timestamp_02121_start}")
log(f"Nuevo inicio 02122:      {timestamp_02122_start}")


# ==============================================================
# CORREGIR 02121
# ==============================================================

corrected_02121 = correct_file(
    rows_02121,
    timestamp_02121_start,
)


# ==============================================================
# CORREGIR 02122
# ==============================================================

corrected_02122 = correct_file(
    rows_02122,
    timestamp_02122_start,
)


# ==============================================================
# RUTAS DE SALIDA
# ==============================================================

output_02121 = OUTPUT_DIR / "acc_02121.csv"
output_02122 = OUTPUT_DIR / "acc_02122.csv"


# ==============================================================
# GUARDAR
# ==============================================================

write_csv(output_02121, corrected_02121)
write_csv(output_02122, corrected_02122)

log(f"Generado: {output_02121}")
log(f"Generado: {output_02122}")


# ==============================================================
# VERIFICACIÓN DE TIMESTAMPS
# ==============================================================

new_02121_first = get_timestamp(corrected_02121[0])
new_02121_last = get_timestamp(corrected_02121[-1])

new_02122_first = get_timestamp(corrected_02122[0])
new_02122_last = get_timestamp(corrected_02122[-1])


difference_02120_02121 = (
    new_02121_first - timestamp_02120_last
).total_seconds()

difference_02121_02122 = (
    new_02122_first - new_02121_last
).total_seconds()


log(
    f"Separación 02120 -> inicio 02121: "
    f"{difference_02120_02121:.6f} s"
)

log(
    f"Separación fin 02121 -> inicio 02122: "
    f"{difference_02121_02122:.6f} s"
)


# ==============================================================
# TABLA RESUMEN
# ==============================================================

summary_file = (
    TABLES_DIR
    / "bearing1_1_timestamp_correction_summary.csv"
)

summary_rows = [
    [
        "experiment",
        "bearing",
        "file",
        "reference",
        "rows",
        "new_start",
        "new_end",
        "interval_seconds",
    ],
    [
        "EXP005",
        "Bearing1_1",
        "acc_02121.csv",
        "acc_02120.csv",
        len(corrected_02121),
        new_02121_first.isoformat(),
        new_02121_last.isoformat(),
        difference_02120_02121,
    ],
    [
        "EXP005",
        "Bearing1_1",
        "acc_02122.csv",
        "acc_02121.csv",
        len(corrected_02122),
        new_02122_first.isoformat(),
        new_02122_last.isoformat(),
        difference_02121_02122,
    ],
]

write_csv(summary_file, summary_rows)

log(f"Resumen generado: {summary_file}")


# ==============================================================
# CONFIG.YAML
# ==============================================================

config = {
    "experiment": "EXP005",
    "name": "timestamp_fix",
    "bearing": "Bearing1_1",
    "input_directory": str(INPUT_DIR),
    "output_directory": str(OUTPUT_DIR),
    "files_corrected": [
        "acc_02121.csv",
        "acc_02122.csv",
    ],
    "reference_files": [
        "acc_02120.csv",
        "acc_02123.csv",
    ],
    "file_interval_seconds": FILE_INTERVAL_SECONDS,
    "sample_rate_hz": SAMPLE_RATE_HZ,
    "modify_acceleration": False,
    "modify_raw": False,
}


with open(
    EXPERIMENT_DIR / "config.yaml",
    "w",
    encoding="utf-8",
) as f:

    yaml.safe_dump(
        config,
        f,
        sort_keys=False,
        allow_unicode=True,
    )


# ==============================================================
# NOTES.MD
# ==============================================================

notes = """# EXP005 - Corrección de timestamps Bearing1_1

## Objetivo

Corregir los timestamps de `acc_02121.csv` y `acc_02122.csv`
del rodamiento `Bearing1_1`.

## Método

Se utiliza el último timestamp de `acc_02120.csv` como referencia.

El inicio de `acc_02121.csv` se establece 10 segundos después.

El inicio de `acc_02122.csv` se establece 20 segundos después
del último timestamp de `acc_02120.csv`.

Dentro de cada archivo se reconstruye la progresión temporal
utilizando una frecuencia de muestreo de 25.6 kHz.

## Integridad de los datos

Las columnas de aceleración horizontal y vertical se mantienen
exactamente iguales a los archivos originales.

Los archivos ubicados en `data/raw` no son modificados.

Los archivos corregidos se almacenan exclusivamente en `data/interim`.

## Trazabilidad

Este experimento corresponde a EXP005.

Se generan:

- archivos corregidos
- tabla resumen
- log de ejecución
- config.yaml
- manifest.json
"""


with open(
    EXPERIMENT_DIR / "notes.md",
    "w",
    encoding="utf-8",
) as f:

    f.write(notes)


# ==============================================================
# MANIFEST.JSON
# ==============================================================

manifest = {
    "experiment": "EXP005",
    "experiment_name": "timestamp_fix",
    "bearing": "Bearing1_1",
    "input_directory": str(INPUT_DIR),
    "output_directory": str(OUTPUT_DIR),
    "corrected_files": [
        {
            "input": str(FILE_02121),
            "output": str(output_02121),
            "rows": len(corrected_02121),
        },
        {
            "input": str(FILE_02122),
            "output": str(output_02122),
            "rows": len(corrected_02122),
        },
    ],
    "reference_files": [
        str(FILE_02120),
        str(FILE_02123),
    ],
    "timestamp_interval_seconds": FILE_INTERVAL_SECONDS,
    "sample_rate_hz": SAMPLE_RATE_HZ,
    "raw_modified": False,
    "acceleration_modified": False,
    "status": "completed",
}


with open(
    EXPERIMENT_DIR / "manifest.json",
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        manifest,
        f,
        indent=4,
        ensure_ascii=False,
    )


# ==============================================================
# FIN
# ==============================================================

log("Manifest generado.")
log("EXP005 finalizado correctamente.")
log("=" * 70)