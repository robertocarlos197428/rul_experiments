# Reporte 01 — Auditoría y Consolidación del Dataset FEMTO

**Experimento asociado:** exp006_consolidate_final_set
**Fecha:** 2026-08-17
**Estado de la etapa:** cerrada (manifest completed)

## 1. Objetivo
Auditar los datos originales del dataset FEMTO (IEEE PHM 2012), corregir las anomalías
documentadas y consolidar una fuente de verdad congelada en data/processed/ para el
pipeline de mantenimiento predictivo (RUL).

## 2. Alcance
- Sets: learning_set, full_test_set, test_set (17 rodamientos).
- 38,848 archivos acc (2,560 filas × 6 columnas, 25.6 kHz, registros de 0.1 s cada 10 s).

## 3. Anomalías detectadas y correcciones
- exp004_delimiter_fix: archivos con delimitador inconsistente → normalizados en interim.
- exp005_timestamp_fix: no monotonía/solapamiento de timestamps en Bearing1_1
  (acc_02121 y acc_02122) → corregidos en interim.
- Bearing1_4 (full_test_set): carpeta completa reemplazada por su versión corregida.

## 4. Reglas establecidas en esta etapa
- Regla suprema: los archivos solo se transfieren íntegros (SHA256 origen = destino);
  nunca se tocan ni se modifican.
- data/processed/ = fuente de verdad congelada; downstream solo lectura.
- data/raw/ = archivo frío en disco externo.
- Derivados (features, fpt, labels, splits, HI) viven en results/exp00X_/, nunca en processed.
- Sets canónicos en minúsculas; rodamientos y archivos tal cual el origen (Regla 3).

## 5. Resultado de la consolidación (EXP006)
- archivos_total: 38,848 | ok: 38,848 | failed: 0.
- versiones_interim_usadas: 1,430 (2 de Bearing1_1 + 1,428 de Bearing1_4).
- Verificación SHA256 por archivo: OK.
- Estado global: completed. Auditoría cerrada formalmente.

## 6. Estado actual
- processed congelado y verificado; carpetas legacy purgadas.
- Guía Maestra v2 vigente (capas, artefactos, idiomas).
- Git activado

## 7. Próximo paso
exp007: extracción de características (kurtosis por registro de 2,560 muestras, RMS)
y detección de FPT sobre processed.


        