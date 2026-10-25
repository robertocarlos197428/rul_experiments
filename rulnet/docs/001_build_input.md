# 001 - Build Input FEMTO

**Fecha:** 2026-09-09 13:47:52
**Script:** `src/input_builder/001_build_input.py`

## Que hace
Lee los 17 Bearings planos de `data/raw/FEMTO/` (ya auditados, todos 2560 muestras) y crea un tensor congelado `[N][1][2560]` en crudo (g) sin normalizar.

## Por que no normaliza
- Si normaliza aqui, congela el factor de FEMTO y al cambiar de sensor (ULM u otro) hay que rehacer todo.
- La amplitud en g es indicador de falla. Normalizar global a -1/1 destruye severidad.
- La normalizacion se delega a `src/core/normalizer.py` con modo configurable (none, zscore global sana, etc) entrenado solo con train.

## Entradas
- `data/raw/FEMTO/BearingX_Y/acc_*.csv`
- Formato fijo: 6 columnas [hora, min, seg, microsec, H, V]
- Se usa solo columna 5 H (indice 4) -> contrato [N][1][2560]
- Todos los archivos ya auditados: 2560 muestras. Solo varia cantidad por bearing porque fallan en tiempos distintos.

## Salidas
- `escribe aqui tu ruta con:
  - `X`: float32 [N,1,2560] crudo
  - `bearing_names`: array ["Bearing1_1"...]
  - `boundaries`: array [[0,2802], [2803,3673]...] -> trazabilidad liviana
  - `counts`: cantidad por bearing
- `escribe aqui tu ruta
- `escribe aqui tu ruta (este archivo)

## Trazabilidad sin lista de 40k
No se guarda lista de 40k strings `Bearing1_1/acc_00001.csv`. Eso pesa y no sirve.
Se guarda limites de indice:
```
Bearing1_1: [0, 2802) -> 2802 muestras
Bearing1_2: [2803, 3673) -> 870 muestras
...
```
Para debuggear muestra N, buscar en que intervalo cae. Es liviano (17x2 ints).

## Codigo en detalle
1. Busca 17 carpetas `Bearing*` en RAW_DIR
2. Por cada bearing, lista `acc_*.csv` ordenados temporalmente
3. Lee cada csv sin header, valida 6 cols, toma iloc[:,4] (H)
4. Valida 2560 muestras, apila en lista
5. Guarda start/end antes y despues de cada bearing para index_map
6. Stack a [N,1,2560], valida NaN y forma
7. Guarda NPZ comprimido
8. Genera este MD

## Contrato
- Entrada TCN: [N][1][2560]
- No normalizado
- Trazable por boundaries

## Resultados de esta ejecucion
- Bearing1_1: [0, 2803) -> 2803
- Bearing1_2: [2803, 3674) -> 871
- Bearing1_3: [3674, 6049) -> 2375
- Bearing1_4: [6049, 7477) -> 1428
- Bearing1_5: [7477, 9940) -> 2463
- Bearing1_6: [9940, 12388) -> 2448
- Bearing1_7: [12388, 14647) -> 2259
- Bearing2_1: [14647, 15558) -> 911
- Bearing2_2: [15558, 16355) -> 797
- Bearing2_3: [16355, 18310) -> 1955
- Bearing2_4: [18310, 19061) -> 751
- Bearing2_5: [19061, 21372) -> 2311
- Bearing2_6: [21372, 22073) -> 701
- Bearing2_7: [22073, 22303) -> 230
- Bearing3_1: [22303, 22818) -> 515
- Bearing3_2: [22818, 24455) -> 1637
- Bearing3_3: [24455, 24889) -> 434

- Total N=24889
- Rango crudo: min -48.147999 max 48.127998 mean 0.001270
