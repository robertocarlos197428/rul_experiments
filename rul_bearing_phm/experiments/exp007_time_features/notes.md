# exp007_time_features - Notas

## Objetivo
Extraer 16 features de dominio tiempo (8 fórmulas x H,V) para baseline RUL.

## Ruta entrada
`data/processed/FEMTO/{learning_set,test_set,full_test_set}/Bearing*/acc_*.csv`

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
`results/exp007_time_features/features/` SOLO tablas:
- tabla_maestra_learning_set.parquet /.csv
- tabla_maestra_test_set.parquet /.csv
- tabla_maestra_full_test_set.parquet /.csv

Total 6 archivos, 22 columnas cada uno.

Fecha: 2026-08-22 16:51
