# EXP005 - Corrección de timestamps Bearing1_1

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
