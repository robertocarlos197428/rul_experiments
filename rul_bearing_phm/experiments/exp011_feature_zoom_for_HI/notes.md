# exp011_feature_zoom_for_HI

## Objetivo
Revisar visualmente RMS, Std, Skewness y Kurtosis (canales H y V) en
Learning_set, usando escalas fijas por feature para evitar que outliers
distorsionen la lectura de tendencia y monotonicidad.

## Escalas fijas usadas
- RMS: 0-5
- Std: 0-4
- Skewness: 0-2
- Kurtosis: 0-50

(Peak no se incluye en este analisis, ya fue confirmada como feature valida.)

## Bearings incluidos
Bearing1_1, Bearing1_2, Bearing2_1, Bearing2_2, Bearing3_1, Bearing3_2

## Pendiente
- Revisar resultado y actualizar veredicto de Skewness y Kurtosis.
- Definir tratamiento de outliers puntuales antes de normalizar.
- Comparar HI con y sin correccion de outliers (experimento posterior).
