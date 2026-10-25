# Guía Maestra de Experimentos (v2)

Referencia obligatoria antes de crear o ejecutar cualquier script del proyecto.

## 1. Reglas de Oro
1. `data/processed/` es la fuente de verdad congelada: solo la escribe el script de consolidación; todo downstream es solo lectura, jamás reescribir processed.

## 2. Ruta Base
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parents[1]

## 3. Capas
data/interim/        → correcciones quirúrgicas aisladas (staging).
data/processed/      → sets canónicos consolidados (fuente de verdad).
results/exp00X_/     → tablas, gráficos, logs y derivados (features, fpt, labels, splits, HI).
reports/             → informes humanos de etapa o proyecto.
experiments/exp00X_/ → gobernanza: config.yaml, notes.md, manifest.json.
scripts/             → código ejecutable.
src/                 → módulos y funciones que los scripts importan
test                 → verificación de resultados (ejemplo:correr la función de kurtosis sobre una señal gaussiana conocida y confirmar que da ≈3)
Los derivados de experimentos nunca viven en processed; se consumen declarándolos como input en el manifest.

## 4. Script Obligatorio
- Encabezado: nombre del script (línea 1), rutas de lectura/salida, resumen ≤ 5 líneas.
- Rutas solo vía BASE_DIR + pathlib; salidas con `.mkdir(parents=True, exist_ok=True)`.
- Logging dual: consola + `results/exp00X_/logs/exp00X_.log`.
- Validación estricta (columnas, delimitadores, estructura, errores) antes de exportar.

## 5. Artefactos por Experimento
- `config.yaml` → parámetros técnicos (umbrales, ventanas, fs, rutas, flags).
- `notes.md` → bitácora humana (objetivo, hallazgos, anomalías, decisiones).
- `manifest.json` → id, estado completed/failed, inputs, outputs, métricas, archivos procesados/descartados.

## 6. Idiomas y Nombres
1. Estructurales en inglés; contenido humano en español.
2. Heredados de la fuente (Bearing1_1, acc_XXXXX.csv) tal cual el origen.
3. Sets canónicos minúsculos: learning_set, full_test_set, test_set.
4. Columnas generadas: español snake_case sin tildes, salvo siglas de dominio (FPT, ZS, RMS).
5. Excepciones justificadas en el notes.md del experimento.